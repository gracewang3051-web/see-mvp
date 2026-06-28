"""Layer 2: 解释层 — 将结构数据转为解释指令 (代码, 零 LLM 调用)

生成的解释指令嵌入主 prompt，由主 LLM 在一次调用中完成解释 + 报告生成。
"""

from engine.rules import rule_summary


def interpret(structure, raw_input=''):
    """生成解释指导文本，嵌入主 prompt。

    Returns:
        dict: {behavior_decode, raw_input, summary}
    """
    summary = rule_summary(structure)

    trc = structure.get('trc', {})
    atd = structure.get('atd', {})
    channel = structure.get('channel', {})
    behavior = structure.get('behavior', {})
    combos = structure.get('combos', [])
    combo_labels = [c['label'] for c in combos]

    # 解释指导（纯文本，由主 LLM 在生成报告时执行）
    instructions = []
    instructions.append("## 行为解释指导")
    instructions.append("在报告开头，请基于以下框架解释用户的行为模式：\n")

    # 整体模式
    mode_parts = []
    if trc:
        mode_parts.append(f"学习容量{trc['label']}（{trc.get('capacity','')}）")
    if atd:
        mode_parts.append(f"反应风格{atd['label']}（{atd.get('focus','')}）")
    if mode_parts:
        instructions.append(f"1. 整体模式：{', '.join(mode_parts)}")
        instructions.append("   → 解释：这个人如何接收和处理信息？\n")

    # 学习通道
    if channel:
        ch_label = channel.get('label', '')
        instructions.append(f"2. 最佳学习通路：{ch_label}")
        instructions.append("   → 解释：什么样的输入方式对他最有效？\n")

    # 行为模式
    if behavior:
        instructions.append(f"3. 行为驱动力：{behavior['type']}")
        instructions.append(f"   → 解释：{behavior.get('desc','')[:100]}\n")

    # 三优一阻
    if structure.get('top_three'):
        instructions.append(f"4. 优势区与成长区：")
        instructions.append(f"   优势区 = {', '.join(structure['top_three'])}")
        instructions.append(f"   成长提醒区 = {structure.get('bottom_one','')}")
        instructions.append("   → 解释：这些强弱之间的关系，优势区如何辅助成长区？\n")

    # 组合特征
    if combos:
        instructions.append(f"5. 组合特征：{', '.join(combo_labels)}")
        instructions.append("   → 解释：这些组合特征意味着怎样的行为倾向？\n")

    # 纹型
    for p in structure.get('pattern_insights', []):
        instructions.append(f"6. 纹型洞察 - {p['area']}({p['code']}): {p['insight']}")

    return {
        'behavior_decode': '\n'.join(instructions),
        'raw_input': raw_input,
        'summary': summary,
    }
