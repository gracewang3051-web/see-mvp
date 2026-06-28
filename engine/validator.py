"""Layer 4: 输出校验 — 兜底检查 (代码)"""

BANNED_WORDS = ['智商', '不聪明', '注定', '绝对是', '笨蛋', '聪明绝顶']


def validate(report_text, structure):
    """校验报告输出。

    Args:
        report_text: LLM 生成的报告文本
        structure: rules.apply_rules() 的输出

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
            # 检查是否提到了非主通道作为主通道
            other_channels = [c for c in ['auditory', 'visual', 'kinesthetic'] if c != primary]
            for oc in other_channels:
                if f'{oc}主导' in report_text or f'{oc}型' in report_text:
                    warnings.append(f'通道不一致: 引擎判定 {primary}，报告提到 {oc}')

    # 3. 结构完整性
    required_sections = ['行为解码', '特质', '优势', '建议']
    for section in required_sections:
        if section not in report_text:
            warnings.append(f'结构不完整: 缺少「{section}」相关章节')

    # 4. 低分区语言检查
    danger_phrases = ['缺陷', '太差', '弱点是', '你这孩子不行']
    for phrase in danger_phrases:
        if phrase in report_text:
            warnings.append(f'表述不当: 低分区使用了「{phrase}」')

    return {
        'passed': len(warnings) == 0,
        'warnings': warnings,
    }
