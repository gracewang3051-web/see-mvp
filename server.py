"""SEE 生命印迹 - 本地测试服务端（保护 API Key）"""
import json, base64, ssl, os, subprocess, tempfile, sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from http.client import HTTPSConnection
from urllib.parse import urlparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine.rule_engine import process as engine_process

# ===== API Keys（环境变量注入，不写入代码）=====
BAOSI_KEY = os.environ.get('BAOSI_KEY', '')
DEEPSEEK_KEY = os.environ.get('DEEPSEEK_KEY', '')

# ===== 直连请求（服务器不需要代理）=====

def proxy_request(url, payload, headers, timeout=180):
    """直连 API（宝思/DeepSeek 国内直连通）"""
    parsed = urlparse(url)
    conn = HTTPSConnection(parsed.hostname, parsed.port or 443, timeout=timeout)
    ctx = ssl.create_default_context()
    ctx.check_hostname = True
    ctx.verify_mode = ssl.CERT_REQUIRED
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
        elif self.path == '/api/belief':
            self._proxy_belief(body)
        elif self.path == '/api/growth':
            self._proxy_growth(body)
        elif self.path == '/api/composite':
            self._proxy_composite(body)
        else:
            self.send_error(404)

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
        prompts = {
            'portrait': f"""你是思维特质分析师。基于以下SEE思维画像数据，生成"基础思维画像报告"（800-1200字，Markdown）。

数据：{json.dumps(p, ensure_ascii=False)}

结构：## 基础思维画像报告\n### 一、核心思维模式\n### 二、各维度解读\n### 三、综合优势\n### 四、潜在盲区\n### 五、成长建议""",

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

    # ===== Talent V2（新版：规则引擎 + 结构化知识库）=====
    def _proxy_talent_v2(self, body):
        """新版天赋报告：使用 rule_engine.py 结构化 pipeline"""
        try:
            data = json.loads(body)
            ocr_text = data.get('ocrText', '')
            report_type = data.get('type', 'portrait')
            base_report = data.get('baseReport', '')

            # 支持结构化输入
            structured = data.get('structured', None)

            # 如果有 base_report，拼接起来
            full_text = ocr_text
            if base_report:
                full_text = ocr_text + '\n\n[基础报告]\n' + base_report

            # 运行规则引擎
            engine_result = engine_process(full_text, report_type, structured_data=structured)
            # Debug log
            m = engine_result['debug']['metrics']
            with open('/tmp/see_v2_debug.log', 'a') as lf:
                lf.write(f"[V2] OCR={len(full_text)}ch | TRC={m.get('trc')} ATD={m.get('atd')} | channels={m.get('learning_channels')} primary={m.get('primary_channel')} | rules={len(engine_result['debug']['rule_outputs'])}\n")
                lf.write(f"  OCR_TEXT: {full_text[:500]}\n")
                lf.write(f"  RULES: {[r['label'] for r in engine_result['debug']['rule_outputs']]}\n\n")

            # 构建消息
            messages = [
                {"role": "system", "content": engine_result['system_prompt']},
                {"role": "user", "content": engine_result['user_prompt']},
            ]

            result = proxy_request(
                "https://api.deepseek.com/v1/chat/completions",
                json.dumps({
                    "model": "deepseek-chat",
                    "messages": messages,
                    "max_tokens": 3500, "temperature": 0.7
                }).encode(),
                {"Content-Type":"application/json","Authorization":f"Bearer {DEEPSEEK_KEY}"}
            )
            content = result["choices"][0]["message"]["content"]
            usage = result.get("usage", {})
            tokens = usage.get("total_tokens", 0)
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            cost = (prompt_tokens * 0.27 + completion_tokens * 1.10) / 1_000_000
            self._json(200, {
                "content": content,
                "usage": usage,
                "cost": round(cost, 6),
                "debug": engine_result['debug'],
                "version": "v2"
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
                    "model": "deepseek-chat",
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


if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    server = HTTPServer(('0.0.0.0', 8088), SEEHandler)
    print('🔒 SEE 服务端启动: http://0.0.0.0:8088')
    print('   API Key 仅在服务端，前端不可见')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
        print('\n已停止')
