"""SEE 卡 25 题思维画像 — 轻量解释层 (纯代码, 零 LLM)

规则来源: kb_portrait/SEE卡应用手册.md
输入: index.html::buildPortrait() 的 portrait dict
输出: {observed_data, rule_hits, evidence, missing, summary}
"""

import os


# ============================================================
# A/B/C/D 标准定义 (来源: SEE卡应用手册 六、引导师速查表)
# ============================================================
ABCD_DEF = {
    'A': {'meaning': '左脑优势', 'desc': '逻辑、细节、执行面强',
          'positive': '目标明确、逻辑清晰、执行力强', 'risk': '过度分析、钻牛角尖、太急太硬'},
    'B': {'meaning': '右脑优势', 'desc': '直觉、整体、创意面强',
          'positive': '有愿景、战略眼光、情感共鸣', 'risk': '忽略细节、不落地、光想不做'},
    'C': {'meaning': '左右脑双启动', 'desc': '左右脑协同，极强、不费力',
          'positive': '全面、高效、双强', 'risk': '精力分散、两头都想抓、容易过载'},
    'D': {'meaning': '需要支持', 'desc': '相对薄弱或策略性选择不在此处用力',
          'positive': '借力、合作、聚焦天赋', 'risk': '容易卡顿、消耗大',
          'note': 'D有两层含义：先天短板（天生不主场）或策略选择（有能力但选择不做）。遇到D必追问。'},
}

# ============================================================
# 五大功能区 组合规则表 (来源: SEE卡应用手册 六、引导师速查表)
# key: combo like "A", "B", "A+B", "B+C", "A+B+D", etc.
# ============================================================
AREA_COMBO_RULES = {
    'strategic': {
        'A':     {'label': '左脑驱动', 'interpretation': '目标明确，执行力强',
                  'typical': '目标明确，按计划推进', 'risk': '太急、太硬、不顾感受', 'growth': '在计划中留弹性空间，关注他人感受'},
        'B':     {'label': '右脑驱动', 'interpretation': '有愿景，画蓝图',
                  'typical': '有宏大愿景，使命感驱动', 'risk': '光想不做、眼高手低', 'growth': '将愿景拆解为具体可执行步骤'},
        'C':     {'label': '双启动', 'interpretation': '目标+愿景+执行全强',
                  'typical': '方向与动力兼备，不费力', 'risk': '什么都想抓、容易累', 'growth': '学会优先级排序，合理分配精力'},
        'D':     {'label': '需支持', 'interpretation': '易没目标、易放弃',
                  'typical': '需要外部目标引导', 'risk': '缺乏持续动力', 'growth': '建立小目标+外部监督', 'd_note': True},
        'A+B':   {'label': '双脑启动', 'interpretation': '定目标+画愿景',
                  'typical': '既有执行力又有方向感', 'risk': '两种模式可能打架', 'growth': '建立模式切换机制'},
        'A+C':   {'label': '左为主+双', 'interpretation': '目标导向，关键时调用愿景',
                  'typical': '平时执行力强，关键时刻有大局观', 'risk': '平时太急', 'growth': '练习在行动前先看方向'},
        'B+C':   {'label': '右为主+双', 'interpretation': '愿景驱动，关键时调用执行',
                  'typical': '平时看方向，关键时刻能落地', 'risk': '平时想得美', 'growth': '定期检查执行进度'},
        'C+D':   {'label': '双启动+需支持', 'interpretation': '状态好时极强，状态差时完全没动力',
                  'typical': '能量波动大', 'risk': '能量波动大、不稳定', 'growth': '建立能量管理策略，善用高能时段'},
        'A+B+C': {'label': '三强', 'interpretation': '目标、愿景、执行全强',
                  'typical': '全方位驱动', 'risk': '容易过载', 'growth': '学会取舍，不是所有事都需要全力以赴'},
        'A+D':   {'label': '左+需支持', 'interpretation': '目标明确但易放弃',
                  'typical': '有目标但需要外力推动', 'risk': '有头无尾', 'growth': '建立完成激励机制'},
        'B+D':   {'label': '右+需支持', 'interpretation': '有愿景但落地难',
                  'typical': '想法好但执行需要支持', 'risk': '光说不练', 'growth': '找人帮忙落地执行'},
        'A+B+D': {'label': '双脑+需支持', 'interpretation': '能定目标能画愿景，落地需外力',
                  'typical': '方向能力兼备但执行力弱', 'risk': '需要有人推', 'growth': '借助外力推动，建立问责伙伴'},
    },
    'thinking': {
        'A':     {'label': '左脑驱动', 'interpretation': '逻辑清晰，擅分析',
                  'typical': '分析能力强，逻辑严谨', 'risk': '过度分析、钻牛角尖、思维散收不回', 'growth': '定时收束思维，设定分析截止点'},
        'B':     {'label': '右脑驱动', 'interpretation': '战略眼光，看整体',
                  'typical': '宏观把握能力强，有战略视野', 'risk': '忽略细节、逻辑不严', 'growth': '补充细节论证，用数据支撑直觉'},
        'C':     {'label': '双启动', 'interpretation': '深度分析+宏观战略',
                  'typical': '既能深入分析又能跳出看全局', 'risk': '想太多、切换累', 'growth': '合理分配思考精力，分阶段切换'},
        'D':     {'label': '需支持', 'interpretation': '想问题乱、易被带偏',
                  'typical': '独立思考有困难', 'risk': '容易被别人思路带走', 'growth': '建立思维框架，学会结构化思考', 'd_note': True},
        'A+B':   {'label': '双脑启动', 'interpretation': '分析细节+看全局',
                  'typical': '细节与大局兼顾', 'risk': '切换不够顺', 'growth': '练习在两种模式间灵活切换'},
        'A+C':   {'label': '左为主+双', 'interpretation': '逻辑分析为主，关键时看全局',
                  'typical': '平时分析细致，关键时刻有大局观', 'risk': '平时太细', 'growth': '定期跳出细节看全局'},
        'B+C':   {'label': '右为主+双', 'interpretation': '战略为主，关键时深入分析',
                  'typical': '平时看大局，关键时刻能深入', 'risk': '平时看大局', 'growth': '重要决策时补充深入分析'},
        'C+D':   {'label': '双启动+需支持', 'interpretation': '状态好时思路清晰，状态差时一团乱麻',
                  'typical': '思维时灵时不灵', 'risk': '思维时灵时不灵', 'growth': '善用思维清晰时处理复杂问题'},
        'A+B+C': {'label': '三强', 'interpretation': '分析+战略+逻辑全强',
                  'typical': '思维全方位强大', 'risk': '思维过载、停不下来', 'growth': '学会思维"关机"，给大脑休息时间'},
        'A+D':   {'label': '左+需支持', 'interpretation': '逻辑清但复杂问题易卡',
                  'typical': '简单问题能分析，复杂问题需帮助', 'risk': '想得通但说不清', 'growth': '复杂问题分步解决，寻求外部梳理'},
        'B+D':   {'label': '右+需支持', 'interpretation': '战略好但逻辑不严',
                  'typical': '方向对但论证弱', 'risk': '方向对但论证弱', 'growth': '用框架补充逻辑论证'},
        'A+B+D': {'label': '双脑+需支持', 'interpretation': '能分析能战略，深度思考需外力',
                  'typical': '能力有但需要帮助理清思路', 'risk': '需要帮忙理思路', 'growth': '借助外部讨论梳理深度思考'},
    },
    'kinesthetic': {
        'A':     {'label': '左脑驱动', 'interpretation': '动手精准，擅精细',
                  'typical': '精细操作能力强，动作精准', 'risk': '太慢、太细、不敢放手', 'growth': '适当加快节奏，信任直觉'},
        'B':     {'label': '右脑驱动', 'interpretation': '反应快、直觉好',
                  'typical': '行动迅速，身体直觉强', 'risk': '毛躁、不稳、坐不住', 'growth': '重要行动前加入理性检查'},
        'C':     {'label': '双启动', 'interpretation': '精准+快速',
                  'typical': '快准兼备', 'risk': '动不停、静不下', 'growth': '学会适时停下来调整'},
        'D':     {'label': '需支持', 'interpretation': '行动慢、不爱动',
                  'typical': '行动力偏弱', 'risk': '启动困难、行动力弱', 'growth': '建立启动仪式，从小行动开始', 'd_note': True},
        'A+B':   {'label': '双脑启动', 'interpretation': '精细+快速',
                  'typical': '速度与精度兼顾', 'risk': '想快但手慢', 'growth': '练习在速度与精度间找平衡'},
        'A+C':   {'label': '左为主+双', 'interpretation': '精细为主，关键时快速',
                  'typical': '平时精细', 'risk': '平时慢', 'growth': '关键时刻敢于加速'},
        'B+C':   {'label': '右为主+双', 'interpretation': '快速为主，关键时精细',
                  'typical': '平时快', 'risk': '平时快但不够细', 'growth': '重要操作时放慢检查'},
        'C+D':   {'label': '双启动+需支持', 'interpretation': '状态好时行动力爆棚，状态差时完全不想动',
                  'typical': '行动力时灵时不灵', 'risk': '行动力时灵时不灵', 'growth': '善用高能时段完成重要行动'},
        'A+B+C': {'label': '三强', 'interpretation': '手眼身协调极强',
                  'typical': '身体协调能力顶级', 'risk': '动个不停', 'growth': '学会适时休息和恢复'},
        'A+D':   {'label': '左+需支持', 'interpretation': '精细强但易累',
                  'typical': '精细活能做但体力有限', 'risk': '需帮忙干体力活', 'growth': '精细活自己做，体力活借力'},
        'B+D':   {'label': '右+需支持', 'interpretation': '反应快但持久差',
                  'typical': '爆发力强但耐力不足', 'risk': '需收尾、善后', 'growth': '建立持续行动节奏，借助外力收尾'},
        'A+B+D': {'label': '双脑+需支持', 'interpretation': '精细+快速，持续需外力',
                  'typical': '能力有但缺持续力', 'risk': '需要有人推', 'growth': '建立问责机制，让外力推动持续'},
    },
    'listening': {
        'A':     {'label': '左脑驱动', 'interpretation': '语言理解强，抓重点',
                  'typical': '能快速抓住关键信息', 'risk': '太理性、不听情绪', 'growth': '加入情感确认，先回应情绪再谈事'},
        'B':     {'label': '右脑驱动', 'interpretation': '情感共情强，听话外音',
                  'typical': '共情能力强，听出言外之意', 'risk': '太敏感、过度解读', 'growth': '关注事实层面，确认理解'},
        'C':     {'label': '双启动', 'interpretation': '内容+情感双强',
                  'typical': '全面倾听', 'risk': '听太多、易累', 'growth': '调整倾听深度，保护自己的精力'},
        'D':     {'label': '需支持', 'interpretation': '听不进、易走神',
                  'typical': '倾听需要外部支持', 'risk': '重要信息遗漏', 'growth': '重要对话做笔记，减少干扰', 'd_note': True},
        'A+B':   {'label': '双脑启动', 'interpretation': '内容+情绪都听',
                  'typical': '全面倾听', 'risk': '切换时可能漏', 'growth': '练习在内容与情绪间快速切换'},
        'A+C':   {'label': '左为主+双', 'interpretation': '内容为主，关键时共情',
                  'typical': '平时理性倾听', 'risk': '平时理性', 'growth': '关键时刻切换到共情模式'},
        'B+C':   {'label': '右为主+双', 'interpretation': '情感为主，关键时理性',
                  'typical': '平时感性倾听', 'risk': '平时感性', 'growth': '重要决策时切换到理性分析'},
        'C+D':   {'label': '双启动+需支持', 'interpretation': '状态好时沟通顺畅，状态差时完全听不进去',
                  'typical': '沟通能力时灵时不灵', 'risk': '沟通能力时灵时不灵', 'growth': '善用沟通顺畅时处理重要对话'},
        'A+B+C': {'label': '三强', 'interpretation': '沟通理解极强',
                  'typical': '倾听能力顶级', 'risk': '易内耗', 'growth': '学会筛选信息，保护精力'},
        'A+D':   {'label': '左+需支持', 'interpretation': '能听懂但易忘',
                  'typical': '理解力有但记忆力弱', 'risk': '需重复或写下来', 'growth': '重要信息及时记录'},
        'B+D':   {'label': '右+需支持', 'interpretation': '能共情但易过载',
                  'typical': '共情强但容易情绪过载', 'risk': '需帮TA过滤情绪', 'growth': '建立情绪边界，学会过滤'},
        'A+B+D': {'label': '双脑+需支持', 'interpretation': '能听内容能听情绪，专注需外力',
                  'typical': '倾听能力强但需安静', 'risk': '需安静环境', 'growth': '创造专注倾听的环境'},
    },
    'visual': {
        'A':     {'label': '左脑驱动', 'interpretation': '观察力强，发现细节',
                  'typical': '能发现别人看不到的细节', 'risk': '太挑剔、只见细节', 'growth': '培养整体连接能力'},
        'B':     {'label': '右脑驱动', 'interpretation': '审美在线，看整体',
                  'typical': '有审美眼光，把握整体', 'risk': '忽略细节、粗心', 'growth': '补充细节检查'},
        'C':     {'label': '双启动', 'interpretation': '细节+整体双强',
                  'typical': '视觉能力全面', 'risk': '眼太尖、易累', 'growth': '适当降低标准，保护视觉精力'},
        'D':     {'label': '需支持', 'interpretation': '粗心、漏看、审美一般',
                  'typical': '视觉敏感度偏低', 'risk': '错过重要视觉信息', 'growth': '培养视觉敏感度，借助工具', 'd_note': True},
        'A+B':   {'label': '双脑启动', 'interpretation': '细节+整体都看',
                  'typical': '全面观察', 'risk': '两种模式打架', 'growth': '练习模式切换'},
        'A+C':   {'label': '左为主+双', 'interpretation': '细节为主，关键时看整体',
                  'typical': '平时细致观察', 'risk': '平时细', 'growth': '关键时刻跳出细节看大局'},
        'B+C':   {'label': '右为主+双', 'interpretation': '整体为主，关键时抠细节',
                  'typical': '平时看全局', 'risk': '平时粗', 'growth': '重要场合时仔细检查细节'},
        'C+D':   {'label': '双启动+需支持', 'interpretation': '状态好时眼尖，状态差时什么都看不见',
                  'typical': '视觉能力时灵时不灵', 'risk': '视觉能力时灵时不灵', 'growth': '善用视觉敏锐时处理重要任务'},
        'A+B+C': {'label': '三强', 'interpretation': '观察+审美极强',
                  'typical': '视觉能力顶级', 'risk': '易挑剔、要求高', 'growth': '降低完美要求，80分即可'},
        'A+D':   {'label': '左+需支持', 'interpretation': '能看见但易累',
                  'typical': '细节观察力有但容易疲劳', 'risk': '需帮忙复查', 'growth': '重要工作后让他人复查'},
        'B+D':   {'label': '右+需支持', 'interpretation': '有审美但忽略细节',
                  'typical': '审美有但细节弱', 'risk': '需帮忙检查细节', 'growth': '建立细节检查清单'},
        'A+B+D': {'label': '双脑+需支持', 'interpretation': '看细节看整体，专注需外力',
                  'typical': '视觉能力有但需安静', 'risk': '需安静环境', 'growth': '创造专注观察的环境'},
    },
}

# ============================================================
# 大脑通道 (来源: SEE卡应用手册 ③ 战略偏好)
# ============================================================
CHANNEL_RULES = {
    '深度': {'label': '深度模式', 'desc': '喜欢把一个事做透、钻研到底',
             'strength': '专注、深入、精通', 'risk': '容易钻牛角尖、忽略大局'},
    '广度': {'label': '广度模式', 'desc': '喜欢多任务、新鲜感、整合资源',
             'strength': '多元、灵活、跨界', 'risk': '容易分散、不够专注'},
}

# ============================================================
# 大脑接收器 (来源: SEE卡应用手册 ① 接收通道)
# ============================================================
RECEIVER_RULES = {
    '感知': {'label': '敏感型', 'desc': '优先关注感受、氛围、关系',
             'strength': '共情强、善于维护关系', 'risk': '易被情绪影响、怕冲突'},
    '分析': {'label': '分析型', 'desc': '优先关注逻辑、数据、原因',
             'strength': '理性、严谨、不易被骗', 'risk': '决策慢、容易陷入细节'},
    '结果': {'label': '结果型', 'desc': '优先关注目标、行动、效率',
             'strength': '行动快、目标感强', 'risk': '忽略过程和感受、急躁'},
}

# ============================================================
# 知识库参考文本 (LLM prompt 上下文)
# ============================================================
_KB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'kb_portrait')
_KB_CACHE = None


def load_see_card_context():
    """加载 SEE卡应用手册的关键参考段落。"""
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
    excerpts = []
    for marker in ['SEE 卡不贴标签', '核心理念', '它是"镜子"', 'SEE 卡是 SEE 生命印迹体系中的第一个工具']:
        idx = text.find(marker)
        if idx >= 0:
            excerpts.append(text[idx:idx+200].strip())
    idx = text.find('沟通翻译器')
    if idx >= 0:
        excerpts.append(text[idx:idx+350].strip())
    idx = text.find('③ 战略偏好')
    if idx >= 0:
        excerpts.append(text[idx:idx+300].strip())
    idx = text.find('D 的两层智慧')
    if idx >= 0:
        excerpts.append(text[idx:idx+250].strip())
    idx = text.find('使用提醒')
    if idx >= 0:
        excerpts.append(text[idx:idx+200].strip())
    _KB_CACHE = '\n\n---\n\n'.join(e for e in excerpts if e)
    # Filter out excerpts containing forbidden terms for SEE card reports
    forbidden = ['纹型', 'TRC', 'ATD', '皮纹', '指纹']
    if _KB_CACHE:
        lines = _KB_CACHE.split('\n')
        clean_lines = []
        skip = False
        for line in lines:
            if '---' in line and len(line) < 10:
                skip = False
            if any(f in line for f in forbidden):
                skip = True
                continue
            if not skip:
                clean_lines.append(line)
        _KB_CACHE = '\n'.join(clean_lines).strip()
    if len(_KB_CACHE) > 4000:
        _KB_CACHE = _KB_CACHE[:4000] + '\n\n...'
    return _KB_CACHE


# ============================================================
# 组合规则匹配
# ============================================================

def _match_combo(counts):
    """根据选项计数字典匹配最佳组合规则。
    返回 (rule_key, matched_options, secondary_signals)
    D 优先尝试与 top 选项合并为手动支持的主 key；
    否则 D 作为辅助信号单独返回。
    """
    if not counts:
        return None, [], []
    total = sum(counts.get(k, 0) for k in 'ABCD')
    if total == 0:
        return None, [], []

    # A、B、C 全部存在 → 立即返回 A+B+C，D 如有则作为辅助信号
    a_cnt, b_cnt, c_cnt, d_cnt = (counts.get(k, 0) for k in 'ABCD')
    if a_cnt > 0 and b_cnt > 0 and c_cnt > 0:
        secondary = []
        if d_cnt > 0:
            secondary.append({'type': 'D_support', 'count': d_cnt,
                'note': 'D有两层含义：先天短板或策略选择。建议追问：天生 VS 策略。'})
        return 'A+B+C', ['A','B','C'], secondary

    # A、B、D 全部存在且 C 不存在 → A+B+D
    if a_cnt > 0 and b_cnt > 0 and d_cnt > 0 and c_cnt == 0:
        return 'A+B+D', ['A','B','D'], []

    max_count = max(counts.get(k, 0) for k in 'ABCD')
    top_opts = sorted([k for k in 'ABCD' if counts.get(k, 0) == max_count])
    d_count = counts.get('D', 0)
    has_D = d_count > 0
    top_has_D = has_D and 'D' in top_opts

    # 只有 D
    if top_opts == ['D']:
        return 'D', ['D'], []

    if not top_has_D:
        # ABC 按现有规则匹配，D 单独作为辅助信号
        abc_top = [k for k in top_opts if k != 'D']
        if len(abc_top) == 1:
            key = abc_top[0]
            matched = abc_top
        else:
            key = '+'.join(sorted(abc_top))
            matched = sorted(abc_top)
        secondary = []
        if has_D:
            secondary.append({'type': 'D_support', 'count': d_count,
                'note': 'D有两层含义：先天短板或策略选择。建议追问：天生 VS 策略。'})
        return key, matched, secondary

    # D 在 top_opts 中 → 优先 D-combo 主 key
    SUPPORTED_D_COMBOS = {'A+D', 'B+D', 'C+D', 'A+B+D'}
    non_D_top = sorted([k for k in top_opts if k != 'D'])
    # 用 top_opts 中的非 D 选项 + D 构成候选 key
    candidate = '+'.join(sorted(non_D_top + ['D']))
    if candidate in SUPPORTED_D_COMBOS:
        return candidate, sorted(non_D_top + ['D']), []

    # 不支持的主 key (如 B+C+D / A+C+D / A+B+C+D) → ABC top 为主, D 为辅
    abc_key = '+'.join(non_D_top) if non_D_top else None
    if abc_key:
        secondary = [{'type': 'D_support', 'count': d_count,
            'note': 'D有两层含义：先天短板或策略选择。建议追问：天生 VS 策略。'}]
        return abc_key, non_D_top, secondary

    return 'D', ['D'], []

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
        'answers': answers, 'answers_count': len(answers),
        'confidence': confidence, 'module_choices': {},
        'handwritten': {
            'self_label': handwritten.get('self_label', ''),
            'strategy_result': handwritten.get('strategy_result', ''),
            'receiver_result': handwritten.get('receiver_result', ''),
            'output_result': handwritten.get('output_result', ''),
        },
        'brain_fields': {'brain_channel': brain_channel, 'brain_receiver': brain_receiver},
    }
    for m in modules:
        observed_data['module_choices'][m['dimension']] = {
            'name': m['name'], 'dominant': m['dominant'], 'counts': m.get('counts', {}),
            'style': m['style'], 'strength': m.get('strength', ''), 'risk': m.get('risk', ''),
            'growth': m.get('growth', ''),
        }

    # --- rule_hits: 组合规则匹配 ---
    rule_hits = []
    for m in modules:
        dim = m['dimension']
        counts = m.get('counts', {})
        if not counts or dim not in AREA_COMBO_RULES:
            continue

        combo_key, matched_opts, secondary = _match_combo(counts)
        if not combo_key or combo_key not in AREA_COMBO_RULES[dim]:
            continue

        rule = AREA_COMBO_RULES[dim][combo_key]
        hit = {
            'source': 'SEE卡应用手册 六、引导师速查表',
            'module': m['name'], 'dimension': dim,
            'counts': counts,
            'matched_options': matched_opts,
            'matched_rule_key': combo_key,
            'label': rule['label'],
            'manual_interpretation': rule['interpretation'],
            'typical_behavior': rule['typical'],
            'overuse_or_risk': rule['risk'],
            'growth': rule['growth'],
        }
        # D 辅助信号注入 d_note
        has_D_in_secondary = any(s.get('type') == 'D_support' for s in secondary)
        if rule.get('d_note') or 'D' in matched_opts or has_D_in_secondary:
            hit['d_note'] = 'D有两层含义：先天短板（天生不主场）或策略选择（有能力但选择不做）。遇到D必追问。'
        if secondary:
            hit['secondary_signals'] = secondary
        rule_hits.append(hit)

    # 大脑通道
    bc_parts = [p.strip() for p in brain_channel.replace('、', ',').split(',') if p.strip()]
    for bc in bc_parts:
        if bc in CHANNEL_RULES:
            cr = CHANNEL_RULES[bc]
            rule_hits.append({'source': 'SEE卡应用手册 ③ 战略偏好', 'type': 'brain_channel',
                'value': bc, 'label': cr['label'], 'desc': cr['desc'],
                'strength': cr['strength'], 'risk': cr['risk']})

    # 大脑接收器
    br_parts = [p.strip() for p in brain_receiver.replace('、', ',').split(',') if p.strip()]
    for br in br_parts:
        if br in RECEIVER_RULES:
            rr = RECEIVER_RULES[br]
            rule_hits.append({'source': 'SEE卡应用手册 ① 接收通道', 'type': 'brain_receiver',
                'value': br, 'label': rr['label'], 'desc': rr['desc'],
                'strength': rr['strength'], 'risk': rr['risk']})

    # 跨模块组合（基于 matched_rule_key，不使用 legacy dominant）
    combos = []
    # 收集各模块的匹配 key
    matched_keys = {}
    for h in rule_hits:
        if 'matched_rule_key' in h:
            matched_keys[h['dimension']] = h['matched_rule_key']

    # 单键匹配才做跨模块联动（A+B+C 等组合不参与跨模块）
    sk = matched_keys.get('strategic', '')
    tk = matched_keys.get('thinking', '')
    lk = matched_keys.get('listening', '')
    kk = matched_keys.get('kinesthetic', '')
    if sk == 'A' and tk == 'A':
        combos.append('目标-分析联动：左脑精神+左脑思维 → 精密规划执行者')
    if sk == 'B' and tk == 'B':
        combos.append('愿景-统合联动：右脑精神+右脑思维 → 战略方向引领者')
    if lk == 'B' and kk == 'B':
        combos.append('情感-直觉联动：右脑听觉+右脑体觉 → 快速感知响应者')
    c_count = sum(1 for v in matched_keys.values() if v == 'C')
    if c_count >= 3:
        combos.append('全维平衡：3个以上功能区双启动 → 全面但需防精力分散')
    if '深度' in bc_parts and '广度' in bc_parts:
        combos.append('深度广度兼备：既能钻研又能跨界 → 完美搭档潜质')
    for cm in combos:
        rule_hits.append({'source': 'SEE卡应用手册', 'type': 'combo', 'label': cm})

    # --- evidence ---
    # 从 rule_hits 收集 matched_rule_key（不用 legacy dominant）
    matched_keys = {}
    for h in rule_hits:
        if 'matched_rule_key' in h:
            matched_keys[h['dimension']] = h['matched_rule_key']
    evidence = {
        'source': 'SEE卡25题 + SEE卡应用手册',
        'rule_source': 'kb_portrait/SEE卡应用手册.md',
        'modules_found': [m['dimension'] for m in modules],
        'matched_choices': matched_keys,
        'brain_channel_source': f"手动勾选: {brain_channel}" if brain_channel else None,
        'brain_receiver_source': f"手动勾选: {brain_receiver}" if brain_receiver else None,
        'handwritten_fields': [k for k, v in handwritten.items() if v and k not in ('brain_channel', 'brain_mode', 'brain_receiver')],
    }

    # --- missing ---
    missing = []
    if not brain_channel: missing.append('brain_channel（大脑通道：深度/广度）')
    if not brain_receiver: missing.append('brain_receiver（大脑接收器：感知/分析/结果）')
    if not handwritten.get('self_label'): missing.append('self_label')
    if not handwritten.get('strategy_result'): missing.append('strategy_result')
    if not handwritten.get('receiver_result'): missing.append('receiver_result')
    if not handwritten.get('output_result'): missing.append('output_result')

    # --- summary ---
    parts = []
    for m in modules:
        mk = matched_keys.get(m['dimension'], m['dominant'])
        parts.append(f"{m['name']}({m['dimension']}): counts={m.get('counts',{})} | matched={mk}")
    if brain_channel: parts.append(f"大脑通道: {brain_channel}")
    if brain_receiver: parts.append(f"大脑接收器: {brain_receiver}")
    if combos: parts.append(f"组合: {'; '.join(combos)}")
    summary = '\n'.join(parts)

    return {'observed_data': observed_data, 'rule_hits': rule_hits,
            'evidence': evidence, 'missing': missing, 'summary': summary}
