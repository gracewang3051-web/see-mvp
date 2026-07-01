"""SEE 卡 25 题思维画像 — 轻量解释层 (纯代码, 零 LLM)

规则来源: kb_portrait/SEE卡应用手册.md
输入: index.html::buildPortrait() 的 portrait dict
输出: {observed_data, rule_hits, evidence, missing, summary}
"""

import os


# ============================================================
# 知识库参考文本加载 (LLM prompt 上下文)
# ============================================================
_KB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'kb_portrait')
_KB_CACHE = None


def load_see_card_context():
    """加载 SEE卡应用手册的关键参考段落，供 LLM prompt 使用。

    只选取写作边界、咨询表达、场景指导，不加载全部手册。
    返回字符串，约 2500-4000 中文。
    """
    global _KB_CACHE
    if _KB_CACHE is not None:
        return _KB_CACHE

    kb_path = os.path.join(_KB_DIR, 'SEE卡应用手册.md')
    try:
        with open(kb_path, 'r') as f:
            text = f.read()
    except (FileNotFoundError, IOError):
        _KB_CACHE = ''
        return ''

    # 选取关键段落
    excerpts = []

    # 核心原则：镜子不贴标签
    for marker in ['SEE 卡不贴标签', '核心理念', '让思维看见，让理解发生',
                   'SEE 卡是 SEE 生命印迹体系中的第一个工具', '它是"镜子"']:
        idx = text.find(marker)
        if idx >= 0:
            excerpts.append(text[idx:idx+200].strip())

    # 接收通道 - 沟通翻译器 (感知/分析/结果)
    idx = text.find('沟通翻译器')
    if idx >= 0:
        excerpts.append(text[idx:idx+350].strip())

    # 战略偏好 - 深度/广度 + 团队搭配
    idx = text.find('③ 战略偏好')
    if idx >= 0:
        excerpts.append(text[idx:idx+300].strip())

    # 五大功能区核心原则
    idx = text.find('重要原则')
    if idx >= 0:
        excerpts.append(text[idx:idx+180].strip())

    # D 的两层智慧
    idx = text.find('D 的两层智慧')
    if idx >= 0:
        excerpts.append(text[idx:idx+250].strip() if text.find('D 的两层智慧') >= 0 else '')

    # 场景解读 - 沟通通道
    idx = text.find('② 沟通通道——你如何接收信息')
    if idx >= 0:
        excerpts.append(text[idx:idx+350].strip())

    # 成长路径
    idx = text.find('PART 1')
    if idx >= 0:
        excerpts.append(text[idx:idx+120].strip())

    _KB_CACHE = '\n\n---\n\n'.join(e for e in excerpts if e)
    # Cap at ~3500 chars
    if len(_KB_CACHE) > 4000:
        _KB_CACHE = _KB_CACHE[:4000] + '\n\n...（手册其余内容略）'
    return _KB_CACHE

# ============================================================
# A/B/C/D 标准定义 (来源: SEE卡应用手册 六、引导师速查表)
# ============================================================
ABCD_DEFINITIONS = {
    'A': {'meaning': '左脑优势', 'desc': '逻辑、细节、执行面强',
          'positive': '目标明确、逻辑清晰、执行力强', 'risk': '过度分析、钻牛角尖、太急太硬'},
    'B': {'meaning': '右脑优势', 'desc': '直觉、整体、创意面强',
          'positive': '有愿景、战略眼光、情感共鸣', 'risk': '忽略细节、不落地、光想不做'},
    'C': {'meaning': '左右脑双启动', 'desc': '左右脑协同，该功能区极强、不费力',
          'positive': '全面、高效、双强', 'risk': '精力分散、两头都想抓、容易过载'},
    'D': {'meaning': '需要支持', 'desc': '该功能区相对薄弱，或策略性选择不在此处用力',
          'positive': '借力、合作、聚焦天赋', 'risk': '容易卡顿、消耗大',
          'note': 'D有两层含义：先天短板（天生不主场）或策略选择（有能力但选择不做）'},
}

# ============================================================
# 5 模块规则 (来源: SEE卡应用手册 六、引导师速查表)
# ============================================================
MODULE_RULES = {
    'strategic': {
        'name': '精神功能',
        'role': '目标、执行、内驱力',
        'A': {'label': '左脑驱动', 'traits': ['目标明确', '执行力强'], 'risk': '太急太硬不顾感受', 'growth': '在计划中留弹性空间'},
        'B': {'label': '右脑驱动', 'traits': ['有愿景', '画蓝图'], 'risk': '光想不做眼高手低', 'growth': '将愿景拆解为可执行步骤'},
        'C': {'label': '双启动', 'traits': ['目标+愿景+执行全强'], 'risk': '什么都想抓容易累', 'growth': '学会优先级排序'},
        'D': {'label': '需支持', 'traits': ['易没目标', '易放弃'], 'risk': '缺乏持续动力', 'growth': '建立小目标+外部监督', 'd_note': '追问：天生短板 VS 策略选择'},
    },
    'thinking': {
        'name': '思维功能',
        'role': '逻辑、分析、战略',
        'A': {'label': '左脑驱动', 'traits': ['逻辑清晰', '擅长分析'], 'risk': '过度分析钻牛角尖', 'growth': '定时收束思维'},
        'B': {'label': '右脑驱动', 'traits': ['战略眼光', '看整体'], 'risk': '忽略细节逻辑不严', 'growth': '培养细节意识'},
        'C': {'label': '双启动', 'traits': ['深度分析+宏观战略'], 'risk': '想太多切换累', 'growth': '合理分配思考精力'},
        'D': {'label': '需支持', 'traits': ['想问题乱', '易被带偏'], 'risk': '独立思考困难', 'growth': '建立思维框架', 'd_note': '追问：天生短板 VS 策略选择'},
    },
    'listening': {
        'name': '听觉功能',
        'role': '语言理解、情感倾听',
        'A': {'label': '左脑驱动', 'traits': ['抓取关键信息', '认真听仔细想'], 'risk': '忽略情绪需求', 'growth': '加入情感确认'},
        'B': {'label': '右脑驱动', 'traits': ['共情倾听', '听情绪听心声'], 'risk': '忽略事实层面', 'growth': '关注事实信息'},
        'C': {'label': '双启动', 'traits': ['内容情感兼顾'], 'risk': '精力消耗大', 'growth': '调整倾听深度'},
        'D': {'label': '需支持', 'traits': ['复杂信息易漂移'], 'risk': '重要信息遗漏', 'growth': '重要对话做笔记', 'd_note': '追问：天生短板 VS 策略选择'},
    },
    'visual': {
        'name': '视觉功能',
        'role': '细节观察、整体审美',
        'A': {'label': '左脑驱动', 'traits': ['观察力强', '细节敏感'], 'risk': '因小失大', 'growth': '培养整体连接能力'},
        'B': {'label': '右脑驱动', 'traits': ['审美出众', '看整体美感'], 'risk': '忽略功能性', 'growth': '关注实用性'},
        'C': {'label': '双启动', 'traits': ['细节整体平衡'], 'risk': '标准过高', 'growth': '降低完美要求'},
        'D': {'label': '需支持', 'traits': ['易忽略视觉线索'], 'risk': '错过重要信息', 'growth': '培养视觉敏感度', 'd_note': '追问：天生短板 VS 策略选择'},
    },
    'kinesthetic': {
        'name': '体觉功能',
        'role': '行动力、动手能力、身体感知',
        'A': {'label': '左脑驱动', 'traits': ['行动力强', '精细操作'], 'risk': '缺乏直觉信任', 'growth': '留出直觉空间'},
        'B': {'label': '右脑驱动', 'traits': ['直觉反应', '身体先行'], 'risk': '缺乏规划', 'growth': '重要决定理性检查'},
        'C': {'label': '双启动', 'traits': ['力量精准兼备'], 'risk': '完美主义', 'growth': '80%准备就行动'},
        'D': {'label': '需支持', 'traits': ['启动困难'], 'risk': '行动力弱', 'growth': '建立启动仪式', 'd_note': '追问：天生短板 VS 策略选择'},
    },
}

# ============================================================
# 大脑通道 (来源: SEE卡应用手册 ③ 战略偏好)
# ============================================================
BRAIN_CHANNEL_RULES = {
    '深度': {'label': '深度模式', 'desc': '喜欢把一个事做透、钻研到底',
             'strength': '专注、深入、精通', 'risk': '容易钻牛角尖、忽略大局',
             'fit': '研发、技术、学术、精致服务'},
    '广度': {'label': '广度模式', 'desc': '喜欢多任务、新鲜感、整合资源',
             'strength': '多元、灵活、跨界', 'risk': '容易分散、不够专注',
             'fit': '管理、策划、销售、跨界'},
}

# ============================================================
# 大脑接收器 / 接收通道 (来源: SEE卡应用手册 ① 接收通道)
# ============================================================
BRAIN_RECEIVER_RULES = {
    '感知': {'label': '敏感型', 'desc': '优先关注感受、氛围、关系',
             'strength': '共情强、善于维护关系', 'risk': '易被情绪影响、怕冲突',
             'communication': '先给情绪回应，再谈事'},
    '分析': {'label': '分析型', 'desc': '优先关注逻辑、数据、原因',
             'strength': '理性、严谨、不易被骗', 'risk': '决策慢、容易陷入细节',
             'communication': '先给逻辑框架，再给结论'},
    '结果': {'label': '结果型', 'desc': '优先关注目标、行动、效率',
             'strength': '行动快、目标感强', 'risk': '忽略过程和感受、急躁',
             'communication': '先给结论和目标，再讲细节'},
}


def interpret_see_card(portrait):
    """将 SEE 卡 25 题 portrait 转为结构化解释对象。"""
    modules = portrait.get('modules', [])
    dominant = portrait.get('dominant', {})
    handwritten = portrait.get('handwritten', {})
    brain_channel = portrait.get('brain_channel') or handwritten.get('brain_channel', '')
    brain_receiver = portrait.get('brain_receiver') or handwritten.get('brain_receiver', '')
    answers = portrait.get('answers', {})
    confidence = portrait.get('confidence', {})

    # --- observed_data ---
    observed_data = {
        'answers': answers,
        'answers_count': len(answers),
        'confidence': confidence,
        'module_choices': {},
        'handwritten': {
            'self_label': handwritten.get('self_label', ''),
            'strategy_result': handwritten.get('strategy_result', ''),
            'receiver_result': handwritten.get('receiver_result', ''),
            'output_result': handwritten.get('output_result', ''),
        },
        'brain_fields': {
            'brain_channel': brain_channel,
            'brain_receiver': brain_receiver,
        },
    }
    for m in modules:
        observed_data['module_choices'][m['dimension']] = {
            'name': m['name'], 'dominant': m['dominant'],
            'counts': m.get('counts', {}), 'style': m['style'],
            'strength': m.get('strength', ''), 'risk': m.get('risk', ''),
            'growth': m.get('growth', ''),
        }

    # --- rule_hits ---
    rule_hits = []

    # 模块规则命中
    for m in modules:
        dim = m['dimension']
        dom = m['dominant']
        if dim in MODULE_RULES and dom in MODULE_RULES[dim]:
            ri = MODULE_RULES[dim][dom]
            hit = {
                'source': 'SEE卡应用手册 六、引导师速查表',
                'module': m['name'], 'dimension': dim, 'choice': dom,
                'label': ri['label'],
                'meaning': ABCD_DEFINITIONS.get(dom, {}).get('meaning', ''),
                'traits': ri['traits'], 'risk': ri['risk'], 'growth': ri['growth'],
            }
            if 'd_note' in ri:
                hit['note'] = ri['d_note']
            rule_hits.append(hit)

    # 大脑通道规则命中
    bc_parts = [p.strip() for p in brain_channel.replace('、', ',').split(',') if p.strip()]
    for bc in bc_parts:
        if bc in BRAIN_CHANNEL_RULES:
            bcr = BRAIN_CHANNEL_RULES[bc]
            rule_hits.append({
                'source': 'SEE卡应用手册 ③ 战略偏好',
                'type': 'brain_channel', 'value': bc,
                'label': bcr['label'], 'desc': bcr['desc'],
                'strength': bcr['strength'], 'risk': bcr['risk'],
            })

    # 大脑接收器规则命中
    br_parts = [p.strip() for p in brain_receiver.replace('、', ',').split(',') if p.strip()]
    for br in br_parts:
        if br in BRAIN_RECEIVER_RULES:
            brr = BRAIN_RECEIVER_RULES[br]
            rule_hits.append({
                'source': 'SEE卡应用手册 ① 接收通道',
                'type': 'brain_receiver', 'value': br,
                'label': brr['label'], 'desc': brr['desc'],
                'strength': brr['strength'], 'risk': brr['risk'],
                'communication': brr['communication'],
            })

    # 跨模块组合
    combo_matches = []
    if dominant.get('strategic') == 'A' and dominant.get('thinking') == 'A':
        combo_matches.append('目标-分析联动型：左脑精神+左脑思维 → 精密规划执行者')
    if dominant.get('strategic') == 'B' and dominant.get('thinking') == 'B':
        combo_matches.append('愿景-统合联动型：右脑精神+右脑思维 → 战略方向引领者')
    if dominant.get('listening') == 'B' and dominant.get('kinesthetic') == 'B':
        combo_matches.append('情感-直觉联动型：右脑听觉+右脑体觉 → 快速感知响应者')
    c_count = sum(1 for v in dominant.values() if v == 'C')
    if c_count >= 3:
        combo_matches.append('全维平衡型：3个以上功能区双启动 → 全面但需防精力分散')
    # 深度+广度 兼备
    if '深度' in bc_parts and '广度' in bc_parts:
        combo_matches.append('深度广度兼备：既能钻研又能跨界 → 完美搭档潜质（见手册：深度型+广度型=完美搭档）')

    for cm in combo_matches:
        rule_hits.append({'source': 'SEE卡应用手册', 'type': 'combo', 'label': cm})

    # --- evidence ---
    evidence = {
        'source': 'SEE卡25题 + SEE卡应用手册',
        'rule_source': 'kb_portrait/SEE卡应用手册.md',
        'modules_found': [m['dimension'] for m in modules],
        'dominant_choices': {m['dimension']: m['dominant'] for m in modules},
        'brain_channel_source': f"手动勾选: {brain_channel}" if brain_channel else None,
        'brain_receiver_source': f"手动勾选: {brain_receiver}" if brain_receiver else None,
        'handwritten_fields': [k for k, v in handwritten.items() if v and k not in ('brain_channel', 'brain_mode', 'brain_receiver')],
    }

    # --- missing ---
    missing = []
    if not brain_channel:
        missing.append('brain_channel（大脑通道：深度/广度）')
    if not brain_receiver:
        missing.append('brain_receiver（大脑接收器：感知/分析/结果）')
    if not handwritten.get('self_label'):
        missing.append('self_label')
    if not handwritten.get('strategy_result'):
        missing.append('strategy_result')
    if not handwritten.get('receiver_result'):
        missing.append('receiver_result')
    if not handwritten.get('output_result'):
        missing.append('output_result')

    # --- summary ---
    parts = []
    for m in modules:
        parts.append(f"{m['name']}({m['dimension']}): {m['dominant']} {m['style']} | 优势={m.get('strength','')} | 成长={m.get('growth','')}")
    if brain_channel:
        parts.append(f"大脑通道: {brain_channel}")
    if brain_receiver:
        parts.append(f"大脑接收器: {brain_receiver}")
    if combo_matches:
        parts.append(f"组合: {'; '.join(combo_matches)}")

    return {
        'observed_data': observed_data,
        'rule_hits': rule_hits,
        'evidence': evidence,
        'missing': missing,
        'summary': '\n'.join(parts),
    }
