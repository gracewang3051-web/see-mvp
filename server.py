"""SEE 生命印迹 - 本地测试服务端（保护 API Key）"""
import json, base64, ssl, os, subprocess, tempfile, sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from http.client import HTTPSConnection
from urllib.parse import urlparse
from socketserver import ThreadingMixIn
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine.orchestrator import CognitiveEngine
from engine.see_card import interpret_see_card

# ===== API Keys（环境变量注入，不写入代码）=====
BAOSI_KEY = os.environ.get('BAOSI_KEY', '')
DEEPSEEK_KEY = os.environ.get('DEEPSEEK_KEY', 'SET_VIA_ENV')

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

            self._json(200, {"content": content, "usage": usage, "cost": round(cost, 6)})

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
            prompts['portrait'] = f"""你是思维特质分析师。基于以下 SEE 卡 25 题思维画像的结构化分析结果，生成"SEE思维画像报告：AI自动解读"（800-1200字，Markdown）。

## 结构分析数据（必须基于此解释）
规则命中：
{json.dumps(interp['rule_hits'], ensure_ascii=False)}

证据追踪：
{json.dumps(interp['evidence'], ensure_ascii=False)}

缺失字段：{json.dumps(interp.get('missing',[]), ensure_ascii=False)}

行为摘要：
{interp['summary']}

⚠️ 这是 AI 自动解读。必须有从数据到结论的推理链，让读者看懂「AI 是怎么分析的」。
⚠️ 这是 SEE 卡 25 题思维画像，没有 TRC/ATD/纹型数据，禁止在报告中提及这些概念。

结构：
## SEE思维画像报告：AI自动解读
### 一、解读依据（列出 5 个模块的选择结果及来源：25题选择 + 手写字段 + 大脑字段）
### 二、智能分析过程（每模块：选项 → 规则 → 行为含义 → 交叉组合推断）
### 三、核心特质画像（用行为描述，不过度使用术语）
### 四、成长建议（基于每模块的 growth 方向，给出可执行建议）
### 五、数据说明（标注缺失字段为「当前资料不足以判断」）

⚠️ 严禁：编造 TRC/ATD/纹型数据、绝对化断言（一定/绝对/注定）"""
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
                self._json(400, {"error": "缺少报告内容"})
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
                prompt = f"""你是一个 SEE 报告整合专家。你的任务是基于原始报告和用户与你的全部讨论，生成一份用户完全认可的最终报告。

## 你的身份
{persona_guide}

## 知识库参考（你回答的依据）
{kb_context}

## 原始报告
{report_text[:3000]}

## 全部讨论记录
{json.dumps(conversation, ensure_ascii=False)}

## 任务
请直接输出一份最终的综合报告。只输出报告正文，不要任何前言、后记、解释或客气话。

要求：
1. 将原始报告中用户提出修正的部分全部更新
2. 将讨论中用户确认的理解融入
3. 使用与报告对象年龄匹配的语言
4. {persona_guide}

报告结构（必须严格遵循）：
# {{报告标题}}
## 一、行为解码
## 二、先天特质地图（包含纹型解读）
## 三、优势发挥分析
## 四、成长提醒
## 五、支持方案

⚠️ 直接以 # 开头输出报告，不要加「好的」「以下是」等前缀。"""
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
1. 先确认你理解了用户的问题或疑虑，再说你的分析
2. 如果用户指出报告中有不准确的地方，认真考虑并给出修正建议
3. 鼓励用户确认你的理解是否正确（「如果我的理解对的话...」）
4. 如果用户认同某部分，记录下来并在总结时体现
5. 每次回复 150-300 字，聚焦、有实质内容
6. 基于知识库的专业知识来支撑你的回答，但不要堆砌术语
7. ⚠️ 纹型编码必须是上方「纹型数据」中列出的编码（如 Wc、Lu、Ws 等），绝对禁止编造「正形」「负形」「标准型」等不存在的纹型名称
8. ⚠️ 当用户说「可以整合」「出报告」「生成」等关键词时，不要再追问是否要出报告，直接说「好的，正在为您生成最终报告...」然后停止回复。前端会自动生成。
9. ⚠️ 每次回复末尾必须加：「---\\n💡 如果满意请点击下方 **📝 生成整合报告** 按钮，我会将讨论结果整合为最终报告。如需继续调整请直接告诉我。」"""

            result = proxy_request(
                "https://api.deepseek.com/v1/chat/completions",
                json.dumps({
                    "model": "deepseek-v4-pro",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 3000 if action == 'summarize' else 400,
                    "temperature": 0.5
                }).encode(),
                {"Content-Type": "application/json", "Authorization": f"Bearer {DEEPSEEK_KEY}"}
            )
            reply = result["choices"][0]["message"]["content"]
            usage = result.get("usage", {})
            self._json(200, {"reply": reply, "action": action, "usage": usage})
        except Exception as e:
            self._json(500, {"error": str(e)})

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
