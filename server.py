"""SEE 生命印迹 - 服务端（保护 API Key）
图片识别: 豆包视觉 (doubao-seed-1-6-vision)
报告生成: DeepSeek
"""
import json, base64, ssl, os, re
from http.server import HTTPServer, SimpleHTTPRequestHandler
from http.client import HTTPSConnection
from urllib.parse import urlparse

# ===== API Keys（从环境变量读取）=====
DOUBAO_KEY = os.environ.get("DOUBAO_KEY", "")
DEEPSEEK_KEY = os.environ.get("DEEPSEEK_KEY", "")

# ===== 豆包视觉配置 =====
DOUBAO_VISION_MODEL = "doubao-seed-1-6-vision-250815"
DOUBAO_API = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"


def api_call(url, payload, headers, timeout=180):
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


def compress_image(image_b64):
    """压缩图片（使用 PIL，Linux 兼容）"""
    try:
        from io import BytesIO
        from PIL import Image
        img = Image.open(BytesIO(base64.b64decode(image_b64)))
        img = img.convert('RGB')
        img.thumbnail((800, 800), Image.LANCZOS)
        buf = BytesIO()
        img.save(buf, format='JPEG', quality=30)
        return base64.b64encode(buf.getvalue()).decode()
    except ImportError:
        # 无 PIL 则直接返回原图
        return image_b64


class SEEHandler(SimpleHTTPRequestHandler):
    def do_POST(self):
        body = self._read_body()

        if self.path == '/api/vision':
            self._vision(body)
        elif self.path == '/api/report':
            self._report(body)
        elif self.path == '/api/ocr':
            self._ocr(body)
        elif self.path == '/api/talent':
            self._talent(body)
        elif self.path == '/api/belief':
            self._belief(body)
        elif self.path == '/api/growth':
            self._growth(body)
        elif self.path == '/api/composite':
            self._composite(body)
        else:
            self.send_error(404)

    def do_GET(self):
        if self.path == '/':
            self.path = '/index.html'
        return super().do_GET()

    # ===== 图片识别（豆包视觉）=====

    def _vision(self, body):
        """豆包视觉识别 25 题 ABCD + 手写字段"""
        try:
            data = json.loads(body)
            image_b64 = data.get('image', '').split(',')[-1]
            image_b64 = compress_image(image_b64)

            payload = json.dumps({
                "model": DOUBAO_VISION_MODEL,
                "messages": [{"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + image_b64}},
                    {"type": "text", "text": VISION_PROMPT}
                ]}],
                "max_tokens": 3000
            }).encode()

            result = api_call(DOUBAO_API, payload, {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {DOUBAO_KEY}"
            })

            content = result["choices"][0]["message"]["content"]
            parsed = extract_json(content)
            usage = result.get("usage", {})
            tokens = usage.get("total_tokens", 0)
            cost = tokens / 1000 * 0.0008  # 豆包输入价

            self._json(200, {**parsed, "usage": usage, "cost": round(cost, 6)})

        except Exception as e:
            self._json(500, {"error": str(e)})

    # ===== OCR 文字识别（豆包视觉）=====

    def _ocr(self, body):
        try:
            data = json.loads(body)
            image_b64 = data.get('image', '').split(',')[-1]
            image_b64 = compress_image(image_b64)

            result = api_call(DOUBAO_API, json.dumps({
                "model": DOUBAO_VISION_MODEL,
                "messages": [{"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + image_b64}},
                    {"type": "text", "text": "请识别并提取这张图片中的所有文字内容。按原文顺序输出，保持段落结构。只输出识别的文字，不要添加任何解释。"}
                ]}],
                "max_tokens": 2048
            }).encode(), {"Content-Type": "application/json", "Authorization": f"Bearer {DOUBAO_KEY}"})

            text = result["choices"][0]["message"]["content"]
            usage = result.get("usage", {})
            tokens = usage.get("total_tokens", 0)
            self._json(200, {"text": text, "usage": usage, "cost": round(tokens / 1000 * 0.0008, 6)})
        except Exception as e:
            self._json(500, {"error": str(e)})

    # ===== 报告生成（DeepSeek）=====

    def _report(self, body):
        """DeepSeek 报告生成"""
        try:
            data = json.loads(body)
            report_type = data.get('type', 'portrait')
            portrait = data.get('portrait', {})
            base_report = data.get('baseReport', '')

            prompt = report_prompt(report_type, portrait, base_report)

            result = api_call(
                "https://api.deepseek.com/v1/chat/completions",
                json.dumps({
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 3000, "temperature": 0.7
                }).encode(),
                {"Content-Type": "application/json", "Authorization": f"Bearer {DEEPSEEK_KEY}"}
            )

            content = result["choices"][0]["message"]["content"]
            usage = result.get("usage", {})
            tokens = usage.get("total_tokens", 0)
            cost = (usage.get("prompt_tokens", 0) * 2 + usage.get("completion_tokens", 0) * 8) / 1000000

            self._json(200, {"content": content, "usage": usage, "cost": round(cost, 6)})

        except Exception as e:
            self._json(500, {"error": str(e)})

    # ===== Talent / Growth / Composite / Belief（都用 DeepSeek）=====

    KB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kb_talent')

    def _load_kb(self):
        kb = ""
        if os.path.isdir(self.KB_DIR):
            for fname in sorted(os.listdir(self.KB_DIR)):
                if fname.endswith(('.txt', '.md')):
                    try:
                        with open(os.path.join(self.KB_DIR, fname), 'r') as f:
                            kb += f"\n--- {fname} ---\n" + f.read()
                    except: pass
        return kb.strip()

    def _call_deepseek(self, prompt):
        """统一 DeepSeek 调用"""
        result = api_call(
            "https://api.deepseek.com/v1/chat/completions",
            json.dumps({
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 3000, "temperature": 0.7
            }).encode(),
            {"Content-Type": "application/json", "Authorization": f"Bearer {DEEPSEEK_KEY}"}
        )
        return result["choices"][0]["message"]["content"], result.get("usage", {})

    def _talent(self, body):
        try:
            data = json.loads(body)
            ocr_text = data.get('ocrText', '')
            report_type = data.get('type', 'portrait')
            base_report = data.get('baseReport', '')
            kb = self._load_kb()

            prompt = f"""你是先天思维特质分析师。你必须严格依据下方知识库中的理论框架和定义来分析用户数据。

⚠️ 重要规则：
1. 先完整阅读知识库内容，理解其中的特质分类体系、术语定义和分析方法
2. 再用知识库中的框架去解读用户OCR报告中的文字
3. 报告中必须引用知识库中的概念和术语，不得凭空创造

## 知识库（必须基于此分析）
{kb if kb else '（知识库待补充）'}

## 用户报告OCR内容
{ocr_text}

请生成800-1200字的报告（Markdown格式）。
结构：## 先天思维特质报告\n### 一、核心特质画像\n### 二、天赋优势分析\n### 三、成长空间与建议\n### 四、学习与发展策略"""

            content, usage = self._call_deepseek(prompt)
            self._json(200, {"content": content, "usage": usage,
                             "cost": round(usage.get("total_tokens", 0) / 1000 * 0.002, 6)})
        except Exception as e:
            self._json(500, {"error": str(e)})

    def _growth(self, body):
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

请做交叉比对分析，生成600-900字报告（Markdown格式）。
结构：## 成长比对报告\n### 一、稳定特质\n### 二、成长变化\n### 三、综合成长建议\n### 四、下一步行动指引"""

            content, usage = self._call_deepseek(prompt)
            self._json(200, {"content": content, "usage": usage,
                             "cost": round(usage.get("total_tokens", 0) / 1000 * 0.002, 6)})
        except Exception as e:
            self._json(500, {"error": str(e)})

    def _composite(self, body):
        try:
            data = json.loads(body)
            ctype = data.get('type', 'partner')
            my_portrait = data.get('myPortrait', '')
            partner_answers = data.get('partnerAnswers', {})
            partner_handwritten = data.get('partnerHandwritten', {})

            type_names = {'parent': '亲子关系合盘', 'partner': '亲密关系合盘', 'family': '家庭合盘'}

            prompt = f"""你是关系分析专家。请基于双方思维画像数据，生成一份{type_names.get(ctype, '关系合盘')}报告。

## 我的思维画像
{my_portrait[:1500]}

## 对方的思维特质
25题答案：{json.dumps(partner_answers, ensure_ascii=False)}
手写字段：{json.dumps(partner_handwritten, ensure_ascii=False)}

请生成600-900字报告（Markdown格式）。
结构：## {type_names.get(ctype, '关系合盘报告')}\n### 一、契合之处\n### 二、差异与互补\n### 三、沟通建议\n### 四、共同成长方向"""

            content, usage = self._call_deepseek(prompt)
            self._json(200, {"content": content, "usage": usage,
                             "cost": round(usage.get("total_tokens", 0) / 1000 * 0.002, 6)})
        except Exception as e:
            self._json(500, {"error": str(e)})

    def _belief(self, body):
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

请分析用户的信念系统，生成600-900字报告（Markdown格式）。
结构：## 信念系统分析报告\n### 一、核心信念识别\n### 二、限制性信念分析\n### 三、赋能信念强化\n### 四、信念转化练习"""

            content, usage = self._call_deepseek(prompt)
            self._json(200, {"content": content, "usage": usage,
                             "cost": round(usage.get("total_tokens", 0) / 1000 * 0.002, 6)})
        except Exception as e:
            self._json(500, {"error": str(e)})

    # ===== HTTP helpers =====

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


# ===== Prompts =====

VISION_PROMPT = """你是一个答题卡识别器。查看这张SEE思维导图照片，判断25道选择题(q01-q25)各自选了A/B/C/D中的哪一个。

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


def report_prompt(t, p, base):
    prompts = {
        'portrait': f"""你是思维特质分析师。基于以下SEE思维画像数据，生成"基础思维画像报告"（800-1200字，Markdown）。

数据：{json.dumps(p, ensure_ascii=False)}

结构：## 基础思维画像报告\n### 一、核心思维模式\n### 二、各维度解读\n### 三、综合优势\n### 四、潜在盲区\n### 五、成长建议""",
        'communication': f"""你是关系沟通顾问。基于基础画像，生成"沟通与关系报告"（600-900字，Markdown）。

画像摘要：{p.get('traits', [])}

结构：## 沟通与关系报告\n### 一、你的沟通风格\n### 二、与不同类型人沟通建议\n### 三、亲密关系中的你\n### 四、团队协作建议""",
        'action': f"""你是成长教练。基于基础画像，生成"成长行动计划报告"（600-900字，Markdown）。

画像摘要：{p.get('traits', [])}

结构：## 成长行动计划报告\n### 一、21天核心练习\n### 二、每周行动清单\n### 三、推荐学习资源\n### 四、自我检视问题""",
    }
    return prompts.get(t, prompts['portrait'])


def extract_json(text):
    match = re.search(r'\{[\s\S]*\}', text)
    if not match:
        raise ValueError(f"无法解析JSON: {text[:100]}")
    return json.loads(match.group())


# ===== 启动 =====

if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    server = HTTPServer(('0.0.0.0', 8088), SEEHandler)
    print('SEE 服务端启动: http://0.0.0.0:8088')
    print('  图片识别: 豆包视觉 (doubao-seed-1-6-vision)')
    print('  报告生成: DeepSeek')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
        print('\n已停止')
