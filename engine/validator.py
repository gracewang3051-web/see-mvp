"""Layer 4: 输出校验 — 兜底检查 (代码)"""

import re
from engine.rules import PATTERN_MATRIX

BANNED_WORDS = ['智商', '不聪明', '注定', '绝对是', '笨蛋', '聪明绝顶',
                 '一定是', '肯定', '100%', '百分之百']
DANGER_PHRASES = ['缺陷', '太差', '弱点是', '你这孩子不行', '有问题', '不正常']


def validate(report_text, structure, report_type='portrait'):
    """校验报告输出。

    Args:
        report_text: LLM 生成的报告文本
        structure: rules.apply_rules() 的输出
        report_type: 报告类型 (portrait/learning/emotion/potential 等)

    Returns:
        dict: {passed: bool, warnings: [str]}
    """
    warnings = []

    # 1. 禁止词检查
    for word in BANNED_WORDS:
        if word in report_text:
            warnings.append(f'禁止词: 出现「{word}」')

    # 2. 通道一致性
    channel = structure.get('channel', {})
    if channel:
        primary = channel.get('primary', '')
        if primary and primary not in report_text:
            other_channels = [c for c in ['auditory', 'visual', 'kinesthetic'] if c != primary]
            for oc in other_channels:
                if f'{oc}主导' in report_text or f'{oc}型' in report_text:
                    warnings.append(f'通道不一致: 引擎判定 {primary}，报告提到 {oc}')

    # 3. 结构完整性 — 基础检查（非 portrait 类型）
    is_portrait = report_type in ('portrait', 'portrait-see-ai')
    if not is_portrait:
        required_sections = ['行为解码', '特质', '优势', '建议']
        for section in required_sections:
            if section not in report_text:
                warnings.append(f'结构不完整: 缺少「{section}」相关章节')

    # 3b. portrait 模板专项检查（仅 portrait 类型）
    if is_portrait:
        portrait_sections = ['思维画像AI解读', '核心特质', '成长建议', '数据说明']
        for section in portrait_sections:
            if section not in report_text:
                warnings.append(f'Portrait模板缺失: 缺少「{section}」章节')

    # 4. 低分区语言检查
    for phrase in DANGER_PHRASES:
        if phrase in report_text:
            warnings.append(f'表述不当: 低分区使用了「{phrase}」')

    # 5. 数据根基检查 — 非 portrait 类型检查是否引用了至少一个具体指标
    if not is_portrait and not _has_data_reference(report_text):
        warnings.append('数据根基: 报告未引用任何具体指标（TRC/ATD/通道/纹型/功能区）')

    # 6. 绝对化断言检查
    absolute_patterns = [r'一定(是|会|能|可以)', r'绝对(是|能|会)', r'注定', r'100%', r'百分之百']
    for pattern in absolute_patterns:
        matches = re.findall(pattern, report_text)
        if matches:
            warnings.append(f'绝对化断言: 出现「{pattern}」（{len(matches)}次）')

    # 7. 凭空编造检查 — 纹型编码
    _check_fabricated_patterns(report_text, structure, warnings)

    # 8. 凭空编造检查 — 对缺失字段的编造
    _check_fabricated_metrics(report_text, structure, warnings)

    # 9. 缺失数据降级检查（仅核心指标，可选指标不阻塞）
    evidence = structure.get('evidence', {})
    missing = evidence.get('metrics_missing', [])
    if missing:
        has_degradation = any(phrase in report_text for phrase in
            ['资料不足', '不足以判断', '暂时无法', '数据不完整', '建议补充'])
        if not has_degradation:
            warnings.append(f'数据降级: 核心指标缺失 {missing}，但报告中未标注「资料不足」')

    return {
        'passed': len(warnings) == 0,
        'warnings': warnings,
    }


def _has_data_reference(report_text):
    """检查报告是否引用了至少一个具体数据指标。"""
    patterns = [
        r'TRC[=＝]?\s*\d{2,4}',           # TRC=180
        r'ATD[=＝]?\s*\d{1,3}',           # ATD=35
        r'\d+\.?\d*\s*%',                  # 百分比
        r'(听觉|视觉|体觉)[^型]',           # 提到感知通道
        r'(Wc|Ws|Wsc|We|Wi|Wpe|Wd|Wl|Lu|Wt|Lf|R|Xn|X)',  # 纹型编码
        r'\d+\s*分',                        # 功能区得分
        r'动机型|构思型|均衡型',             # 行为模式
    ]
    return any(re.search(p, report_text) for p in patterns)


def _check_fabricated_patterns(report_text, structure, warnings):
    """检查报告中是否出现了未在提取数据中的纹型编码。"""
    # 从 structure 中获取实际提取的纹型
    evidence = structure.get('evidence', {})
    found_patterns = set()
    for pf in evidence.get('patterns_found', []):
        # format: "spirit_left: Wc"
        code = pf.split(': ')[-1].strip()
        found_patterns.add(code)

    # 从 pattern_insights 也收集
    for pi in structure.get('pattern_insights', []):
        found_patterns.add(pi.get('code', ''))

    # 搜索报告中出现的纹型编码
    all_pattern_codes = set(PATTERN_MATRIX.keys())
    report_codes = set()
    for code in all_pattern_codes:
        # 用词边界匹配避免误报
        if re.search(rf'\b{re.escape(code)}\b', report_text):
            report_codes.add(code)

    # 报告中出现但未在实际数据中的编码
    fabricated = report_codes - found_patterns
    if fabricated:
        warnings.append(f'凭空编造纹型: 报告提到 {fabricated}，但提取数据中未发现')


def _check_fabricated_metrics(report_text, structure, warnings):
    """检查对缺失指标的具体数值/描述编造，以及数值不匹配。"""
    trc = structure.get('trc')
    atd = structure.get('atd')
    channel = structure.get('channel')

    # --- TRC 检查 ---
    actual_trc = trc.get('value') if trc else None
    if actual_trc is None:
        if re.search(r'TRC[=＝]?\s*\d+', report_text):
            warnings.append('凭空编造: TRC 数据缺失，但报告包含了 TRC 数值')
    else:
        # 报告中的 TRC 值与实际不匹配
        report_trc_matches = re.findall(r'TRC[=＝]?\s*(\d+)', report_text)
        for m in report_trc_matches:
            report_val = int(m)
            if report_val != actual_trc:
                warnings.append(f'TRC数值不匹配: 引擎提取 TRC={actual_trc}，报告声称 TRC={report_val}')

    # --- ATD 检查 ---
    actual_atd = atd.get('value') if atd else None
    if actual_atd is None:
        if re.search(r'ATD[=＝]?\s*\d+', report_text):
            warnings.append('凭空编造: ATD 数据缺失，但报告包含了 ATD 数值')
    else:
        report_atd_matches = re.findall(r'ATD[=＝]?\s*(\d+)', report_text)
        for m in report_atd_matches:
            report_val = int(m)
            if report_val != actual_atd:
                warnings.append(f'ATD数值不匹配: 引擎提取 ATD={actual_atd}，报告声称 ATD={report_val}')

    # 如果通道为空，不应声称主导通道
    if not channel or not channel.get('primary'):
        channel_claims = re.findall(r'(听觉|视觉|体觉)(?![一-鿿]*?左|[一-鿿]*?右)(?:主导|型|通道)', report_text)
        if channel_claims:
            warnings.append(f'凭空编造: 学习通道数据缺失，但报告声称 {channel_claims}')


def _check_see_card_fabrication(report_text, structure, warnings):
    """SEE卡25题专项: 检查报告是否编造了不存在的 TRC/ATD/纹型数据。"""
    trc = structure.get('trc')
    atd = structure.get('atd')
    has_patterns = bool(structure.get('pattern_insights', []) or structure.get('evidence', {}).get('patterns_found', []))

    # SEE卡25题没有TRC/ATD/纹型，如果structure中这些字段为空，报告不应提及
    if trc is None:
        if re.search(r'TRC\s*[=＝]?\s*\d{2,4}', report_text):
            warnings.append('SEE卡编造: 报告中出现 TRC 数值，但25题思维画像不含此数据')
        if re.search(r'(高TRC|低TRC|TRC.*容量|学习容量)', report_text):
            warnings.append('SEE卡编造: 报告中提及 TRC/学习容量概念，但25题思维画像不含此数据')

    if atd is None:
        if re.search(r'ATD\s*[=＝]?\s*\d{1,3}', report_text):
            warnings.append('SEE卡编造: 报告中出现 ATD 数值，但25题思维画像不含此数据')
        if re.search(r'(反应灵敏度|ATD.*型|反应风格)', report_text):
            warnings.append('SEE卡编造: 报告中提及 ATD/反应风格概念，但25题思维画像不含此数据')

    if not has_patterns:
        pattern_mentions = re.findall(r'\b(Wc|Wsc|Ws|We|Wi|Wpe|Wd|Wl|Lu|Wt|Lf|R|Xn|X)\b', report_text)
        if pattern_mentions:
            warnings.append(f'SEE卡编造: 报告中出现纹型编码 {set(pattern_mentions)}，但25题思维画像不含纹型数据')
