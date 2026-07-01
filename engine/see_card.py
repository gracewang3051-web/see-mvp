"""SEE 卡 25 题思维画像 — 轻量解释层 (纯代码, 零 LLM)

输入: index.html::buildPortrait() 的 portrait dict
输出: {observed_data, rule_hits, evidence, missing, summary}
"""

# 5 模块 × 4 选项 → 行为描述 (与 index.html MODULES 对齐)
MODULE_RULES = {
    'strategic': {
        'A': {'style': '目标驱动型', 'traits': ['执行力强', '按计划推进'], 'risk': '缺乏灵活性', 'growth': '在计划中留探索空间'},
        'B': {'style': '愿景驱动型', 'traits': ['使命感强', '有宏大愿景'], 'risk': '目标不具体', 'growth': '将愿景拆解为可执行步骤'},
        'C': {'style': '双驱平衡型', 'traits': ['方向与动力兼备', '目标与愿景兼具'], 'risk': '双重压力', 'growth': '灵活切换模式'},
        'D': {'style': '探索过渡型', 'traits': ['心态开放', '灵活适应'], 'risk': '缺乏持续动力', 'growth': '建立小目标+外部监督'},
    },
    'thinking': {
        'A': {'style': '分析型', 'traits': ['逻辑严谨', '注重细节推理'], 'risk': '忽略大局', 'growth': '从细节跳出来看全局'},
        'B': {'style': '统合型', 'traits': ['全局视野', '宏观把握'], 'risk': '忽略关键细节', 'growth': '培养细节意识'},
        'C': {'style': '全维型', 'traits': ['深度广度兼备', '分析与统合俱佳'], 'risk': '思维负载大', 'growth': '合理分配精力'},
        'D': {'style': '梳理型', 'traits': ['借助外力理清', '逐步建立框架'], 'risk': '独立迷失', 'growth': '建立思维框架'},
    },
    'listening': {
        'A': {'style': '内容型', 'traits': ['抓取关键信息', '关注事实内容'], 'risk': '忽略情绪需求', 'growth': '加入情感确认'},
        'B': {'style': '情感型', 'traits': ['共情能力强', '听情绪听语气'], 'risk': '忽略事实层面', 'growth': '关注事实信息'},
        'C': {'style': '全息型', 'traits': ['内容情感兼顾', '全面倾听'], 'risk': '精力消耗大', 'growth': '调整倾听深度'},
        'D': {'style': '要点型', 'traits': ['快节奏沟通', '抓取要点'], 'risk': '复杂信息遗漏', 'growth': '重要对话做笔记'},
    },
    'visual': {
        'A': {'style': '细节型', 'traits': ['观察力强', '对视觉细节敏感'], 'risk': '因小失大', 'growth': '培养整体连接能力'},
        'B': {'style': '审美型', 'traits': ['品位出众', '注重美感整体'], 'risk': '忽略功能性', 'growth': '关注实用性'},
        'C': {'style': '全观型', 'traits': ['细节整体平衡', '审美与功能兼顾'], 'risk': '标准过高', 'growth': '降低完美要求'},
        'D': {'style': '大局型', 'traits': ['不被细节困扰', '关注全局'], 'risk': '错过重要信息', 'growth': '培养视觉敏感度'},
    },
    'kinesthetic': {
        'A': {'style': '执行型', 'traits': ['行动力强', '效率高'], 'risk': '缺乏直觉信任', 'growth': '留出直觉空间'},
        'B': {'style': '直觉型', 'traits': ['反应迅速', '身体先行'], 'risk': '缺乏规划', 'growth': '重要决定理性检查'},
        'C': {'style': '掌控型', 'traits': ['力量精准兼备', '把握节奏'], 'risk': '完美主义', 'growth': '80%准备就行动'},
        'D': {'style': '启动型', 'traits': ['启动后能坚持', '循序渐进'], 'risk': '启动困难', 'growth': '建立启动仪式'},
    },
}

# 跨模块组合规则 (简化版，基于 SEE 卡手册)
COMBO_RULES = [
    {
        'label': '目标-分析联动型',
        'condition': lambda d: d.get('strategic') == 'A' and d.get('thinking') == 'A',
        'desc': '目标明确 + 逻辑分析强 → 适合需要精密规划的执行角色',
    },
    {
        'label': '愿景-统合联动型',
        'condition': lambda d: d.get('strategic') == 'B' and d.get('thinking') == 'B',
        'desc': '有宏大愿景 + 整体把握 → 适合战略规划与方向引领',
    },
    {
        'label': '情感-直觉联动型',
        'condition': lambda d: d.get('listening') == 'B' and d.get('kinesthetic') == 'B',
        'desc': '共情倾听 + 直觉行动 → 适合需要快速感知与响应的场景',
    },
    {
        'label': '全维平衡型',
        'condition': lambda d: sum(1 for v in d.values() if v == 'C') >= 3,
        'desc': '多模块均衡 → 全面但需防止精力分散',
    },
    {
        'label': '大脑通道-听觉优势',
        'condition': lambda bc: '听觉' in str(bc) if bc else False,
        'desc': '听觉为信息接收主通道 → 听讲、讨论、音频学习最有效',
    },
    {
        'label': '大脑通道-视觉优势',
        'condition': lambda bc: '视觉' in str(bc) if bc else False,
        'desc': '视觉为信息接收主通道 → 图表、阅读、演示最有效',
    },
    {
        'label': '大脑通道-体觉优势',
        'condition': lambda bc: '体觉' in str(bc) if bc else False,
        'desc': '体觉为信息接收主通道 → 动手实践、体验式学习最有效',
    },
]


def interpret_see_card(portrait):
    """将 SEE 卡 25 题 portrait 转为结构化解释对象。

    Args:
        portrait: index.html::buildPortrait() 的输出

    Returns:
        dict: {observed_data, rule_hits, evidence, missing, summary}
    """
    modules = portrait.get('modules', [])
    dominant = portrait.get('dominant', {})
    handwritten = portrait.get('handwritten', {})
    brain_channel = portrait.get('brain_channel') or handwritten.get('brain_channel', '')
    brain_mode = portrait.get('brain_mode') or handwritten.get('brain_mode', '')
    brain_receiver = portrait.get('brain_receiver') or handwritten.get('brain_receiver', '')

    # --- observed_data: 原始输入 ---
    observed_data = {
        'module_choices': {},
        'handwritten': {
            'self_label': handwritten.get('self_label', ''),
            'strategy_result': handwritten.get('strategy_result', ''),
            'receiver_result': handwritten.get('receiver_result', ''),
            'output_result': handwritten.get('output_result', ''),
        },
        'brain_fields': {
            'brain_channel': brain_channel,
            'brain_mode': brain_mode,
            'brain_receiver': brain_receiver,
        },
    }
    for m in modules:
        observed_data['module_choices'][m['dimension']] = {
            'name': m['name'],
            'dominant': m['dominant'],
            'style': m['style'],
            'strength': m.get('strength', ''),
            'risk': m.get('risk', ''),
            'growth': m.get('growth', ''),
        }

    # --- rule_hits: 规则命中 ---
    rule_hits = []
    for m in modules:
        dim = m['dimension']
        dom = m['dominant']
        if dim in MODULE_RULES and dom in MODULE_RULES[dim]:
            rule_info = MODULE_RULES[dim][dom]
            rule_hits.append({
                'module': m['name'],
                'dimension': dim,
                'choice': dom,
                'style': rule_info['style'],
                'traits': rule_info['traits'],
                'risk': rule_info['risk'],
                'growth': rule_info['growth'],
            })

    # 跨模块组合
    for combo in COMBO_RULES:
        try:
            if combo['condition'](dominant) if 'dominant' not in str(combo['condition'].__code__.co_varnames[:1]) else True:
                pass
        except:
            pass

    # 重新实现组合检查
    combo_matches = []
    # 目标-分析联动型
    if dominant.get('strategic') == 'A' and dominant.get('thinking') == 'A':
        combo_matches.append(COMBO_RULES[0]['label'])
    # 愿景-统合联动型
    if dominant.get('strategic') == 'B' and dominant.get('thinking') == 'B':
        combo_matches.append(COMBO_RULES[1]['label'])
    # 情感-直觉联动型
    if dominant.get('listening') == 'B' and dominant.get('kinesthetic') == 'B':
        combo_matches.append(COMBO_RULES[2]['label'])
    # 全维平衡型
    c_count = sum(1 for v in dominant.values() if v == 'C')
    if c_count >= 3:
        combo_matches.append(COMBO_RULES[3]['label'])

    # 大脑通道组合
    for i in [4, 5, 6]:
        try:
            if COMBO_RULES[i]['condition'](brain_channel):
                combo_matches.append(COMBO_RULES[i]['label'])
        except:
            pass

    for cm in combo_matches:
        rule_hits.append({'type': 'combo', 'label': cm})

    # --- evidence: 数据来源追踪 ---
    evidence = {
        'source': 'SEE卡25题手动/OCR识别',
        'modules_found': [m['dimension'] for m in modules],
        'dominant_choices': {m['dimension']: m['dominant'] for m in modules},
        'brain_channel_source': f"手动输入: {brain_channel}" if brain_channel else None,
        'brain_mode_source': f"手动输入: {brain_mode}" if brain_mode else None,
        'brain_receiver_source': f"手动输入: {brain_receiver}" if brain_receiver else None,
        'handwritten_fields': [k for k, v in handwritten.items() if v and k not in ('brain_channel', 'brain_mode', 'brain_receiver')],
    }

    # --- missing: 缺失字段 ---
    missing = []
    if not brain_channel:
        missing.append('brain_channel')
    if not brain_mode:
        missing.append('brain_mode')
    if not brain_receiver:
        missing.append('brain_receiver')
    if not handwritten.get('self_label'):
        missing.append('self_label')
    if not handwritten.get('strategy_result'):
        missing.append('strategy_result')
    if not handwritten.get('receiver_result'):
        missing.append('receiver_result')
    if not handwritten.get('output_result'):
        missing.append('output_result')

    # --- summary: 行为层面摘要 ---
    parts = []
    for m in modules:
        parts.append(f"{m['name']}: {m['style']}（优势：{m.get('strength','')} | 成长方向：{m.get('growth','')}）")
    if brain_channel:
        parts.append(f"大脑通道: {brain_channel}")
    if brain_mode:
        parts.append(f"大脑模式: {brain_mode}")
    if brain_receiver:
        parts.append(f"大脑接收器: {brain_receiver}")
    if combo_matches:
        parts.append(f"组合特征: {'、'.join(combo_matches)}")

    summary = '\n'.join(parts)

    return {
        'observed_data': observed_data,
        'rule_hits': rule_hits,
        'evidence': evidence,
        'missing': missing,
        'summary': summary,
    }
