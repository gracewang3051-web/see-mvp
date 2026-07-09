"""SEE 生命印迹 - 本地测试服务端（保护 API Key）"""
import json, base64, re, ssl, os, io, tempfile, sys, threading, time, uuid, sqlite3, traceback
from weasyprint import HTML
from http.server import HTTPServer, SimpleHTTPRequestHandler
from http.client import HTTPSConnection
from urllib.parse import urlparse, urlencode
from socketserver import ThreadingMixIn
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine.orchestrator import CognitiveEngine
from engine.see_card import interpret_see_card, load_see_card_context

# ===== API Keys（环境变量注入，不写入代码）=====
DEEPSEEK_KEY = os.environ.get('DEEPSEEK_KEY', '')
BAIDU_OCR_API_KEY = os.environ.get('BAIDU_OCR_API_KEY', '')
BAIDU_OCR_SECRET_KEY = os.environ.get('BAIDU_OCR_SECRET_KEY', '')

_BAIDU_OCR_TOKEN = ''
_TALENT_JOBS = {}
_TALENT_JOB_LOCK = threading.Lock()

# ===== SQLite 数据库 =====
_DB_LOCK = threading.Lock()
_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'see_data.db')

def _init_db():
    """创建数据库表（幂等）。"""
    with _DB_LOCK:
        conn = sqlite3.connect(_DB_PATH)
        conn.execute('''CREATE TABLE IF NOT EXISTS users (
            code TEXT PRIMARY KEY, name TEXT DEFAULT '', max_reports INTEGER DEFAULT 20,
            created_at TEXT DEFAULT (datetime('now')), last_active TEXT DEFAULT '')''')
        conn.execute('''CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_code TEXT NOT NULL,
            type TEXT NOT NULL, sections TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')))''')
        conn.execute('''CREATE TABLE IF NOT EXISTS qr_codes (
            id TEXT PRIMARY KEY, name TEXT DEFAULT '', url TEXT DEFAULT '',
            max_users INTEGER DEFAULT 10, max_reports INTEGER DEFAULT 20,
            used_users INTEGER DEFAULT 0, used_reports INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active', expires TEXT, created_at TEXT DEFAULT (datetime('now')))''')
        conn.execute('''CREATE TABLE IF NOT EXISTS activation_codes (
            code TEXT PRIMARY KEY, bonus_type TEXT DEFAULT '', extra_reports INTEGER DEFAULT 10,
            used INTEGER DEFAULT 0, used_at TEXT, created_at TEXT DEFAULT (datetime('now')))''')
        conn.execute('''CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT, time TEXT, code TEXT DEFAULT '',
            questions INTEGER DEFAULT 0, reports INTEGER DEFAULT 0, cost REAL DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')))''')
        conn.commit()
        conn.close()

# ===== 区域模板（1280×1920 参考尺寸，按实际图片等比缩放）=====
REGION_REF_W = 1280
REGION_REF_H = 1920

# 每个区域 key → 裁切坐标 (x, y, width, height)，仅包含「值」区域
REGION_TEMPLATE = {
    # 总览区
    'trc':                  (176, 498, 230, 68),
    'atd':                  (411, 498, 225, 68),
    'personality_type':     (640, 498, 230, 68),
    'trc_average':          (896, 498, 231, 68),
    # 学习通道
    'auditory_pct':         (176, 652, 150, 44),
    'visual_pct':           (333, 652, 144, 44),
    'kinesthetic_pct':      (484, 652, 152, 44),
    # 行为 / 脑平衡
    'behavior_mode':        (640, 630, 230, 66),
    'brain_balance':        (896, 630, 231, 66),
    # 精神功能
    'spirit_communication': (216, 1430, 128, 58),
    'spirit_creative':      (355, 1430, 180, 58),
    # 思维功能
    'thinking_logic':       (240, 963,  145, 52),
    'thinking_spatial':     (240, 1070, 155, 52),
    # 体觉功能
    'body_discrimination':  (526, 790,  118, 50),
    'body_feeling':         (666, 790,  126, 50),
    # 听觉功能
    'auditory_discrimination': (954, 984,  150, 54),
    'auditory_feeling':        (954, 1070, 150, 54),
    # 视觉功能
    'visual_discrimination':   (848, 1430, 134, 58),
    'visual_feeling':          (968, 1430, 162, 58),
}

def _get_image_size(b64_data):
    """从 base64 图片数据中解码宽高（无需 PIL）。支持 JPEG / PNG。"""
    import struct
    raw = base64.b64decode(b64_data)
    if raw[:2] == b'\xff\xd8':           # JPEG
        i = 2
        while i < len(raw) - 9:
            if raw[i] != 0xff:
                break
            marker = raw[i + 1]
            if marker in (0xc0, 0xc2):    # SOF0 / SOF2
                h = struct.unpack('>H', raw[i + 5:i + 7])[0]
                w = struct.unpack('>H', raw[i + 7:i + 9])[0]
                return w, h
            i += 2 + struct.unpack('>H', raw[i + 2:i + 4])[0]
    elif raw[:8] == b'\x89PNG\r\n\x1a\n':  # PNG
        w = struct.unpack('>I', raw[16:20])[0]
        h = struct.unpack('>I', raw[20:24])[0]
        return w, h
    return None, None

def _scale_region(rx, ry, rw, rh, img_w, img_h):
    """将模板坐标按实际图片尺寸等比缩放。"""
    sx = img_w / REGION_REF_W if REGION_REF_W else 1
    sy = img_h / REGION_REF_H if REGION_REF_H else 1
    return (int(rx * sx), int(ry * sy), int(rw * sx), int(rh * sy))

def _normalize_image_for_baidu_ocr(image_b64):
    """压缩并缩放图片，降低百度 OCR 的 image size error 概率。"""
    import base64 as _b64
    import io
    try:
        from PIL import Image
    except Exception:
        return image_b64

    raw = _b64.b64decode(image_b64)
    with Image.open(io.BytesIO(raw)) as img:
        img = img.convert('RGB')
        max_side = 1600
        if max(img.size) > max_side:
            img.thumbnail((max_side, max_side), Image.LANCZOS)
        out = io.BytesIO()
        img.save(out, format='JPEG', quality=85, optimize=True)
        return _b64.b64encode(out.getvalue()).decode('ascii')

# 中文标签 → field key 映射（按模板 report 固定格式）
_LABEL_TO_KEY = {
    '学习潜能TRC': 'trc', 'TRC': 'trc',
    '反应速度ATD': 'atd', 'ATD': 'atd',
    '性格类型': 'personality_type',
    'TRC平均值': 'trc_average',
    '听觉型': 'auditory_pct',
    '视觉型': 'visual_pct',
    '体觉型': 'kinesthetic_pct',
    '行为模式': 'behavior_mode',
    '左右脑分布': 'brain_balance',
    '沟通管理': 'spirit_communication',
    '计划判断': 'spirit_communication',
    '创造领导': 'spirit_creative',
    '目标憧憬': 'spirit_creative',
    '逻辑推理': 'thinking_logic',
    '语言功能': 'thinking_logic',
    '空间心像': 'thinking_spatial',
    '构思拟想': 'thinking_spatial',
    '体觉辨识': 'body_discrimination',
    '操作理解': 'body_discrimination',
    '体觉感受': 'body_feeling',
    '艺术欣赏': 'body_feeling',
    '听觉辨识': 'auditory_discrimination',
    '语言理解': 'auditory_discrimination',
    '听觉感受': 'auditory_feeling',
    '音乐欣赏': 'auditory_feeling',
    '视觉辨识': 'visual_discrimination',
    '观察理解': 'visual_discrimination',
    '视觉感受': 'visual_feeling',
    '图像欣赏': 'visual_feeling',
    # OCR 常见错字
    '休觉感受': 'body_feeling',
    '休觉辨识': 'body_discrimination',
}

def _extract_region_values(words, image_b64):
    """基于文字匹配 + 位置辅助：标签下方的值块 → {key: value_text}。

    先用现有 merge 逻辑把「标签 + 下方值」合并成对，
    再按中文标签文本映射到 field key。
    对未能合并的独立行，尝试直接匹配标签文本。

    2026-07-09 修复：
    - 只搜索下方（不再区分左右排列），dy 上限 80→160，X 容差 60→120
    - 性格类型允许含中文的值块
    """
    result = {}

    # 1. 按 Y 排序（10px 容差同行，同行左到右）
    sorted_w = sorted(words, key=lambda w: (
        round(w.get('location', {}).get('top', 0) / 10) * 10,
        w.get('location', {}).get('left', 0)
    ))
    word_list = [(w.get('words', '').strip(), w.get('location', {})) for w in sorted_w if w.get('words', '').strip()]

    def _is_value_block(text, allow_cjk=False):
        """判断是否为值块。allow_cjk=True 时允许中文（用于性格类型等）。"""
        if allow_cjk:
            return bool(re.match(r'^[一-鿿A-Za-z\d\s]{2,7}$', text))
        return bool(re.match(r'^[\d\s.WwLlRrXxNnSsCcPpTtDdIiEeFfAaKkUuHh%+\-]+$', text))

    # 2. 标签 + 值块合并（统一在下方搜）
    merged_pairs = []  # [(label_text, value_text)]
    used = set()
    for i, (cur, loc) in enumerate(word_list):
        if i in used:
            continue
        used.add(i)
        cx, cy = loc.get('left', 0), loc.get('top', 0)

        is_personality_label = (cur == '性格类型')
        allow_cjk = is_personality_label

        best_j, best_dy = None, 999
        for j, (nxt, loc2) in enumerate(word_list):
            if j in used:
                continue
            ny = loc2.get('top', 0)
            nx = loc2.get('left', 0)

            # 只搜下方：dy 5~80px，X 对齐 ±60px
            if ny <= cy + 5:
                continue
            dy = ny - cy
            if dy > 120:
                continue
            if abs(nx - cx) > 100:
                continue
            if not _is_value_block(nxt, allow_cjk=allow_cjk):
                continue
            if dy < best_dy:
                best_dy = dy
                best_j = j

        if best_j is not None:
            merged_pairs.append((cur, word_list[best_j][0]))
            used.add(best_j)
        else:
            merged_pairs.append((cur, None))

        # 3. 按标签文字映射到 key
    for label, value in merged_pairs:
        key = _LABEL_TO_KEY.get(label)
        if key:
            if value:
                result[key] = value

    # 3b. 拆分多值串（如「20 Wsc 22 Wc」→ 两个独立值），按 X 就近分配
    #     按 X 坐标分配（左边=第一个值）
    multi_val_pattern = re.compile(r'^(\d+\s*\w+)\s+(\d+\s*\w+)$')
    for i, (label, value) in enumerate(merged_pairs):
        if not value:
            continue
        m = multi_val_pattern.match(value)
        if not m:
            continue
        # 找到该 label 的位置
        label_x, label_y = None, None
        for t, loc in word_list:
            if t == label:
                label_x = loc.get('left', 0) + loc.get('width', 0) / 2
                label_y = loc.get('top', 0)
                break
        if label_x is None:
            continue


        # 找同行未匹配 label（Y 差 ≤ 40px），选 X 最近的
        best_j, best_dx = None, 999
        other_x_for_split, other_y_for_split = None, None
        for j, (other_label, other_val) in enumerate(merged_pairs):
            if other_val or other_label == label:
                continue
            other_x, other_y = None, None
            for t, loc in word_list:
                if t == other_label:
                    other_x = loc.get('left', 0) + loc.get('width', 0) / 2
                    other_y = loc.get('top', 0)
                    break
            if other_x is None or other_y is None:
                continue
            if label_y and abs(other_y - label_y) > 40:
                continue
            dx = abs(other_x - label_x)
            if dx < best_dx:
                best_dx = dx
                best_j = j
                other_x_for_split = other_x
                other_y_for_split = other_y
        if best_j is not None:
            other_label, _ = merged_pairs[best_j]
            val1, val2 = m.group(1), m.group(2)
            if label_x < other_x_for_split:
                merged_pairs[i] = (label, val1)
                merged_pairs[best_j] = (other_label, val2)
            else:
                merged_pairs[i] = (label, val2)
                merged_pairs[best_j] = (other_label, val1)
            break

    # 4. 处理本身就是中文值的情况（行为模式、脑平衡、性格类型）
    for label, value in merged_pairs:
        if label in ('动机型', '构思型', '均衡型'):
            result.setdefault('behavior_mode', label)
        if label in ('左脑型', '右脑型', '均衡型') and result.get('brain_balance') is None:
            result.setdefault('brain_balance', label)

    # 5. 对未能匹配 personality_type 的情况，扫一遍找逆思/认知等类型词
    #    同时支持更宽泛的性格类型值（如「认知模仿型」「开放整合型」等复合型）
    if 'personality_type' not in result:
        _personality_types = [
            '逆思型', '认知型', '模仿型', '开放型', '整合型',
            '认知模仿型', '开放整合型', '逆思认知型', '模仿开放型',
        ]
        for text, _ in word_list:
            if text in _personality_types:
                result['personality_type'] = text
                break
        # fallback: 匹配含「型」字的短文本（2-7字）作为性格类型
        if 'personality_type' not in result:
            for text, _ in word_list:
                if re.match(r'^[\u4e00-\u9fffA-Za-z]{2,7}$', text) and '型' in text:
                    result['personality_type'] = text
                    break

    # 5b. 拆分已分配的多值串（如 spirit_communication="20 Wsc 22 Wc" → split to spirit_creative）
    _split_keys = [('spirit_communication', 'spirit_creative'),
                   ('spirit_creative', 'spirit_communication')]
    for _k1, _k2 in _split_keys:
        if _k1 in result and _k2 not in result:
            _m = re.match(r'^(\d+\s*\w+)\s+(\d+\s*\w+)$', result[_k1])
            if _m:
                # Find which label is more left — assign left val to left label, right val to right label
                _k1_labels = [l for l in _LABEL_TO_KEY if _LABEL_TO_KEY[l] == _k1]
                _k2_labels = [l for l in _LABEL_TO_KEY if _LABEL_TO_KEY[l] == _k2]
                _k1_x = None
                _k2_x = None
                for t, loc in word_list:
                    if t in _k1_labels and _k1_x is None:
                        _k1_x = loc.get('left', 0)
                    if t in _k2_labels and _k2_x is None:
                        _k2_x = loc.get('left', 0)
                if _k1_x is not None and _k2_x is not None:
                    if _k1_x < _k2_x:
                        result[_k1] = _m.group(1)
                        result[_k2] = _m.group(2)
                    else:
                        result[_k1] = _m.group(2)
                        result[_k2] = _m.group(1)
                break

    # 6. Fallback: 通道百分比 X 就近匹配（合并失败时）
    pct_words = [(t, loc) for t, loc in word_list if re.match(r'^\d+\.?\d*\s*%$', t)]
    channel_types = [('听觉型', 'auditory_pct'), ('视觉型', 'visual_pct'), ('体觉型', 'kinesthetic_pct')]
    for ch_label, ch_key in channel_types:
        if ch_key in result:
            continue
        ch_loc = None
        for t, loc in word_list:
            if t == ch_label:
                ch_loc = loc
                break
        if not ch_loc:
            continue
        ch_x = ch_loc.get('left', 0)
        best_pct, best_dx = None, 999
        for pct_text, pct_loc in pct_words:
            if pct_text in result.values():
                continue
            dx = abs(pct_loc.get('left', 0) - ch_x)
            if dx < best_dx:
                best_dx = dx
                best_pct = pct_text
        if best_pct:
            result[ch_key] = best_pct

    return result

def proxy_request(url, payload, headers, timeout=180):
    """直连 API"""
    parsed = urlparse(url)
    ctx = ssl.create_default_context()
    conn = HTTPSConnection(parsed.hostname, parsed.port or 443, timeout=timeout, context=ctx)
    try:
        conn.request("POST", parsed.path + ("?" + parsed.query if parsed.query else ""),
                     body=payload, headers=headers)
        resp = conn.getresponse()
        data = resp.read().decode()
    except Exception:
        traceback.print_exc()
        raise
    finally:
        conn.close()
    if resp.status != 200:
        snippet = data.strip().replace('\n', ' ')[:300]
        raise Exception(f"upstream HTTP {resp.status} {resp.reason}: {snippet or 'empty response'}")
    if not data.strip():
        raise Exception("upstream returned empty response")
    try:
        result = json.loads(data)
    except json.JSONDecodeError as e:
        snippet = data.strip().replace('\n', ' ')[:300]
        raise Exception(f"upstream returned non-JSON response: {snippet or str(e)}")
    if "error" in result:
        raise Exception(result["error"].get("message", json.dumps(result["error"])))
    return result

def _deepseek_chat(messages, max_tokens=3000, temperature=0.7):
    """Call DeepSeek with a local config check so missing keys fail clearly."""
    if not DEEPSEEK_KEY or not DEEPSEEK_KEY.startswith('sk-'):
        raise ValueError("DeepSeek API Key 未配置。请设置环境变量 DEEPSEEK_KEY。")
    return proxy_request(
        "https://api.deepseek.com/v1/chat/completions",
        json.dumps({
            "model": "deepseek-v4-pro",
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }).encode(),
        {"Content-Type": "application/json", "Authorization": f"Bearer {DEEPSEEK_KEY}"}
    )

def _deepseek_cost(usage):
    return (usage.get("prompt_tokens", 0) * 0.55 + usage.get("completion_tokens", 0) * 2.19) / 1000000

def _trim_incomplete(text):
    """Remove trailing incomplete sentence/fragment from LLM output."""
    text = text.rstrip()
    if not text:
        return text

    # Remove dangling markdown markers at the end.
    text = re.sub(r'(?:\n\s*)+(?:#+\s*|[-*]\s*)$', '', text)
    text = re.sub(r'\n+#+\s*$', '', text)

    # If the final line looks like a fragment, drop it.
    lines = text.split('\n')
    while len(lines) > 1:
        last = lines[-1].strip()
        if not last:
            lines.pop()
            continue
        if len(last) <= 60 and not re.search(r'[。！？.!?；;：:」』"）\)】]$', last):
            lines.pop()
            continue
        break
    text = '\n'.join(lines).rstrip()

    # If the text still ends without a terminal mark, trim back to the last
    # complete sentence boundary near the end.
    if text and not re.search(r'[。！？.!?；;：:」』"）\)】]$', text):
        tail = text[-240:]
        boundary = max(
            tail.rfind('。'),
            tail.rfind('！'),
            tail.rfind('？'),
            tail.rfind('.'),
            tail.rfind('!'),
            tail.rfind('?'),
            tail.rfind('；'),
            tail.rfind(';'),
            tail.rfind('：'),
            tail.rfind(':'),
        )
        if boundary >= 0:
            text = text[:-len(tail) + boundary + 1].rstrip()

    # Remove trailing junk characters.
    text = re.sub(r'[，,、\s]*$', '', text)
    return text


def _markdown_to_html(title, markdown):
    """Convert markdown to a styled HTML page for wkhtmltopdf."""
    import re as _re

    if isinstance(markdown, bytes):
        markdown = markdown.decode('utf-8', errors='ignore')
    markdown = str(markdown)

    html_body = markdown.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    html_body = _re.sub(r'```(\w*)\n(.*?)```', r'<pre><code>\2</code></pre>', html_body, flags=_re.DOTALL)
    html_body = _re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html_body)
    html_body = _re.sub(r'`(.+?)`', r'<code>\1</code>', html_body)
    html_body = _re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', html_body)
    html_body = _re.sub(r'^#### (.+)$', r'<h4>\1</h4>', html_body, flags=_re.MULTILINE)
    html_body = _re.sub(r'^### (.+)$', r'<h3>\1</h3>', html_body, flags=_re.MULTILINE)
    html_body = _re.sub(r'^## (.+)$', r'<h2>\1</h2>', html_body, flags=_re.MULTILINE)
    html_body = _re.sub(r'^# (.+)$', r'<h1>\1</h1>', html_body, flags=_re.MULTILINE)
    html_body = _re.sub(r'^- (.+)$', r'<li>\1</li>', html_body, flags=_re.MULTILINE)
    html_body = _re.sub(r'(<li>.*?</li>\n?)+', r'<ul>\g<0></ul>', html_body)
    paragraphs = []
    for block in _re.split(r'\n\s*\n', html_body):
        block = block.strip()
        if block and not block.startswith('<'):
            paragraphs.append('<p>' + block.replace('\n', '<br>') + '</p>')
        elif block:
            paragraphs.append(block)
    html_body = '\n'.join(paragraphs)

    title_safe = str(title or 'SEE Report').replace('&', '&amp;').replace('<', '&lt;')

    return '''<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>''' + title_safe + '''</title>
<style>
  body { font-family: "WenQuanYi Zen Hei", "Noto Sans CJK SC", "PingFang SC",
         "Microsoft YaHei", sans-serif; max-width: 720px; margin: 30px auto;
         padding: 20px; line-height: 1.9; color: #333; font-size: 14px; }
  h1 { font-size: 1.5em; border-bottom: 2px solid #333; padding-bottom: 6px; }
  h2 { font-size: 1.2em; margin-top: 24px; }
  h3 { font-size: 1.05em; }
  pre { background: #f5f5f5; padding: 12px; border-radius: 4px; overflow-x: auto; }
  code { background: #f0f0f0; padding: 1px 4px; border-radius: 2px; }
  pre code { background: none; padding: 0; }
  li { margin: 4px 0; }
</style></head>
<body><h1>''' + title_safe + '''</h1>
''' + html_body + '''
</body></html>'''


def _generate_pdf(title, markdown):
    """Generate Chinese PDF from markdown using weasyprint (zero system deps)."""
    html = _markdown_to_html(title, markdown)
    buf = io.BytesIO()
    HTML(string=html).write_pdf(buf)
    buf.seek(0)
    return buf.read()


def _pdf_content_disposition(title):
    """Build an ASCII-safe Content-Disposition header value.

    http.server encodes header values as latin-1, so raw Chinese filenames
    will raise before the response is sent. We keep an ASCII fallback filename
    and add an RFC 5987 filename* parameter for browsers that support it.
    """
    from urllib.parse import quote

    safe = re.sub(r'[^A-Za-z0-9._-]+', '_', str(title or 'SEE_Report')).strip('._-')
    if not safe:
      safe = 'SEE_Report'
    utf8_name = quote(f'{title}.pdf' if title else 'SEE_Report.pdf', safe='')
    return f'attachment; filename="{safe}.pdf"; filename*=UTF-8\'\'{utf8_name}'


class SEEHandler(SimpleHTTPRequestHandler):
    def do_POST(self):
        body = self._read_body()

        if self.path == '/api/vision':
            self._proxy_vision(body)
        elif self.path == '/api/report':
            self._proxy_report(body)
        elif self.path == '/api/ocr':
            self._proxy_ocr(body)
        elif self.path == '/api/baidu-ocr':
            self._proxy_baidu_ocr(body)
        elif self.path == '/api/extract-metrics':
            self._proxy_extract_metrics(body)
        elif self.path == '/api/talent':
            self._proxy_talent(body)
        elif self.path == '/api/talent-v2':
            self._proxy_talent_v2(body)
        elif self.path == '/api/talent-job':
            self._start_talent_job(body)
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
        elif self.path == '/api/export-doc':
            self._export_doc(body)
        elif self.path == '/api/db/reports':
            self._db_save_report(body)
        elif self.path == '/api/db/users':
            self._db_save_user(body)
        elif self.path == '/api/db/qr-codes':
            self._db_save_qrcode(body)
        elif self.path == '/api/db/activation-codes':
            self._db_save_actcode(body)
        elif self.path == '/api/db/records':
            self._db_save_record(body)
        else:
            self.send_error(404)

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()

    def do_GET(self):
        if self.path == '/':
            self.path = '/index.html'
        elif self.path == '/health':
            self._json(200, {"ok": True})
            return
        elif self.path.startswith('/api/talent-job'):
            self._get_talent_job()
            return
        elif self.path.startswith('/api/db/reports'):
            self._db_get_reports()
            return
        elif self.path.startswith('/api/db/users'):
            self._db_get_users()
            return
        elif self.path.startswith('/api/db/qr-codes'):
            self._db_get_qrcodes()
            return
        elif self.path.startswith('/api/db/activation-codes'):
            self._db_get_actcodes()
            return
        elif self.path.startswith('/api/db/records'):
            self._db_get_records()
            return
        return super().do_GET()

    def list_directory(self, path):
        self.send_error(403, "Directory listing disabled")
        return None

    def _proxy_vision(self, body):
        """云端识图已停用"""
        self._json(503, {"error": "云端OCR已停用，请手动输入或粘贴文本", "stage": "disabled"})
        return
    def _proxy_vision_legacy(self, body):
        self._json(503, {"error": "旧云端识图代理已停用，请使用 /api/baidu-ocr", "stage": "disabled"})

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
        if not length:
            return b''
        data = self.rfile.read(length)
        while len(data) < length:
            chunk = self.rfile.read(length - len(data))
            if not chunk:
                break
            data += chunk
        return data

    def _json(self, code, data):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    # ===== SQLite 数据库 API =====
    def _db_save_report(self, body):
        """POST /api/db/reports — 保存一份报告"""
        try:
            data = json.loads(body)
            code = data.get('code', '').strip()
            rtype = data.get('type', 'portrait')
            sections = data.get('sections', {})
            if not code: return self._json(400, {"error": "缺少用户码"})
            with _DB_LOCK:
                conn = sqlite3.connect(_DB_PATH)
                conn.execute("INSERT OR IGNORE INTO users (code) VALUES (?)", (code,))
                conn.execute("UPDATE users SET last_active=datetime('now') WHERE code=?", (code,))
                conn.execute("INSERT INTO reports (user_code, type, sections) VALUES (?,?,?)",
                             (code, rtype, json.dumps(sections, ensure_ascii=False)))
                conn.commit()
                conn.close()
            self._json(200, {"success": True})
        except Exception as e:
            self._json(500, {"error": str(e)})

    def _db_get_reports(self):
        """GET /api/db/reports?code=PX001 — 获取用户所有报告"""
        from urllib.parse import parse_qs
        try:
            qs = parse_qs(urlparse(self.path).query)
            code = (qs.get('code') or [''])[0].strip()
            if not code: return self._json(400, {"error": "缺少用户码"})
            with _DB_LOCK:
                conn = sqlite3.connect(_DB_PATH)
                rows = conn.execute(
                    "SELECT id, user_code, type, sections, created_at FROM reports WHERE user_code=? ORDER BY id ASC",
                    (code,)).fetchall()
                conn.close()
            versions = []
            for row in rows:
                try:
                    sec = json.loads(row[3])
                except Exception:
                    sec = {}
                versions.append({"time": row[4], "type": row[2], "sections": sec})
            self._json(200, {"code": code, "versions": versions})
        except Exception as e:
            self._json(500, {"error": str(e)})

    def _db_get_users(self):
        """GET /api/db/users — Admin 取用户列表（含报告计数）"""
        try:
            with _DB_LOCK:
                conn = sqlite3.connect(_DB_PATH)
                users = conn.execute(
                    "SELECT u.code, u.name, u.max_reports, u.created_at, u.last_active, COUNT(r.id) as cnt "
                    "FROM users u LEFT JOIN reports r ON u.code=r.user_code GROUP BY u.code ORDER BY u.last_active DESC"
                ).fetchall()
                conn.close()
            result = []
            for row in users:
                result.append({
                    "code": row[0], "name": row[1], "maxReports": row[2],
                    "createdAt": row[3], "lastActive": row[4], "reports": row[5]
                })
            self._json(200, {"users": result})
        except Exception as e:
            self._json(500, {"error": str(e)})

    def _db_save_user(self, body):
        """POST /api/db/users — Admin 增/改/删用户 {action, code, name, maxReports}"""
        try:
            data = json.loads(body)
            action = data.get('action', 'upsert')
            code = data.get('code', '').strip()
            if not code: return self._json(400, {"error": "缺少用户码"})
            with _DB_LOCK:
                conn = sqlite3.connect(_DB_PATH)
                if action == 'delete':
                    conn.execute("DELETE FROM reports WHERE user_code=?", (code,))
                    conn.execute("DELETE FROM users WHERE code=?", (code,))
                else:
                    name = data.get('name', code)
                    max_reports = int(data.get('maxReports', 20))
                    # 兼容旧版 SQLite < 3.24（如 CentOS 7）：先 UPDATE，无行影响再 INSERT
                    cur = conn.execute("UPDATE users SET name=?, max_reports=? WHERE code=?", (name, max_reports, code))
                    if cur.rowcount == 0:
                        conn.execute("INSERT INTO users (code, name, max_reports) VALUES (?,?,?)",
                                     (code, name, max_reports))
                conn.commit()
                conn.close()
            self._json(200, {"success": True})
        except Exception as e:
            self._json(500, {"error": str(e)})

    # ===== QR Codes API =====
    def _db_get_qrcodes(self):
        try:
            with _DB_LOCK:
                conn = sqlite3.connect(_DB_PATH)
                rows = conn.execute("SELECT id,name,url,max_users,max_reports,used_users,used_reports,status,expires,created_at FROM qr_codes ORDER BY created_at DESC").fetchall()
                conn.close()
            result = [{"id":r[0],"name":r[1],"url":r[2],"maxUsers":r[3],"maxReports":r[4],"usedUsers":r[5],"usedReports":r[6],"status":r[7],"expires":r[8],"createdAt":r[9]} for r in rows]
            self._json(200, {"codes": result})
        except Exception as e:
            self._json(500, {"error": str(e)})

    def _db_save_qrcode(self, body):
        try:
            data = json.loads(body)
            action = data.get('action', 'upsert')
            with _DB_LOCK:
                conn = sqlite3.connect(_DB_PATH)
                if action == 'delete':
                    conn.execute("DELETE FROM qr_codes WHERE id=?", (data.get('id',''),))
                else:
                    qid = data.get('id','')
                    cur = conn.execute("UPDATE qr_codes SET name=?,url=?,max_users=?,max_reports=?,used_users=?,used_reports=?,status=?,expires=? WHERE id=?",
                        (data.get('name',''), data.get('url',''), data.get('maxUsers',10), data.get('maxReports',20), data.get('usedUsers',0), data.get('usedReports',0), data.get('status','active'), data.get('expires',''), qid))
                    if cur.rowcount == 0:
                        conn.execute("INSERT INTO qr_codes (id,name,url,max_users,max_reports,used_users,used_reports,status,expires) VALUES (?,?,?,?,?,?,?,?,?)",
                            (qid, data.get('name',''), data.get('url',''), data.get('maxUsers',10), data.get('maxReports',20), data.get('usedUsers',0), data.get('usedReports',0), data.get('status','active'), data.get('expires','')))
                conn.commit()
                conn.close()
            self._json(200, {"success": True})
        except Exception as e:
            self._json(500, {"error": str(e)})

    # ===== Activation Codes API =====
    def _db_get_actcodes(self):
        try:
            with _DB_LOCK:
                conn = sqlite3.connect(_DB_PATH)
                rows = conn.execute("SELECT code,bonus_type,extra_reports,used,used_at,created_at FROM activation_codes ORDER BY created_at DESC").fetchall()
                conn.close()
            result = [{"code":r[0],"bonusType":r[1],"extraReports":r[2],"used":bool(r[3]),"usedAt":r[4],"createdAt":r[5]} for r in rows]
            self._json(200, {"codes": result})
        except Exception as e:
            self._json(500, {"error": str(e)})

    def _db_save_actcode(self, body):
        try:
            data = json.loads(body)
            action = data.get('action', 'upsert')
            with _DB_LOCK:
                conn = sqlite3.connect(_DB_PATH)
                if action == 'delete':
                    conn.execute("DELETE FROM activation_codes WHERE code=?", (data.get('code',''),))
                else:
                    acode = data.get('code','')
                    cur = conn.execute("UPDATE activation_codes SET bonus_type=?,extra_reports=?,used=?,used_at=? WHERE code=?",
                        (data.get('bonusType',''), data.get('extraReports',10), 1 if data.get('used') else 0, data.get('usedAt',''), acode))
                    if cur.rowcount == 0:
                        conn.execute("INSERT INTO activation_codes (code,bonus_type,extra_reports,used,used_at) VALUES (?,?,?,?,?)",
                            (acode, data.get('bonusType',''), data.get('extraReports',10), 1 if data.get('used') else 0, data.get('usedAt','')))
                conn.commit()
                conn.close()
            self._json(200, {"success": True})
        except Exception as e:
            self._json(500, {"error": str(e)})

    # ===== Records API =====
    def _db_get_records(self):
        try:
            with _DB_LOCK:
                conn = sqlite3.connect(_DB_PATH)
                rows = conn.execute("SELECT id,time,code,questions,reports,cost,created_at FROM records ORDER BY id DESC LIMIT 200").fetchall()
                conn.close()
            result = [{"time":r[1],"code":r[2],"questions":r[3],"reports":r[4],"cost":r[5]} for r in rows]
            self._json(200, {"records": result})
        except Exception as e:
            self._json(500, {"error": str(e)})

    def _db_save_record(self, body):
        try:
            data = json.loads(body)
            action = data.get('action', 'add')
            with _DB_LOCK:
                conn = sqlite3.connect(_DB_PATH)
                if action == 'clear':
                    conn.execute("DELETE FROM records")
                else:
                    conn.execute("INSERT INTO records (time,code,questions,reports,cost) VALUES (?,?,?,?,?)",
                        (data.get('time',''), data.get('code',''), data.get('questions',0), data.get('reports',0), data.get('cost',0)))
                conn.commit()
                conn.close()
            self._json(200, {"success": True})
        except Exception as e:
            self._json(500, {"error": str(e)})

    def _baidu_ocr_token(self):
        global _BAIDU_OCR_TOKEN
        if _BAIDU_OCR_TOKEN:
            return _BAIDU_OCR_TOKEN
        payload = urlencode({
            'grant_type': 'client_credentials',
            'client_id': BAIDU_OCR_API_KEY,
            'client_secret': BAIDU_OCR_SECRET_KEY
        }).encode()
        ctx = ssl.create_default_context()
        conn = HTTPSConnection('aip.baidubce.com', 443, timeout=30, context=ctx)
        try:
            conn.request(
                'POST',
                '/oauth/2.0/token',
                body=payload,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            resp = conn.getresponse()
            raw = resp.read().decode()
        finally:
            conn.close()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            raise Exception('百度OCR鉴权返回非JSON')
        if resp.status != 200 or not data.get('access_token'):
            raise Exception(data.get('error_description') or data.get('error') or '百度OCR鉴权失败')
        _BAIDU_OCR_TOKEN = data['access_token']
        return _BAIDU_OCR_TOKEN

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
        """云端OCR已停用"""
        self._json(503, {"error": "云端OCR已停用，请手动输入或粘贴文本", "stage": "disabled"})
        return
    def _proxy_ocr_legacy(self, body):
        self._json(503, {"error": "旧云端OCR代理已停用，请使用 /api/baidu-ocr", "stage": "disabled"})

    def _proxy_baidu_ocr(self, body):
        """百度云 OCR：只返回文字草稿，前端必须让用户校对后再生成报告。"""
        if not BAIDU_OCR_API_KEY or not BAIDU_OCR_SECRET_KEY:
            self._json(503, {"error": "服务未配置 BAIDU_OCR_API_KEY / BAIDU_OCR_SECRET_KEY", "stage": "config"})
            return
        try:
            data = json.loads(body)
            image = data.get('image', '')
            if not image:
                self._json(400, {"error": "缺少图片", "stage": "validate"})
                return
            image_b64 = image.split(',', 1)[-1]
            image_b64 = _normalize_image_for_baidu_ocr(image_b64)
            token = self._baidu_ocr_token()
            payload = urlencode({
                'image': image_b64,
                'detect_direction': 'true',
                'paragraph': 'true',
                'probability': 'true'
            }).encode()
            ctx = ssl.create_default_context()
            conn = HTTPSConnection('aip.baidubce.com', 443, timeout=60, context=ctx)
            try:
                conn.request(
                    'POST',
                    '/rest/2.0/ocr/v1/accurate?access_token=' + token,
                    body=payload,
                    headers={'Content-Type': 'application/x-www-form-urlencoded'}
                )
                resp = conn.getresponse()
                raw = resp.read().decode()
            finally:
                conn.close()
            result = json.loads(raw)
            if resp.status != 200 or result.get('error_code'):
                # Token may expire or be revoked; retry once with a fresh token.
                global _BAIDU_OCR_TOKEN
                if result.get('error_code') in (110, 111):
                    _BAIDU_OCR_TOKEN = ''
                self._json(502, {
                    "error": result.get('error_msg') or ('百度OCR HTTP ' + str(resp.status)),
                    "stage": "baidu_ocr",
                    "raw": {"error_code": result.get('error_code')}
                })
                return
            # 按位置排序：从上到下，同行从左到右
            words_result = result.get('words_result', [])
            sorted_words = sorted(words_result, key=lambda w: (
                round(w.get('location', {}).get('top', 0) / 10) * 10,  # Y→10px容差同行
                w.get('location', {}).get('left', 0)  # X→左到右
            ))

            # 文字锁定：中文标签 + 正下方值块（X轴对齐，Y轴近距）
            words = [(w.get('words', '').strip(), w.get('location', {})) for w in sorted_words]
            words = [(t, l) for t, l in words if t]
            merged = []
            used = set()
            for i, (cur, loc) in enumerate(words):
                if i in used:
                    continue
                used.add(i)
                cx, cy = loc.get('left', 0), loc.get('top', 0)
                cw = loc.get('width', 0)
                cur_has_cjk = bool(re.search(r'[一-鿿]', cur))

                is_personality = (cur == '性格类型')
                allow_cjk_val = is_personality

                # 统一在下方搜，dy 5~80px，X对齐±60px
                best_j, best_dy = None, 999
                for j, (nxt, loc2) in enumerate(words):
                    if j in used:
                        continue
                    ny = loc2.get('top', 0)
                    nx = loc2.get('left', 0)
                    nxt_is_value = bool(re.match(
                        r'^[一-鿿A-Za-z\d\s]{2,7}$' if allow_cjk_val else
                        r'^[\d\s.WwLlRrXxNnSsCcPpTtDdIiEeFfAaKkUuHh+-]+$', nxt))
                    if not nxt_is_value:
                        continue

                    # 只搜下方：dy 5~80px，X对齐±60px
                    if ny <= cy + 5:
                        continue
                    dy = ny - cy
                    if dy > 120:
                        continue
                    if abs(nx - cx) > 100:
                        continue
                    if dy < best_dy:
                        best_dy = dy
                        best_j = j
                if best_j is not None:
                    nxt_word, _ = words[best_j]
                    merged.append(cur + '  ' + nxt_word)
                    used.add(best_j)
                else:
                    merged.append(cur)
            text = '\n'.join(merged).strip()
            # 区域驱动提取
            region_values = _extract_region_values(sorted_words, image_b64)
            # Debug: 列出每个识别字符及其坐标
            debug_words = []
            for w in sorted_words:
                loc = w.get('location', {})
                debug_words.append({
                    'word': w.get('words', ''),
                    'x': loc.get('left', 0),
                    'y': loc.get('top', 0),
                    'w': loc.get('width', 0),
                    'h': loc.get('height', 0),
                })

            self._json(200, {
                "text": text,
                "lines": merged,
                "words_result_num": result.get('words_result_num', len(merged)),
                "direction": result.get('direction'),
                "region_values": region_values,
                "region_count": len(region_values),
                "debug_words": debug_words,
                "stage": "baidu_ocr"
            })
        except Exception as e:
            self._json(500, {"error": str(e), "stage": "baidu_ocr"})

    # ===== Extract Metrics（OCR 文本 → 结构化指标）=====
    def _proxy_extract_metrics(self, body):
        """从 OCR 文本中提取结构化指标，返回可编辑的 JSON。纯代码，零 LLM。"""
        try:
            data = json.loads(body)
            ocr_text = data.get('ocrText', '')
            if not ocr_text or not ocr_text.strip():
                self._json(400, {"metrics": {}, "success": False, "error": "缺少OCR文本"})
                return
            from engine.extractor import extract_metrics
            metrics = extract_metrics(ocr_text)
            self._json(200, {"metrics": metrics, "success": True, "stage": "extract_metrics"})
        except Exception as e:
            self._json(500, {"metrics": {}, "success": False, "error": str(e), "stage": "extract_metrics"})

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

            result = _deepseek_chat(
                [{"role":"user","content": prompts.get(report_type, prompts['portrait'])}],
                max_tokens=3000,
                temperature=0.7
            )
            content = result["choices"][0]["message"]["content"]
            usage = result.get("usage", {})
            self._json(200, {"content": content, "usage": usage, "cost": round(_deepseek_cost(usage), 6)})
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
            structured_metrics = data.get('structuredMetrics', None)  # 前端编辑后的指标

            # 检查 API Key
            if not DEEPSEEK_KEY or not DEEPSEEK_KEY.startswith('sk-'):
                self._json(503, {"error": "DeepSeek API Key 未配置。请设置环境变量 DEEPSEEK_KEY。", "stage": "config"})
                return

            # 拼接基础报告
            full_text = ocr_text
            if base_report:
                full_text = ocr_text + '\n\n[基础报告]\n' + base_report

            # 运行认知引擎
            engine = CognitiveEngine()
            engine_result = engine.run(full_text, report_type, style, age=age, target=target,
                                       pre_extracted_metrics=structured_metrics)

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

    def _start_talent_job(self, body):
        try:
            job_id = uuid.uuid4().hex
            with _TALENT_JOB_LOCK:
                _TALENT_JOBS[job_id] = {
                    'status': 'running',
                    'created_at': time.time(),
                    'updated_at': time.time(),
                    'finished_at': None,
                    'result': None,
                    'error': None,
                }

            def worker():
                try:
                    result = self._run_talent_v2_job(body)
                    with _TALENT_JOB_LOCK:
                        job = _TALENT_JOBS.get(job_id)
                        if job:
                            job['status'] = 'done'
                            job['result'] = result
                            job['updated_at'] = time.time()
                            job['finished_at'] = time.time()
                except Exception as e:
                    with _TALENT_JOB_LOCK:
                        job = _TALENT_JOBS.get(job_id)
                        if job:
                            job['status'] = 'error'
                            job['error'] = str(e)
                            job['updated_at'] = time.time()
                            job['finished_at'] = time.time()

            threading.Thread(target=worker, daemon=True).start()
            self._json(202, {'jobId': job_id, 'status': 'running'})
        except Exception as e:
            self._json(500, {'error': str(e)})

    def _get_talent_job(self):
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(self.path)
        job_id = (parse_qs(parsed.query).get('id') or [''])[0]
        if not job_id:
            self._json(400, {'error': 'missing job id'})
            return
        with _TALENT_JOB_LOCK:
            # TTL 清理：完成/错误的任务 5 分钟后删除，运行中的 30 分钟后清理
            now = time.time()
            stale = []
            for jid, j in _TALENT_JOBS.items():
                if j.get('finished_at') and now - j['finished_at'] > 300:
                    stale.append(jid)
                elif j['status'] == 'running' and now - j['created_at'] > 1800:
                    stale.append(jid)
            for jid in stale:
                _TALENT_JOBS.pop(jid, None)
            job = _TALENT_JOBS.get(job_id)
            if not job:
                self._json(404, {'error': 'job not found'})
                return
            payload = {'jobId': job_id, 'status': job['status']}
            if job['status'] == 'done':
                payload['result'] = job['result']
            elif job['status'] == 'error':
                payload['error'] = job['error']
            payload['age'] = round(now - job['created_at'], 1)
            if job['status'] in ('done', 'error'):
                _TALENT_JOBS.pop(job_id, None)
        self._json(200, payload)

    def _run_talent_v2_job(self, body):
        data = json.loads(body)
        ocr_text = data.get('ocrText', '')
        report_type = data.get('type', 'portrait')
        base_report = data.get('baseReport', '')
        style = data.get('style', 'gentle')
        age = data.get('age')
        target = data.get('target', 'self')
        structured_metrics = data.get('structuredMetrics', None)

        if not DEEPSEEK_KEY or not DEEPSEEK_KEY.startswith('sk-'):
            raise Exception('DeepSeek API Key 未配置。请设置环境变量 DEEPSEEK_KEY。')

        full_text = ocr_text
        if base_report:
            full_text = ocr_text + '\n\n[基础报告]\n' + base_report

        engine = CognitiveEngine()
        engine_result = engine.run(full_text, report_type, style, age=age, target=target,
                                   pre_extracted_metrics=structured_metrics)

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

        from engine.validator import validate
        validation = validate(content, engine_result['debug']['structure'], report_type)

        return {
            "content": content,
            "usage": usage,
            "debug": engine_result['debug'],
            "validation": validation,
            "version": "3.1",
            "style": style,
        }

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

    # ===== Export Helpers =====
    def _parse_post_body(self, body):
        """Safely parse POST body: JSON or form-encoded, with encoding fallback."""
        if not body:
            return {}
        if body[0:1] == b'{':
            try:
                return json.loads(body)
            except (json.JSONDecodeError, UnicodeDecodeError):
                return {}
        from urllib.parse import parse_qs
        try:
            text = body.decode('utf-8')
        except UnicodeDecodeError:
            text = body.decode('latin-1')
        params = parse_qs(text)
        return {k: v[0] if isinstance(v, list) else v for k, v in params.items()}

    def _export_pdf(self, body):
        """服务端 PDF 导出（移动端 Safari 兼容，支持 JSON + form POST）"""
        try:
            data = self._parse_post_body(body)
            title = data.get('title', 'SEE报告')
            markdown = data.get('markdown', '')
            if not markdown:
                self._json(400, {"error": "缺少报告内容"})
                return
            # 确保 markdown 是纯 str，避免 bytes/encoding 问题
            if isinstance(markdown, bytes):
                markdown = markdown.decode('utf-8', errors='ignore')

            pdf_bytes = _generate_pdf(title, markdown)
            self.send_response(200)
            self.send_header('Content-Type', 'application/pdf')
            self.send_header('Content-Disposition', _pdf_content_disposition(title))
            self.send_header('Content-Length', str(len(pdf_bytes)))
            self.end_headers()
            self.wfile.write(pdf_bytes)
        except Exception as e:
            self._json(500, {"error": str(e), "stage": "pdf"})

    def _export_doc(self, body):
        """服务端 Word 导出（HTML 作为 .doc 返回，兼容微信内置浏览器）"""
        try:
            data = self._parse_post_body(body)

            title = data.get('title', 'SEE报告')
            html = data.get('html', '')
            markdown = data.get('markdown', '')
            if not html and markdown:
                html = '<!DOCTYPE html><html><head><meta charset="utf-8"></head><body><pre style="white-space:pre-wrap;font-family:Arial,\"PingFang SC\",sans-serif">' + markdown + '</pre></body></html>'
            if not html:
                self._json(400, {"error": "缺少报告内容", "stage": "doc"})
                return

            content = html.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/msword; charset=utf-8')
            self.send_header('Content-Disposition', _pdf_content_disposition(title).replace('.pdf', '.doc'))
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self._json(500, {"error": str(e), "stage": "doc"})

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

                prompt = f"""你是一个 SEE 报告整合专家。你的任务不是重新写一份泛化报告，而是把「进一步讨论」里已经确认的补充信息、修正意见和个人背景，稳稳地并入原始报告。

## 你的身份
{persona_guide}

## 知识库参考
{kb_context}

## 原始报告
{report_text[:3000]}

## 全部讨论记录（用户补充的个人背景与修正意见）
{json.dumps(conversation, ensure_ascii=False)}

## 任务
生成一份融合了用户个性化补充的最终报告。只输出报告正文，不要前言后记、不要解释过程、不要额外点评。

要求：
1. 保留原始报告的核心结论和章节顺序，只更新用户明确修正过的部分
2. 只吸收讨论中已经确认的内容；不确定的信息要保守表达，不要补编
3. 将用户的年龄、对象、偏好、补充背景、修正意见融入对应章节，不要堆在一个段落里
4. 新增「个性化补充」章节时，写成归纳总结，不要复述对话
5. 如果原始报告是孩子/家长视角，就沿用该视角；如果是本人视角，就沿用本人视角
6. 语言风格与原始报告保持一致，句子短一些，段落清楚，避免收尾被拉成长尾句
7. {persona_guide}

报告结构（必须严格遵循）：
# {{报告标题}}
{structure}

⚠️ 如果内容较多，优先压缩重复说明和例子，保留结论完整收尾，不要在末尾留下半句话。"""
            else:
                history = '\n'.join([f"{'用户' if m['role']=='user' else '顾问'}: {m['content'][:300]}" for m in conversation[-8:]])
                prompt = f"""你是一个 SEE 报告顾问。当前这轮对话不是闲聊，而是「进一步讨论」：用户通常在这里补充背景、修正结论、确认表述，目标是把这些信息整合回最终报告。

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
1. 先判断用户这句话属于哪类：补充信息、修正错误、追问解释、还是请求整合
2. 如果是补充或修正，先简短确认你接收到了什么，再说明会把它并入最终报告的哪个部分
3. 如果是追问解释，直接用当前报告和知识库回答，不要绕远，也不要发散成长篇
4. 每次回复 80-220 字，尽量一两段，像顾问对话，不像模板答案
5. 不要堆砌术语。除非上方纹型数据或当前报告明确列出，否则不要提具体纹型编码；优先用行为语言解释，不用编码堆砌
6. 对「报什么班」类问题：给出能力方向建议而非具体机构，使用「可优先考虑/可以尝试」而非「一定/必须」
7. 如果用户说「可以整合」「出报告」「生成」，直接回复「好的，正在整合...」，不要继续展开
8. 不要在回复末尾添加「💡 如果满意...」等固定广告语。前端已有按钮
9. 结尾必须是完整句子，不要留下半截句、未完成列表或无意义尾巴"""

            result = proxy_request(
                "https://api.deepseek.com/v1/chat/completions",
                json.dumps({
                    "model": "deepseek-v4-pro",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 4000 if action == 'summarize' else 800,
                    "temperature": 0.5
                }).encode(),
                {"Content-Type": "application/json", "Authorization": f"Bearer {DEEPSEEK_KEY}"}
            )
            reply = result["choices"][0]["message"]["content"]
            # Post-process: trim trailing fragments
            reply = _trim_incomplete(reply)
            usage = result.get("usage", {})
            self._json(200, {"reply": reply, "action": action, "usage": usage})
        except Exception as e:
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

            result = _deepseek_chat(
                [{"role":"user","content": prompt}],
                max_tokens=3000,
                temperature=0.7
            )
            content = result["choices"][0]["message"]["content"]
            usage = result.get("usage", {})
            self._json(200, {"content": content, "usage": usage, "cost": round(_deepseek_cost(usage), 6)})
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

            result = _deepseek_chat(
                [{"role":"user","content": prompt}],
                max_tokens=3000,
                temperature=0.7
            )
            content = result["choices"][0]["message"]["content"]
            usage = result.get("usage", {})
            self._json(200, {"content": content, "usage": usage, "cost": round(_deepseek_cost(usage), 6)})
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

            result = _deepseek_chat(
                [{"role":"user","content": prompt}],
                max_tokens=3000,
                temperature=0.7
            )
            content = result["choices"][0]["message"]["content"]
            usage = result.get("usage", {})
            self._json(200, {"content": content, "usage": usage, "cost": round(_deepseek_cost(usage), 6)})
        except Exception as e:
            self._json(500, {"error": str(e)})

    @staticmethod
    def _extract_json(text):
        match = re.search(r'\{[\s\S]*\}', text)
        if not match: raise ValueError(f"无法解析JSON: {text[:100]}")
        return json.loads(match.group())


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    """多线程 HTTP 服务器，支持并发请求"""
    daemon_threads = True

if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    _init_db()
    # 启用 WAL 模式提升并发性能
    try:
        conn = sqlite3.connect(_DB_PATH)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.close()
    except Exception:
        pass
    # Load shell-persisted API keys when the process is started directly.
    # This keeps local desktop/mobile testing aligned with ~/.zshrc and ~/.claude/settings.json.
    #
    # 注意：模块级全局变量（DEEPSEEK_KEY / BAIDU_OCR_API_KEY / BAIDU_OCR_SECRET_KEY）
    # 在 import 时已从 os.environ 取过一次值。systemd 启动没有环境变量，所以此处
    # 从 ~/.zshrc 回读后必须重新赋值，否则全局变量仍然是空字符串。
    try:
        zshrc = os.path.expanduser('~/.zshrc')
        if os.path.exists(zshrc):
            with open(zshrc, 'r', encoding='utf-8', errors='ignore') as fh:
                for line in fh:
                    line = line.strip()
                    if line.startswith('export DEEPSEEK_KEY=') and not DEEPSEEK_KEY:
                        val = line.split('=', 1)[1].strip().strip('"').strip("'")
                        os.environ['DEEPSEEK_KEY'] = val
                        DEEPSEEK_KEY = val
                    elif line.startswith('export BAIDU_OCR_API_KEY=') and not BAIDU_OCR_API_KEY:
                        val = line.split('=', 1)[1].strip().strip('"').strip("'")
                        os.environ['BAIDU_OCR_API_KEY'] = val
                        BAIDU_OCR_API_KEY = val
                    elif line.startswith('export BAIDU_OCR_SECRET_KEY=') and not BAIDU_OCR_SECRET_KEY:
                        val = line.split('=', 1)[1].strip().strip('"').strip("'")
                        os.environ['BAIDU_OCR_SECRET_KEY'] = val
                        BAIDU_OCR_SECRET_KEY = val
    except Exception:
        pass
    ThreadingHTTPServer.allow_reuse_address = True
    port = int(os.environ.get('PORT', 8088))
    import socket
    lan_ip = ''
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        lan_ip = s.getsockname()[0]
        s.close()
    except: pass
    server = ThreadingHTTPServer(('0.0.0.0', port), SEEHandler)
    print('🔒 SEE 服务端启动 (多线程): http://127.0.0.1:8088')
    if lan_ip: print(f'   📱 手机访问: http://{lan_ip}:8088')
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
