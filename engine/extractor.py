"""Layer 0: OCR 文本 → 结构化指标  (纯代码, 零 LLM)

从 SEE 报告 OCR 文本中提取: TRC, ATD, 学习通道, 行为模式, 脑平衡, 纹型, 功能区分数
"""

import re


def extract_metrics(ocr_text):
    """从 OCR 文本中解析关键指标。返回 dict，缺失字段为 None。"""
    m = {}

    # ---- TRC ----
    trc_m = re.search(r'TRC[：:\s]*(\d{2,4})', ocr_text, re.IGNORECASE)
    if trc_m:
        m['trc'] = int(trc_m.group(1))
    else:
        for line in ocr_text.split('\n'):
            if '%' in line or re.search(r'\b(Lu|Ws|Wc|Wsc|Wl|We|Wi|Wpe|Wd|Xn|R)\b', line):
                continue
            nums = re.findall(r'\b(\d{2,4})\b', line)
            if len(nums) >= 2 and int(nums[0]) >= 80:
                m['trc'] = int(nums[0])
                m['atd'] = int(nums[1])
                break

    # ---- ATD ----
    if m.get('atd') is None:
        atd_m = re.search(r'ATD[：:\s]*(\d{1,3})', ocr_text, re.IGNORECASE)
        if not atd_m:
            atd_m = re.search(r'反应[灵敏度速度].*?(\d{1,3})', ocr_text)
        if atd_m:
            m['atd'] = int(atd_m.group(1))

    # ---- 行为模式 (兼容 "动机型" 和 "动机 型") ----
    for kw in ['动机型', '构思型', '均衡型']:
        if kw in ocr_text:
            m['behavior_mode'] = kw
            break

    # ---- 脑平衡 ----
    for kw in ['均衡型', '左脑型', '右脑型']:
        if kw in ocr_text:
            m['brain_balance'] = kw
            break

    # ---- 纹型 / 人格类型 ----
    pm = re.search(r'(?:纹型|人格类型|personality)[：:\s]*(\w+)', ocr_text)
    if pm:
        m['personality_type'] = pm.group(1)

    # ---- 学习通道 (优先百分比行) ----
    ch = {}
    pct_line = re.search(r'(\d+\.?\d*)%\s+(\d+\.?\d*)%\s+(\d+\.?\d*)%', ocr_text)
    if pct_line:
        vals = [float(pct_line.group(i)) for i in (1, 2, 3)]
        ch = {'auditory': vals[0], 'visual': vals[1], 'kinesthetic': vals[2]}
    else:
        for label, key in [('听觉', 'auditory'), ('视觉', 'visual'), ('体觉', 'kinesthetic')]:
            pct = re.search(rf'{label}(?!左|右)[^0-9]*?(\d+\.?\d+)\s*%', ocr_text)
            if pct:
                ch[key] = float(pct.group(1))
    if ch:
        m['learning_channels'] = ch
        m['primary_channel'] = max(ch, key=ch.get)

    # ---- 功能区 10 项 ----
    area_map = [
        ('精神左', 'spirit_left'), ('精神右', 'spirit_right'),
        ('思维左', 'thinking_left'), ('思维右', 'thinking_right'),
        ('体觉左', 'kinesthetic_left'), ('体觉右', 'kinesthetic_right'),
        ('听觉左', 'auditory_left'), ('听觉右', 'auditory_right'),
        ('视觉左', 'visual_left'), ('视觉右', 'visual_right'),
    ]
    func = {}
    patterns = {}
    for cn, en in area_map:
        s = re.search(rf'{cn}[^0-9]*?(\d+)', ocr_text)
        if s:
            func[en] = int(s.group(1))

    if func:
        m['function_scores'] = func
        sorted_areas = sorted(func, key=func.get, reverse=True)
        m['top_three_areas'] = sorted_areas[:3]
        m['lowest_area'] = sorted_areas[-1]

    # ---- 功能区得分 + 纹型编码 (从数字+纹型对提取) ----
    PATTERN_CODES = r'(Lu|Ws|Wc|Wsc|Wl|We|Wi|Wpe|Wd|Xn|R|Lf|X|Wt)'
    raw_pairs = re.findall(rf'\b(\d+)\s+{PATTERN_CODES}\b', ocr_text)
    area_order = [en for _, en in area_map]

    if raw_pairs:
        if len(raw_pairs) >= 10:
            # 完整 10 对 → 按 SEE 标准顺序分配
            raw_pairs = raw_pairs[:10]
            for i, (score_str, code) in enumerate(raw_pairs):
                en = area_order[i]
                score = int(score_str)
                if en not in func:
                    func[en] = score
                patterns[en] = code
        elif func:
            # 部分匹配 → 按 func 值对应
            used = set()
            for en in area_order:
                if en not in func:
                    continue
                expected = func[en]
                for i, (score_str, code) in enumerate(raw_pairs):
                    if i in used:
                        continue
                    if int(score_str) == expected:
                        patterns[en] = code
                        used.add(i)
                        break
        else:
            # 无 func，按出现顺序直接分配（可能不完整但至少保留数据）
            for i, (score_str, code) in enumerate(raw_pairs):
                if i < len(area_order):
                    en = area_order[i]
                    score = int(score_str)
                    if en not in func:
                        func[en] = score
                    patterns[en] = code

    if func:
        # 都用纹型对来修正 func
        m['function_scores'] = func
        m['function_patterns'] = patterns
        sorted_areas = sorted(func, key=func.get, reverse=True)
        m['top_three_areas'] = sorted_areas[:3]
        m['lowest_area'] = sorted_areas[-1]

    # ---- 左右脑差值 ----
    if func:
        left_keys = [k for k in func if 'left' in k]
        right_keys = [k for k in func if 'right' in k]
        if left_keys and right_keys:
            left_avg = sum(func[k] for k in left_keys) / len(left_keys)
            right_avg = sum(func[k] for k in right_keys) / len(right_keys)
            m['left_right_diff'] = left_avg - right_avg

    return m
