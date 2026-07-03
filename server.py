"""SEE 生命印迹 - 本地测试服务端（保护 API Key）"""
import json, base64, ssl, os, subprocess, tempfile, sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from http.client import HTTPSConnection
from urllib.parse import urlparse
from socketserver import ThreadingMixIn
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine.orchestrator import CognitiveEngine
from engine.see_card import interpret_see_card, load_see_card_context

# ===== API Keys（环境变量注入，不写入代码）=====
BAOSI_KEY = os.environ.get('BAOSI_KEY', '')
DEEPSEEK_KEY = os.environ.get('DEEPSEEK_KEY', '')

def proxy_request(url, payload, headers, timeout=180):
    """直连 API"""
    parsed = urlparse(url)
    conn = HTTPSConnection(parsed.hostname, parsed.port or 443, timeout=timeout)
    ctx = ssl.create_default_context()
    conn._context = ctx
    conn.connect()
    conn.request("POST", parsed.path + ("?" + parsed.query if parsed.query else ""),
                 body=payload, headers=headers)
    resp = conn.getresponse()
    data = resp.read().decode()
    conn.close()
    result = json.loads(data)
    if "error" in result:
        raise Exception(result["error"].get("message", json.dumps(result["error"])))
    return result

def _trim_incomplete(text):
    """Remove trailing incomplete sentence/fragment from LLM output."""
    import re
    text = text.rstrip()
    # Remove trailing partial sentence (no ending punctuation)
    last_newline = text.rfind('\n')
    if last_newline > 0:
        last_line = text[last_newline+1:].strip()
        if last_line and len(last_line) < 20:
            if not re.search(r'[。！？.!?」』"）\)】]$', last_line):
                text = text[:last_newline].rstrip()
    # Remove trailing markdown heading fragment like '## ' with no content after
    text = re.sub(r'\n+#+\s*$', '', text)
    # Remove trailing junk characters
    text = re.sub(r'[，,、\s]*$', '', text)
    return text


def _generate_pdf(title, markdown):
    """Generate Chinese PDF from markdown using fpdf."""
    import io, re
    from fpdf import FPDF

    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.set_left_margin(15)
    pdf.set_right_margin(15)
    # Chinese font: env var → macOS common paths → Linux common paths → bundled
    font_path = os.environ.get('SEE_FONT_PATH', '')
    if not font_path or not os.path.exists(font_path):
        candidates = [
            '/System/Library/Fonts/STHeiti Light.ttc',
            '/Library/Fonts/Arial Unicode.ttf',
            '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
            '/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf',
            '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
        ]
        font_path = next((p for p in candidates if os.path.exists(p)), '')
    if not font_path:
        raise RuntimeError('No Chinese font found. Set SEE_FONT_PATH env var or install a CJK font.')
    pdf.add_font('CJK', '', font_path)
    pdf.add_page()
    pdf.set_auto_page_break(True, 20)

    lines = markdown.split('\n')
    for line in lines:
        line = line.rstrip()
        if not line:
            pdf.ln(2)
            continue
        clean = re.sub(r'\*\*(.+?)\*\*', r'\1', line)
        clean = re.sub(r'`(.+?)`', r'\1', clean)
        clean = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', clean)
        clean = re.sub(r'^#+\s*', '', clean)
        clean = re.sub(r'^- ', '  - ', clean)
        if not clean.strip():
            continue
        if line.startswith('# '):
            pdf.set_font('CJK', '', 14)
            pdf.ln(2)
            pdf.cell(0, 8, clean, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)
        elif line.startswith('## '):
            pdf.set_font('CJK', '', 11)
            pdf.ln(2)
            pdf.cell(0, 7, clean, new_x="LMARGIN", new_y="NEXT")
        elif line.startswith('### '):
            pdf.set_font('CJK', '', 10)
            pdf.cell(0, 6.5, clean, new_x="LMARGIN", new_y="NEXT")
        elif line.startswith('```'):
            continue
        elif len(clean) < 80:
            pdf.set_font('CJK', '', 9)
            pdf.cell(0, 5.5, clean, new_x="LMARGIN", new_y="NEXT")
        else:
            pdf.set_font('CJK', '', 9)
            pdf.multi_cell(0, 5.5, clean)

    buf = io.BytesIO()
    pdf.output(buf)
    return buf.getvalue()


class SEEHandler(SimpleHTTPRequestHandler):
    def do_POST(self):
        body = self._read_body()

        if self.path == '/api/vision':
            self._proxy_vision(body)
        elif self.path == '/api/report':
            self._proxy_report(body)
        elif self.path == '/api/ocr':
            self._proxy_ocr(body)
        elif self.path == '/api/talent':
            self._proxy_talent(body)
        elif self.path == '/api/talent-v2':
            self._proxy_talent_v2(body)
        elif self.path == '/api/parse-answers':
            self._proxy_parse_answers(body)
        elif self.path == '/api/talent-chat':
            self._proxy_talent_chat(body)
        elif self.path == '/api/belief':
            self._proxy_belief(body)
        elif self.path == '/api/growth':
            self._proxy_growth(body)
        elif self.path == '/api/composite':
            self._proxy_composite(body)
        elif self.path == '/api/export-pdf':
            self._export_pdf(body)
        else:
            self.send_error(404)

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()

    def do_GET(self):
        if self.path == '/':
            self.path = '/index.html'
        return super().do_GET()

    def _proxy_vision(self, body):
        """代理智谱 GLM-4V-Flash 识图"""
        try:
            data = json.loads(body)
            image_b64 = data.get('image', '').split(',')[-1]  # strip data: prefix

            # Compress image to reduce proxy timeout
            tmp_in = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
            tmp_out = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
            tmp_in.write(base64.b64decode(image_b64))
            tmp_in.close(); tmp_out.close()
            subprocess.run(['sips', '-s', 'format', 'jpeg', '-s', 'formatOptions', '30', '-Z', '800',
                tmp_in.name, '--out', tmp_out.name], capture_output=True)
            with open(tmp_out.name, 'rb') as f:
                image_b64 = base64.b64encode(f.read()).decode()
            os.unlink(tmp_in.name); os.unlink(tmp_out.name)

            payload = json.dumps({
                "model": "claude-sonnet-4-20250514",
                "messages": [{"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + image_b64}},
                    {"type": "text", "text": self._vision_prompt()}
                ]}],
                "max_tokens": 3000
            }).encode()

            result = proxy_request(
                "https://api.baosiapi.com/v1/chat/completions",
                payload,
                {"Content-Type": "application/json", "Authorization": f"Bearer {BAOSI_KEY}"}
            )

            content = result["choices"][0]["message"]["content"]
            parsed = self._extract_json(content)
            usage = result.get("usage", {})

            # 计算成本 (baosi Claude Sonnet 4)
            tokens = usage.get("total_tokens", 0)
            cost = tokens / 1000 * 0.003

            self._json(200, {**parsed, "usage": usage, "cost": round(cost, 6)})

        except Exception as e:
            self._json(500, {"error": str(e)})

    def _proxy_report(self, body):
        """代理 DeepSeek 报告生成"""
        try:
            data = json.loads(body)
            report_type = data.get('type', 'portrait')
            portrait = data.get('portrait', {})
            base_report = data.get('baseReport', '')

            prompt = self._report_prompt(report_type, portrait, base_report)

            payload = json.dumps({
                "model": "deepseek-v4-pro",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 3000,
                "temperature": 0.7
            }).encode()

            result = proxy_request(
                "https://api.deepseek.com/v1/chat/completions",
                payload,
                {"Content-Type": "application/json", "Authorization": f"Bearer {DEEPSEEK_KEY}"}
            )

            content = result["choices"][0]["message"]["content"]
            usage = result.get("usage", {})
            tokens = usage.get("total_tokens", 0)
            cost = (usage.get("prompt_tokens", 0) * 0.55 + usage.get("completion_tokens", 0) * 2.19) / 1000000

            # SEE卡 portrait 校验
            response = {"content": content, "usage": usage, "cost": round(cost, 6)}
            if report_type == 'portrait':
                from engine.see_card import interpret_see_card
                from engine.validator import validate
                try:
                    interp = interpret_see_card(portrait)
                    structure = {'trc': None, 'atd': None, 'evidence': interp.get('evidence', {})}
                    validation = validate(content, structure, 'see-card-portrait')
                    response['validation'] = validation
                except:
                    pass

            self._json(200, response)

        except Exception as e:
            self._json(500, {"error": str(e)})

    def _read_body(self):
        length = int(self.headers.get('Content-Length', 0))
        return self.rfile.read(length) if length else b''

    def _json(self, code, data):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def _vision_prompt(self):
        return """你是一个答题卡识别器。查看这张SEE思维导图照片，判断25道选择题(q01-q25)各自选了A/B/C/D中的哪一个。

识别方法：
1. 找到每道题的文字（左侧区域）
2. 在题目同一行的右侧，看ABCD四个选项
3. 哪个选项被绿色箭头/标记/连线指向，就是该题答案
4. 每道题只有一个答案

手写字段（图片最右侧区域）：
- self_label: "我"相关的手写文字
- strategy_result: "深度"相关的手写文字
- receiver_result: "结果"相关的手写文字
- output_result: "分析"相关的手写文字

只输出纯JSON，不要任何解释：
{"answers":{"q01":"A","q02":"B","q03":"C","q04":"D","q05":"A","q06":"A","q07":"B","q08":"C","q09":"D","q10":"B","q11":"A","q12":"C","q13":"B","q14":"D","q15":"A","q16":"A","q17":"B","q18":"C","q19":"D","q20":"A","q21":"A","q22":"B","q23":"C","q24":"D","q25":"A"},"handwritten_fields":{"self_label":"","strategy_result":"","receiver_result":"","output_result":""},"confidence":{"overall":0.9,"uncertain_items":[]}}"""

    def _report_prompt(self, t, p, base):
        prompts = {}
        if t == 'portrait':
            interp = interpret_see_card(p)
            manual_ctx = load_see_card_context()
            prompts['portrait'] = f"""你是思维特质分析师。基于以下 SEE 卡 25 题思维画像的结构化分析结果，生成"SEE思维画像报告：AI自动解读"（800-1200字，Markdown）。

## SEE卡应用手册参考（写作边界与咨询表达）
{manual_ctx}

⚠️ 使用手册参考的方式：用其中的语言风格和咨询边界来写作，不要大段引用手册原文。不要引入 observed_data / rule_hits 中没有支撑的概念。

## 组合规则使用指引（必须遵守）
1. 以 rule_hits 中的 matched_rule_key、manual_interpretation、typical_behavior、overuse_or_risk、growth 为主要证据撰写各功能区解读。
2. 若 matched_rule_key 含 +（如 B+C），写「组合呈现」或「并列主导」，不得简化为单一主导。
3. 若 secondary_signals 含 D_support，描述为「需要支持/策略性选择信号」而非固定缺陷，并建议追问：天生短板还是主动选择。
4. 不要使用前端旧标签 style/strength/risk/growth 当它们与 rule_hits 冲突时。

## 原始作答数据（25题结论 + 大脑字段）
{json.dumps(interp['observed_data'], ensure_ascii=False)}

## 结构分析数据（必须基于此解释）
规则命中：
{json.dumps(interp['rule_hits'], ensure_ascii=False)}

证据追踪：
{json.dumps(interp['evidence'], ensure_ascii=False)}

缺失字段：{json.dumps(interp.get('missing',[]), ensure_ascii=False)}

行为摘要：
{interp['summary']}

⚠️ 这是 AI 自动解读。每个结论必须基于规则命中数据，但不要在报告中解释推导方法。
⚠️ 这是 SEE 卡 25 题思维画像。不要提及当前资料未覆盖的其他测评体系、指标名称或数据项。

结构：
## SEE思维画像报告：AI自动解读
### 一、核心特质画像（先做整体画像总览，用行为描述，不过度使用术语）
### 二、功能区解读（按精神功能/思维功能/体觉功能/听觉功能/视觉功能，逐一基于 matched_rule_key 和 manual_interpretation 解读。每个功能区解读直接开始，不设资料来源清单，不解释推理链方法）
### 三、成长建议（基于每模块的 growth 方向，给出可执行建议）
### 四、数据说明（如有缺失字段标注「当前资料不足以判断」。必须包含：本报告仅基于 SEE 卡 25 题选择结果和用户补充字段，未使用当前资料之外的数据。）

⚠️ 严禁：
- 提及当前资料未覆盖的测评体系或指标术语
- 编造数据、绝对化断言（一定/绝对/注定）
- 设置资料来源或推导依据清单类章节
- 添加说明分析方法、规则来源或推导流程的元描述段落
- 以选项计数、规则命中或台账式信息作为功能区解读开头
- 在报告中复述或引用 组合规则使用指引 中的方法论说明"""
        else:
            prompts = {

            'communication': f"""你是关系沟通顾问。基于基础画像，生成"沟通与关系报告"（600-900字，Markdown）。

画像摘要：{p.get('traits', [])}

结构：## 沟通与关系报告\n### 一、你的沟通风格\n### 二、与不同类型人沟通建议\n### 三、亲密关系中的你\n### 四、团队协作建议""",

            'action': f"""你是成长教练。基于基础画像，生成"成长行动计划报告"（600-900字，Markdown）。

画像摘要：{p.get('traits', [])}
各维度成长方向：{json.dumps([{'name':m['name'],'style':m['style'],'growth':m['growth']} for m in p.get('modules',[])], ensure_ascii=False)}

结构：## 成长行动计划报告\n### 一、21天核心练习\n### 二、每周行动清单\n### 三、推荐学习资源\n### 四、自我检视问题""",

            'learning': f"""你是学习风格分析师。基于思维画像，结合先天特质知识库，生成"学习风格分析报告"（600-900字，Markdown）。

画像摘要：{p.get('traits', [])}

结构：## 学习风格分析报告\n### 一、你的学习模式\n### 二、最高效的学习方式\n### 三、需要避免的学习陷阱\n### 四、个性化学习建议""",

            'emotion': f"""你是情绪模式分析师。基于思维画像，结合先天特质知识库，生成"情绪模式洞察报告"（600-900字，Markdown）。

画像摘要：{p.get('traits', [])}

结构：## 情绪模式洞察报告\n### 一、情绪反应特征\n### 二、压力下的行为模式\n### 三、情绪调节优势策略\n### 四、日常情绪管理建议""",

            'potential': f"""你是潜能发展顾问。基于思维画像，结合先天特质知识库，生成"潜能发展方向报告"（600-900字，Markdown）。

画像摘要：{p.get('traits', [])}

结构：## 潜能发展方向报告\n### 一、核心天赋识别\n### 二、重点发展领域\n### 三、成长加速策略\n### 四、长期发展规划""",

            'career': f"""你是职业发展顾问。基于基础画像，生成"事业发展报告"（600-900字，Markdown）。

画像摘要：{p.get('traits', [])}
各维度详情：{json.dumps([{'name':m['name'],'style':m['style'],'strength':m['strength'],'risk':m['risk']} for m in p.get('modules',[])], ensure_ascii=False)}

结构：## 事业发展报告\n### 一、你的职业优势\n### 二、适合的职业方向\n### 三、团队中的最佳定位\n### 四、职业成长建议

请用专业、务实的中文写作。"""
        }
        return prompts.get(t, prompts['portrait'])

    # ===== OCR（文字识别）=====
    def _proxy_ocr(self, body):
        try:
            data = json.loads(body)
            image_b64 = data.get('image', '').split(',')[-1]
            # Compress
            import subprocess as sp, tempfile as tf
            tin = tf.NamedTemporaryFile(suffix='.jpg', delete=False)
            tout = tf.NamedTemporaryFile(suffix='.jpg', delete=False)
            tin.write(base64.b64decode(image_b64)); tin.close(); tout.close()
            sp.run(['sips','-s','format','jpeg','-s','formatOptions','30','-Z','800',tin.name,'--out',tout.name], capture_output=True)
            with open(tout.name, 'rb') as f: image_b64 = base64.b64encode(f.read()).decode()
            os.unlink(tin.name); os.unlink(tout.name)

            result = proxy_request(
                "https://api.baosiapi.com/v1/chat/completions",
                json.dumps({
                    "model": "claude-sonnet-4-20250514",
                    "messages": [{"role":"user","content":[
                        {"type":"image_url","image_url":{"url":"data:image/jpeg;base64,"+image_b64}},
                        {"type":"text","text":"请识别并提取这张图片中的所有文字内容。按原文顺序输出，保持段落结构。只输出识别的文字，不要添加任何解释。"}
                    ]}],
                    "max_tokens": 2048
                }).encode(),
                {"Content-Type":"application/json","Authorization":f"Bearer {BAOSI_KEY}"}
            )
            text = result["choices"][0]["message"]["content"]
            usage = result.get("usage", {})
            tokens = usage.get("total_tokens", 0)
            self._json(200, {"text": text, "usage": usage, "cost": round(tokens/1000*0.003, 6)})
        except Exception as e:
            self._json(500, {"error": str(e)})

    # ===== Talent Report（知识库 + 报告生成）=====
    KB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kb_talent')

    def _load_kb(self):
        """加载知识库文件"""
        kb = ""
        if os.path.isdir(self.KB_DIR):
            for fname in sorted(os.listdir(self.KB_DIR)):
                if fname.endswith(('.txt', '.md')):
                    try:
                        with open(os.path.join(self.KB_DIR, fname), 'r') as f:
                            kb += f"\n--- {fname} ---\n" + f.read()
                    except: pass
        return kb.strip()

    def _proxy_talent(self, body):
        try:
            data = json.loads(body)
            ocr_text = data.get('ocrText', '')
            report_type = data.get('type', 'portrait')
            base_report = data.get('baseReport', '')
            kb = self._load_kb()

            prompts = {
                'portrait': f"""你是先天思维特质分析师。你必须严格依据下方知识库中的理论框架和定义来分析用户数据。

⚠️ 重要规则：
1. 先完整阅读知识库内容，理解其中的特质分类体系、术语定义和分析方法
2. 再用知识库中的框架去解读用户OCR报告中的文字
3. 报告中必须引用知识库中的概念和术语，不得凭空创造
4. 如果知识库中某个特质有明确的描述，请直接引用

## 知识库（必须基于此分析）
{kb if kb else '（知识库待补充）'}

## 用户报告OCR内容
{ocr_text}

请生成800-1200字的报告（Markdown格式）。
结构：## 先天思维特质报告\\n### 一、核心特质画像（引用知识库框架）\\n### 二、天赋优势分析（基于知识库定义）\\n### 三、成长空间与建议\\n### 四、学习与发展策略""",

                'learning': f"""你是学习风格分析师。严格依据知识库中的学习理论分析用户。⚠️ 必须先阅读知识库，用其中的框架来分析，引用其中的术语和定义。

知识库：{kb[:3000] if kb else '（知识库待补充）'}
用户特质：{ocr_text[:1500]}
基础报告：{base_report[:500]}

结构：## 学习风格分析报告\\n### 一、你的学习模式\\n### 二、最高效的学习方式\\n### 三、需要避免的学习陷阱\\n### 四、个性化建议""",

                'emotion': f"""你是情绪模式分析师。严格依据知识库中的情绪理论分析用户。⚠️ 必须先阅读知识库，用其中的框架来分析，引用其中的术语和定义。

知识库：{kb[:3000] if kb else '（知识库待补充）'}
用户特质：{ocr_text[:1500]}
基础报告：{base_report[:500]}

结构：## 情绪模式洞察报告\\n### 一、情绪反应特征\\n### 二、压力下的行为模式\\n### 三、情绪调节策略\\n### 四、日常情绪管理建议""",

                'potential': f"""你是潜能发展顾问。严格依据知识库中的潜能理论分析用户。⚠️ 必须先阅读知识库，用其中的框架来分析，引用其中的术语和定义。

知识库：{kb[:3000] if kb else '（知识库待补充）'}
用户特质：{ocr_text[:1500]}
基础报告：{base_report[:500]}

结构：## 潜能发展方向报告\\n### 一、核心天赋识别\\n### 二、重点发展领域\\n### 三、成长加速策略\\n### 四、长期发展规划"""
            }

            result = proxy_request(
                "https://api.baosiapi.com/v1/chat/completions",
                json.dumps({
                    "model": "claude-sonnet-4-20250514",
                    "messages": [{"role":"user","content": prompts.get(report_type, prompts['portrait'])}],
                    "max_tokens": 3000, "temperature": 0.7
                }).encode(),
                {"Content-Type":"application/json","Authorization":f"Bearer {BAOSI_KEY}"}
            )
            content = result["choices"][0]["message"]["content"]
            usage = result.get("usage", {})
            tokens = usage.get("total_tokens", 0)
            self._json(200, {"content": content, "usage": usage, "cost": round(tokens/1000*0.003, 6)})
        except Exception as e:
            self._json(500, {"error": str(e)})

    # ===== Talent V2（新版：三层认知引擎）=====
    def _proxy_talent_v2(self, body):
        """新版天赋报告：CognitiveEngine 三层 pipeline"""
        try:
            data = json.loads(body)
            ocr_text = data.get('ocrText', '')
            report_type = data.get('type', 'portrait')
            base_report = data.get('baseReport', '')
            style = data.get('style', 'gentle')
            age = data.get('age')
            target = data.get('target', 'self')

            # 拼接基础报告
            full_text = ocr_text
            if base_report:
                full_text = ocr_text + '\n\n[基础报告]\n' + base_report

            # 运行认知引擎
            engine = CognitiveEngine()
            engine_result = engine.run(full_text, report_type, style, age=age, target=target)

            # 构建消息
            messages = [
                {"role": "system", "content": engine_result['system_prompt']},
                {"role": "user", "content": engine_result['user_prompt']},
            ]

            result = proxy_request(
                "https://api.deepseek.com/v1/chat/completions",
                json.dumps({
                    "model": "deepseek-v4-pro",
                    "messages": messages,
                    "max_tokens": 3000, "temperature": 0.5
                }).encode(),
                {"Content-Type":"application/json","Authorization":f"Bearer {DEEPSEEK_KEY}"}
            )
            content = result["choices"][0]["message"]["content"]
            usage = result.get("usage", {})

            # 校验输出
            from engine.validator import validate
            validation = validate(content, engine_result['debug']['structure'], report_type)

            self._json(200, {
                "content": content,
                "usage": usage,
                "debug": engine_result['debug'],
                "validation": validation,
                "version": "3.1",
                "style": style,
            })
        except Exception as e:
            self._json(500, {"error": str(e)})

    # ===== Parse Answers（Tesseract.js OCR → DeepSeek 解析）=====
    def _proxy_parse_answers(self, body):
        try:
            data = json.loads(body)
            ocr_text = data.get('ocrText', '')
            prompt = f"""你是一个答题卡解析器。从以下OCR识别文字中，提取25道选择题的答案和手写字段。

识别规则：
1. 找到每道题(编号q01-q25)，判断选中的是A/B/C/D中的哪一个
2. 每道题只有一个答案
3. 手写字段（图片右侧区域）：
   - self_label: "我"相关的手写文字
   - strategy_result: "深度"相关的手写文字
   - receiver_result: "结果"相关的手写文字
   - output_result: "分析"相关的手写文字

只输出纯JSON，不要任何解释：
{{"answers":{{"q01":"A","q02":"B",...}},"handwritten_fields":{{"self_label":"","strategy_result":"","receiver_result":"","output_result":""}},"confidence":{{"overall":0.9,"uncertain_items":[]}}}}

OCR文字内容：
{ocr_text[:5000]}"""

            result = proxy_request(
                "https://api.deepseek.com/v1/chat/completions",
                json.dumps({
                    "model": "deepseek-v4-pro",
                    "messages": [{"role":"user","content": prompt}],
                    "max_tokens": 2000, "temperature": 0.1
                }).encode(),
                {"Content-Type":"application/json","Authorization":f"Bearer {DEEPSEEK_KEY}"}
            )
            content = result["choices"][0]["message"]["content"]
            parsed = self._extract_json(content)
            usage = result.get("usage", {})
            self._json(200, {**parsed, "usage": usage})
        except Exception as e:
            self._json(500, {"error": str(e)})

    # ===== Talent Chat（报告对话 + 整合）=====
    def _export_pdf(self, body):
        """服务端 PDF 导出（移动端 Safari 兼容，支持 JSON + form POST）"""
        try:
            # Support both JSON and form-encoded POST
            if body and body[0:1] == b'{':
                data = json.loads(body)
            else:
                from urllib.parse import parse_qs
                params = parse_qs(body.decode('utf-8') if isinstance(body, bytes) else body)
                data = {k: v[0] if isinstance(v, list) else v for k, v in params.items()}
            title = data.get('title', 'SEE报告')
            markdown = data.get('markdown', '')
            if not markdown:
                self._json(400, {"error": "缺少报告内容"})
                return

            pdf_bytes = _generate_pdf(title, markdown)
            self.send_response(200)
            self.send_header('Content-Type', 'application/pdf')
            self.send_header('Content-Disposition', f'attachment; filename="{title}.pdf"')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Length', str(len(pdf_bytes)))
            self.end_headers()
            self.wfile.write(pdf_bytes)
        except Exception as e:
            self._json(500, {"error": str(e), "stage": "pdf"})

    def _proxy_talent_chat(self, body):
        """对话式报告咨询。基于知识库 + 画像身份，帮助用户产出认可的最终报告。"""
        try:
            data = json.loads(body)
            report_text = data.get('reportText', '')
            conversation = data.get('conversation', [])
            user_message = data.get('userMessage', '')
            action = data.get('action', 'chat')  # chat | summarize
            age = data.get('age')
            persona = data.get('persona', {})  # {style, target}

            if not report_text:
                self._json(400, {"error": "缺少报告内容", "stage": "validate"})
                return
            if not DEEPSEEK_KEY:
                self._json(500, {"error": "服务未配置 API Key，请联系管理员", "stage": "config"})
                return

            # 加载知识库上下文 + 纹型数据
            from engine.retrieval import _kb
            kb = _kb()
            kb_context = kb.get('ontology', '')[:1500]

            # 如果提供了 OCR 原文，也提取纹型信息
            ocr_text = data.get('ocrText', '')
            pattern_context = ''
            if ocr_text:
                from engine.extractor import extract_metrics
                from engine.rules import apply_rules, rule_summary
                try:
                    m = extract_metrics(ocr_text)
                    s = apply_rules(m)
                    pis = s.get('pattern_insights', [])
                    if pis:
                        lines = ['\n## 当前报告的纹型数据（权威，不可编造）']
                        for p in pis:
                            lines.append(f"- {p['area']} 纹型={p['code']}：{p['insight']}")
                        pattern_context = '\n'.join(lines)
                except:
                    pass

            age_label = f'{age}岁' if age else '未知年龄'
            target = persona.get('target', 'self')
            style = persona.get('style', 'gentle')

            # 角色指令
            persona_guide = {
                'self': f'你正在与报告本人（{age_label}）对话。用「你」称呼，语气亲切。',
                'parent': f'你正在与一位家长对话，报告对象是{age_label}的孩子。用「您的孩子」称呼，先共情再建议。',
                'other': f'你正在与一位第三方解读人对话，报告对象是{age_label}的人。语气中立专业，用「这位」称呼报告对象。',
                'global': f'这份报告会分享给多个人看。兼顾本人、家人、老师同事的需求，给出分角色的建议。',
            }.get(target, '')

            if action == 'summarize':
                # 根据原始报告内容判断报告类型并使用对应结构
                is_personal = any(kw in report_text[:500] for kw in ['能量引擎', '个人成长', '主性格画像'])
                is_child = any(kw in report_text[:500] for kw in ['孩子', '学习力', '学习风格'])
                if is_personal or (not is_child):
                    structure = """## 一、能量引擎\n## 二、主性格画像\n## 三、核心驱动力\n## 四、能力结构\n## 五、最优通道\n## 六、各功能区左右脑特征\n## 七、警示提醒\n## 八、成长路径\n## 九、个性化补充（基于讨论中确认的个人背景与修正）"""
                else:
                    structure = """## 一、孩子的学习风格\n## 二、主性格画像\n## 三、最佳学习通道\n## 四、内驱方式\n## 五、行为特点\n## 六、沟通特点\n## 七、给家长的建议\n## 八、个性化补充（基于讨论中确认的补充信息）"""

                prompt = f"""你是一个 SEE 报告整合专家。将用户的个性化补充和修正整合进原始报告。

## 你的身份
{persona_guide}

## 知识库参考
{kb_context}

## 原始报告
{report_text[:3000]}

## 全部讨论记录（用户补充的个人背景与修正意见）
{json.dumps(conversation, ensure_ascii=False)}

## 任务
生成一份融合了用户个性化补充的最终报告。只输出报告正文，不要前言后记。

要求：
1. 保留原始报告的数据和结论，更新用户修正的部分
2. 将讨论中用户确认的个人背景、偏好、补充信息融入对应章节
3. 新增「个性化补充」章节汇总用户的个人化内容
4. 语言风格与原始报告保持一致
5. {persona_guide}

报告结构（必须严格遵循）：
# {{报告标题}}
{structure}

⚠️ 如果接近字数上限，宁可压缩中间章节，也要保证最后一句完整收尾。"""
            else:
                history = '\n'.join([f"{'用户' if m['role']=='user' else '顾问'}: {m['content'][:300]}" for m in conversation[-8:]])
                prompt = f"""你是一个 SEE 报告顾问。你的目标是帮助用户最终获得一份他们完全认可的、准确的报告。

## 你的身份
{persona_guide}

## 知识库（你的专业依据）
{kb_context}
{pattern_context}

## 报告内容（当前版本）
{report_text[:2500]}

## 对话历史
{history}

## 用户刚才说
{user_message}

## 你的回应规则
1. 自然对话，先理解用户，再给出有实质内容的回应
2. 如果用户指出报告中有不准确的地方，认真考虑并给出修正
3. 每次回复 100-250 字，聚焦、自然，像顾问对话而非机器人
4. 不要堆砌术语。除非上方纹型数据或当前报告明确列出，否则不要提具体纹型编码；优先用行为语言解释，不用编码堆砌。
5. 对「报什么班」类问题：给出能力方向建议而非具体机构，使用「可优先考虑/可以尝试」而非「一定/必须」
6. 当用户说「可以整合」「出报告」「生成」时，回复「好的，正在整合...」并停止
7. ⚠️ 不要在回复末尾添加「💡 如果满意...」等固定广告语。前端已有按钮。"""

            result = proxy_request(
                "https://api.deepseek.com/v1/chat/completions",
                json.dumps({
                    "model": "deepseek-v4-pro",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 4000 if action == 'summarize' else 400,
                    "temperature": 0.5
                }).encode(),
                {"Content-Type": "application/json", "Authorization": f"Bearer {DEEPSEEK_KEY}"}
            )
            reply = result["choices"][0]["message"]["content"]
            # Post-process: trim trailing fragments for summarize
            if action == 'summarize':
                reply = _trim_incomplete(reply)
            usage = result.get("usage", {})
            self._json(200, {"reply": reply, "action": action, "usage": usage})
        except Exception as e:
            import traceback
            err_msg = str(e)
            stage = 'llm'
            if 'timeout' in err_msg.lower() or 'timed out' in err_msg.lower():
                stage = 'timeout'
            elif 'auth' in err_msg.lower() or 'key' in err_msg.lower():
                stage = 'auth'
            self._json(500, {"error": err_msg, "stage": stage, "action": action})

    # ===== Growth Report（成长比对）=====
    def _proxy_growth(self, body):
        try:
            data = json.loads(body)
            portrait = data.get('portrait', '')
            talent = data.get('talent', '')
            kb = self._load_kb()

            prompt = f"""你是成长轨迹分析师。请对比用户的两份报告，找出交叉模式和动态变化。

## 思维画像报告
{portrait[:1500]}

## 先天思维特质报告
{talent[:1500]}

## 知识库参考
{kb[:1000] if kb else '（知识库待补充）'}

请做交叉比对分析：
1. 两份报告中一致的核心特质（稳定区域）
2. 两份报告中呈现差异的部分（成长空间/动态区域）
3. 综合分析：用户的成长轨迹和潜在发展方向

生成600-900字报告（Markdown格式）。
结构：## 成长比对报告\\n### 一、稳定特质（两份报告一致）\\n### 二、成长变化（差异分析）\\n### 三、综合成长建议\\n### 四、下一步行动指引"""

            result = proxy_request(
                "https://api.baosiapi.com/v1/chat/completions",
                json.dumps({
                    "model": "claude-sonnet-4-20250514",
                    "messages": [{"role":"user","content": prompt}],
                    "max_tokens": 3000, "temperature": 0.7
                }).encode(),
                {"Content-Type":"application/json","Authorization":f"Bearer {BAOSI_KEY}"}
            )
            content = result["choices"][0]["message"]["content"]
            usage = result.get("usage", {})
            self._json(200, {"content": content, "usage": usage, "cost": round(usage.get("total_tokens",0)/1000*0.003, 6)})
        except Exception as e:
            self._json(500, {"error": str(e)})

    # ===== Composite Report（合盘）=====
    def _proxy_composite(self, body):
        try:
            data = json.loads(body)
            ctype = data.get('type', 'partner')
            my_portrait = data.get('myPortrait', '')
            partner_answers = data.get('partnerAnswers', {})
            partner_handwritten = data.get('partnerHandwritten', {})

            type_names = {'parent': '亲子关系合盘', 'partner': '亲密关系合盘', 'family': '家庭合盘'}
            type_desc = {'parent': '亲子互动模式、沟通特点、成长支持策略', 'partner': '情感契合度、沟通模式、互补与成长空间', 'family': '家庭成员之间的互动模式、角色定位、家庭动力与成长方向'}

            prompt = f"""你是关系分析专家。请基于双方思维画像数据，生成一份{type_names.get(ctype, '关系合盘')}报告。

## 我的思维画像
{my_portrait[:1500]}

## 对方的思维特质
25题答案：{json.dumps(partner_answers, ensure_ascii=False)}
手写字段：{json.dumps(partner_handwritten, ensure_ascii=False)}

请分析{type_desc.get(ctype, '双方关系')}，生成600-900字报告（Markdown格式）。
结构：## {type_names.get(ctype, '关系合盘报告')}\\n### 一、契合之处\\n### 二、差异与互补\\n### 三、沟通建议\\n### 四、共同成长方向"""

            result = proxy_request(
                "https://api.baosiapi.com/v1/chat/completions",
                json.dumps({
                    "model": "claude-sonnet-4-20250514",
                    "messages": [{"role":"user","content": prompt}],
                    "max_tokens": 3000, "temperature": 0.7
                }).encode(),
                {"Content-Type":"application/json","Authorization":f"Bearer {BAOSI_KEY}"}
            )
            content = result["choices"][0]["message"]["content"]
            usage = result.get("usage", {})
            self._json(200, {"content": content, "usage": usage, "cost": round(usage.get("total_tokens",0)/1000*0.003, 6)})
        except Exception as e:
            self._json(500, {"error": str(e)})

    # ===== Belief Report（信念系统）=====
    def _proxy_belief(self, body):
        try:
            data = json.loads(body)
            user_input = data.get('input', '')
            base_report = data.get('ocrText', '')
            kb = self._load_kb()

            prompt = f"""你是信念系统分析师。请根据用户描述和已有报告，生成"信念系统分析报告"。

## 知识库参考
{kb[:2000] if kb else '（知识库待补充）'}

## 已有报告摘要
{base_report[:1000]}

## 用户信念描述
{user_input}

请分析用户的信念系统，包含识别限制性信念、赋能信念、信念来源，并给出转化建议。
生成600-900字报告（Markdown格式）。

结构：## 信念系统分析报告\\n### 一、核心信念识别\\n### 二、限制性信念分析\\n### 三、赋能信念强化\\n### 四、信念转化练习"""

            result = proxy_request(
                "https://api.baosiapi.com/v1/chat/completions",
                json.dumps({
                    "model": "claude-sonnet-4-20250514",
                    "messages": [{"role":"user","content": prompt}],
                    "max_tokens": 3000, "temperature": 0.7
                }).encode(),
                {"Content-Type":"application/json","Authorization":f"Bearer {BAOSI_KEY}"}
            )
            content = result["choices"][0]["message"]["content"]
            usage = result.get("usage", {})
            self._json(200, {"content": content, "usage": usage, "cost": round(usage.get("total_tokens",0)/1000*0.003, 6)})
        except Exception as e:
            self._json(500, {"error": str(e)})

    @staticmethod
    def _extract_json(text):
        import re
        match = re.search(r'\{[\s\S]*\}', text)
        if not match: raise ValueError(f"无法解析JSON: {text[:100]}")
        return json.loads(match.group())


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    """多线程 HTTP 服务器，支持并发请求"""
    daemon_threads = True

if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    ThreadingHTTPServer.allow_reuse_address = True
    server = ThreadingHTTPServer(('0.0.0.0', 8088), SEEHandler)
    print('🔒 SEE 服务端启动 (多线程): http://0.0.0.0:8088')
    print('   API Key 仅在服务端，前端不可见')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
        print('\n已停止')
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f'\n💥 服务端崩溃: {e}\n请手动重启: DEEPSEEK_KEY=sk-... python3 server.py')
