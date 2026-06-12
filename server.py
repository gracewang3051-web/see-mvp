"""SEE 生命印迹 - 服务端
OCR: 浏览器端 Tesseract.js（无需服务端 AI）
报告生成: DeepSeek
"""
import json, ssl, os, re
from http.server import HTTPServer, SimpleHTTPRequestHandler
from http.client import HTTPSConnection
from urllib.parse import urlparse

# ===== 仅需 DeepSeek Key =====
DEEPSEEK_KEY = os.environ.get("DEEPSEEK_KEY", "")


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


class SEEHandler(SimpleHTTPRequestHandler):
    def do_POST(self):
        body = self._read_body()
        try:
            if self.path == '/api/report':
                self._report(body)
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
        except Exception as e:
            self._json(500, {"error": str(e)})

    def do_GET(self):
        if self.path == '/':
            self.path = '/index.html'
        return super().do_GET()

    KB_TALENT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kb_talent')
    KB_PORTRAIT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kb_portrait')

    def _load_kb(self, dirs=None):
        """加载知识库，默认 kb_talent + kb_portrait"""
        if dirs is None:
            dirs = [self.KB_TALENT, self.KB_PORTRAIT]
        kb = ""
        for kdir in dirs:
            if os.path.isdir(kdir):
                for fname in sorted(os.listdir(kdir)):
                    if fname.endswith(('.txt', '.md')):
                        try:
                            with open(os.path.join(kdir, fname), 'r') as f:
                                kb += f"\n--- {fname} ---\n" + f.read()
                        except: pass
        return kb.strip()

    def _call_deepseek(self, prompt):
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

    def _report(self, body):
        data = json.loads(body)
        kb = self._load_kb([self.KB_PORTRAIT])
        prompt = REPORT_PROMPTS.get(data.get('type', 'portrait'), REPORT_PROMPTS['portrait'])(
            data.get('portrait', {}), data.get('baseReport', ''), kb)
        content, usage = self._call_deepseek(prompt)
        self._json(200, {"content": content, "usage": usage,
                         "cost": round(usage.get("total_tokens", 0) / 1000 * 0.002, 6)})

    def _talent(self, body):
        data = json.loads(body)
        kb = self._load_kb()
        prompt = f"""你是先天思维特质分析师。严格依据下方知识库框架分析用户数据。

## 知识库
{kb if kb else '（知识库待补充）'}

## 用户OCR内容
{data.get('ocrText', '')}

生成800-1200字Markdown报告：
## 先天思维特质报告
### 一、核心特质画像
### 二、天赋优势分析
### 三、成长空间与建议
### 四、学习与发展策略"""
        content, usage = self._call_deepseek(prompt)
        self._json(200, {"content": content, "usage": usage,
                         "cost": round(usage.get("total_tokens", 0) / 1000 * 0.002, 6)})

    def _growth(self, body):
        data = json.loads(body)
        kb = self._load_kb()
        prompt = f"""对比两份报告，做交叉分析。

思维画像: {data.get('portrait', '')[:1500]}
先天特质: {data.get('talent', '')[:1500]}
知识库: {kb[:1000] if kb else '无'}

生成600-900字Markdown：
## 成长比对报告
### 一、稳定特质
### 二、成长变化
### 三、综合建议
### 四、下一步行动"""
        content, usage = self._call_deepseek(prompt)
        self._json(200, {"content": content, "usage": usage,
                         "cost": round(usage.get("total_tokens", 0) / 1000 * 0.002, 6)})

    def _composite(self, body):
        data = json.loads(body)
        ctype = data.get('type', 'partner')
        names = {'parent': '亲子关系合盘', 'partner': '亲密关系合盘', 'family': '家庭合盘'}
        prompt = f"""生成{names.get(ctype, '关系合盘')}报告。

我的画像: {data.get('myPortrait', '')[:1500]}
对方答案: {json.dumps(data.get('partnerAnswers', {}), ensure_ascii=False)}
手写字段: {json.dumps(data.get('partnerHandwritten', {}), ensure_ascii=False)}

生成600-900字Markdown：
## {names.get(ctype, '关系合盘报告')}
### 一、契合之处
### 二、差异与互补
### 三、沟通建议
### 四、共同成长方向"""
        content, usage = self._call_deepseek(prompt)
        self._json(200, {"content": content, "usage": usage,
                         "cost": round(usage.get("total_tokens", 0) / 1000 * 0.002, 6)})

    def _belief(self, body):
        data = json.loads(body)
        kb = self._load_kb()
        prompt = f"""分析信念系统。

知识库: {kb[:2000] if kb else '无'}
已有报告: {data.get('ocrText', '')[:1000]}
用户描述: {data.get('input', '')}

生成600-900字Markdown：
## 信念系统分析报告
### 一、核心信念识别
### 二、限制性信念分析
### 三、赋能信念强化
### 四、信念转化练习"""
        content, usage = self._call_deepseek(prompt)
        self._json(200, {"content": content, "usage": usage,
                         "cost": round(usage.get("total_tokens", 0) / 1000 * 0.002, 6)})

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


REPORT_PROMPTS = {
    'portrait': lambda p, b, kb: f"""你是思维特质分析师。严格依据下方知识库框架分析数据。

## 知识库（SEE卡应用手册）
{kb[:4000] if kb else '（知识库待补充）'}

## 用户思维画像数据
{json.dumps(p, ensure_ascii=False)}

生成800-1200字Markdown报告，必须引用知识库中的概念和术语：
## 基础思维画像报告
### 一、核心思维模式
### 二、各维度解读
### 三、综合优势
### 四、潜在盲区
### 五、成长建议""",
    'communication': lambda p, b, kb: f"""生成沟通与关系报告（600-900字Markdown）。

画像：{p.get('traits', [])}

结构：
## 沟通与关系报告
### 一、沟通风格
### 二、与不同类型人的沟通建议
### 三、亲密关系中的你
### 四、团队协作建议""",
    'action': lambda p, b, kb: f"""生成成长行动计划报告（600-900字Markdown）。

画像：{p.get('traits', [])}

结构：
## 成长行动计划报告
### 一、21天核心练习
### 二、每周行动清单
### 三、推荐学习资源
### 四、自我检视问题""",
}


if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    server = HTTPServer(('0.0.0.0', 8088), SEEHandler)
    print('SEE 服务端启动: http://0.0.0.0:8088')
    print('  OCR: 浏览器端 Tesseract.js')
    print('  报告: DeepSeek')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
        print('\n已停止')
