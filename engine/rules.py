"""Layer 1: 结构层 — 纯代码, 零 LLM (评分阈值来自培训手册 p11-12)"""

import json

# ============================================================
# 纹型 × 功能区矩阵 (来自培训手册 p3-p12)
# ============================================================
PATTERN_MATRIX = {
    'Wt': {
        'spirit_left':  '目标坚定，执行时沉默专注，可能固执不变通',
        'spirit_right': '目标空间感强，愿景完整但表达被动',
        'thinking_left': '逻辑完整，分析被动，需要外力推动思考',
        'thinking_right': '创意有空间感和完整性，但表达被动',
        'kinesthetic_left': '行动目标明确但被动，需要计划推动',
        'kinesthetic_right': '动作完整但保守，不喜冒险',
        'auditory_left': '倾听专注但被动，需要明确指令',
        'auditory_right': '对音乐有完整感知，但表达保守',
        'visual_left': '观察完整细致，但可能忽略重点',
        'visual_right': '观察完整，注重完整性',
    },
    'Ws': {
        'spirit_left':  '执行中好为人师，喜欢指导他人，重面子',
        'spirit_right': '设定权威性目标，希望获得他人认可',
        'thinking_left': '分析时好为人师，喜欢总结规律教导他人',
        'thinking_right': '创意注重实用性和权威性',
        'kinesthetic_left': '行动中展现权威，喜欢指导他人操作',
        'kinesthetic_right': '动作展现权威和自信，好胜心强',
        'auditory_left': '倾听时好为人师，喜欢纠正他人',
        'auditory_right': '喜欢权威性音乐，好为人师推荐',
        'visual_left': '观察好为人师，喜欢指出他人错误',
        'visual_right': '观察展现权威，注重标准',
    },
    'Wsc': {
        'spirit_left':  '执行中有强烈权威感，注重计划和规则，喜欢带领他人',
        'spirit_right': '目标设定有权威倾向，希望获得广泛认可和尊重',
        'thinking_left': '分析时注重规则和权威，逻辑严谨有说服力',
        'thinking_right': '创意兼具权威性和实用性，善于融合',
        'kinesthetic_left': '行动有权威感，注重操作的标准和规范',
        'kinesthetic_right': '动作展现自信和力量，有领导气质',
        'auditory_left': '倾听时有权威意识，喜欢纠正和指导',
        'auditory_right': '偏好有权威感的音乐，对音质有要求',
        'visual_left': '观察注重标准和细节，对不符合规范的事物敏感',
        'visual_right': '观察有审美权威，注重品质和格调',
    },
    'We': {
        'spirit_left':  '执行时带入情感角色，可能因感受变化而调整决策',
        'spirit_right': '目标充满想象力和情感色彩，可能善变',
        'thinking_left': '分析中带入情感和联想，逻辑可能跳跃',
        'thinking_right': '创意丰富，联想力强，情感饱满',
        'kinesthetic_left': '行动充满情感表达，可能随感受变化',
        'kinesthetic_right': '动作富有表现力和情感，有感染力',
        'auditory_left': '倾听中产生丰富联想，容易走神',
        'auditory_right': '音乐联想丰富，情感共鸣强',
        'visual_left': '观察产生丰富联想，可能偏离主题',
        'visual_right': '观察富有情感，联想丰富',
    },
    'Wc': {
        'spirit_left':  '执行前权衡性价比，可能因过度谋略而拖延行动',
        'spirit_right': '目标多元，追求性价比，容易摇摆不定',
        'thinking_left': '分析注重性价比和多元可能，谋略思维',
        'thinking_right': '创意多元，考虑性价比，善于整合资源',
        'kinesthetic_left': '行动前计算性价比，可能因权衡而拖延',
        'kinesthetic_right': '动作考虑性价比，可能因权衡而犹豫',
        'auditory_left': '倾听时权衡信息价值，选择性接收',
        'auditory_right': '音乐品味多元，考虑流行度',
        'visual_left': '观察权衡价值，关注实用信息',
        'visual_right': '观察权衡价值，注重实用性',
    },
    'Wd': {
        'spirit_left':  '快速决策，执行力强，但内心固执己见',
        'spirit_right': '目标洞察力强，能快速建立愿景框架',
        'thinking_left': '分析快速，洞察力强，但结论可能固执',
        'thinking_right': '创意洞察力强，能快速建立概念框架',
        'kinesthetic_left': '行动快速准确，但方式可能固执',
        'kinesthetic_right': '动作快速协调，善于借力',
        'auditory_left': '倾听洞察力强，能听出弦外之音',
        'auditory_right': '音乐洞察力强，能快速理解复杂旋律',
        'visual_left': '观察洞察力强，能快速发现关键',
        'visual_right': '观察洞察力强，能快速把握全局',
    },
    'Wi': {
        'spirit_left':  '执行时考虑家庭和感情因素，可能缺乏决断力',
        'spirit_right': '目标以家庭和情感为中心，事业心较弱',
        'thinking_left': '分析受感情影响，逻辑性可能较弱',
        'thinking_right': '创意偏向情感和家庭主题',
        'kinesthetic_left': '行动考虑他人感受，可能不够果断',
        'kinesthetic_right': '动作温和，注重人际和谐',
        'auditory_left': '倾听注重情感内容，对温情话语敏感',
        'auditory_right': '喜欢温情音乐，注重情感表达',
        'visual_left': '观察注重情感细节，如表情微变化',
        'visual_right': '观察注重情感表达，感受细腻',
    },
    'Wpe': {
        'spirit_left':  '追求执行过程的完美，可能因细节停滞',
        'spirit_right': '追求完美的目标设定，可能因高标准而压力大',
        'thinking_left': '分析追求完美细节，可能过度批判',
        'thinking_right': '追求创意完美，可能因高标准而产出少',
        'kinesthetic_left': '追求行动完美，可能因细节影响效率',
        'kinesthetic_right': '动作追求完美协调，可能因苛求而紧张',
        'auditory_left': '倾听追求完美理解，可能过度分析',
        'auditory_right': '追求音乐完美，对音质要求苛刻',
        'visual_left': '观察追求完美，可能过度关注细节',
        'visual_right': '观察追求完美，对细节要求高',
    },
    'Wl': {
        'spirit_left':  '执行中展现优越感，注重品质和形象',
        'spirit_right': '目标设定有优越感，追求高品质成果',
        'thinking_left': '分析中展现优越感，对他人思路挑剔',
        'thinking_right': '创意有优越感，追求独特和高品质',
        'kinesthetic_left': '行动展现优越感，注重操作品质',
        'kinesthetic_right': '动作展现优越感，姿态讲究',
        'auditory_left': '倾听挑剔，对声音品质要求高',
        'auditory_right': '音乐品味有优越感，喜欢小众高品质',
        'visual_left': '观察挑剔，注重品质和美观',
        'visual_right': '观察有优越感，注重视觉品质',
    },
    'Lu': {
        'spirit_left':  '执行时需要榜样参照，模仿能力强',
        'spirit_right': '目标容易受环境影响，模仿他人志向',
        'thinking_left': '分析需要参照现有模式，模仿性强',
        'thinking_right': '创意模仿他人风格，可塑性强',
        'kinesthetic_left': '行动模仿他人，需要示范',
        'kinesthetic_right': '动作模仿性强，善于学习他人',
        'auditory_left': '倾听模仿他人表达方式',
        'auditory_right': '音乐喜好模仿流行趋势',
        'visual_left': '观察模仿他人视角',
        'visual_right': '观察模仿他人，可塑性强',
    },
    'Lf': {
        'spirit_left':  '执行原则性强，按规则办事，应变弱',
        'spirit_right': '目标专注，但可能自我设限',
        'thinking_left': '分析原则性强，逻辑严谨但不够灵活',
        'thinking_right': '创意受原则限制，不够开放',
        'kinesthetic_left': '行动按原则进行，流程严谨',
        'kinesthetic_right': '动作受原则限制，不够舒展',
        'auditory_left': '倾听原则性强，只听认同的内容',
        'auditory_right': '音乐品味固定，不喜变化',
        'visual_left': '观察按原则进行，模式固定',
        'visual_right': '观察按原则，模式固定',
    },
    'R': {
        'spirit_left':  '执行方式与众不同，喜欢尝试新方法',
        'spirit_right': '目标追求独特，不喜欢常规路径',
        'thinking_left': '分析角度与众不同，喜欢反向思考',
        'thinking_right': '创意独特，追求颠覆性想法',
        'kinesthetic_left': '行动方式独特，不喜欢常规做法',
        'kinesthetic_right': '动作独特有个性，喜欢创新表达',
        'auditory_left': '倾听角度独特，喜欢听非主流观点',
        'auditory_right': '音乐品味独特，喜欢实验性音乐',
        'visual_left': '观察角度独特，能看到他人忽略的',
        'visual_right': '观察角度独特，能看到别人忽略的美',
    },
    'X': {
        'spirit_left':  '执行时需要安全感，按部就班，害怕变化',
        'spirit_right': '目标追求安全感，偏好稳定可预测的方向',
        'thinking_left': '分析需要安全感，偏好分段逐步推理',
        'thinking_right': '创意需要安全感，偏好熟悉领域',
        'kinesthetic_left': '行动需要安全感，偏好熟悉流程',
        'kinesthetic_right': '动作保守，需要安全感',
        'auditory_left': '倾听需要安全感，偏好熟悉声音',
        'auditory_right': '偏好熟悉安全的音乐风格',
        'visual_left': '观察需要安全感，偏好熟悉环境',
        'visual_right': '观察需要安全感，偏好熟悉视觉',
    },
    'Xn': {
        'spirit_left':  '执行力强，热情主动，但可能急于求成',
        'spirit_right': '目标感强，喜欢掌控全局，愿景宏大',
        'thinking_left': '分析快速果断，但可能不够细致',
        'thinking_right': '创意执行力强，能快速实现想法',
        'kinesthetic_left': '行动热情主动，但可能计划性不足',
        'kinesthetic_right': '动作热情奔放，喜欢主导活动',
        'auditory_left': '倾听快速抓重点，但可能不够耐心',
        'auditory_right': '喜欢热情奔放的音乐，音量可能较大',
        'visual_left': '观察快速但可能不够细致',
        'visual_right': '观察快速果决，注重效率',
    },
}

# ============================================================
# 规则引擎
# ============================================================

def apply_rules(metrics):
    """纯计算，不做解释。返回结构化 dict。"""
    result = {'trc': None, 'atd': None, 'channel': None, 'behavior': None,
              'top_three': [], 'bottom_one': None, 'combos': [], 'pattern_insights': []}

    trc = metrics.get('trc')
    atd = metrics.get('atd')
    behavior_mode = metrics.get('behavior_mode', '')
    primary_channel = metrics.get('primary_channel', '')
    func = metrics.get('function_scores', {})
    top3 = metrics.get('top_three_areas', [])
    lowest = metrics.get('lowest_area')
    patterns = metrics.get('function_patterns', {})

    # --- TRC ---
    if trc is not None:
        if trc > 220:
            result['trc'] = {'value': trc, 'level': 'ultra_high', 'label': '超全局思维',
                             'capacity': '同一时间承载与接纳事物 4 件以上',
                             'traits': ['全局思维', '一心多用', '不喜欢一成不变'],
                             'risks': ['容易分散', '难聚焦单一任务'],
                             'supports': ['用项目制承载多元兴趣', '建立优先级系统', '阶段性目标聚焦']}
        elif trc >= 180:
            result['trc'] = {'value': trc, 'level': 'high', 'label': '高TRC',
                             'capacity': '同一时间承载与接纳事物 3-4 件',
                             'traits': ['多元', '发散', '多线程'],
                             'risks': ['容易分散', '不喜欢重复', '需要收束'],
                             'supports': ['选择几个才艺和性向深耕', '避免样样通样样松', '用阶段性目标聚焦']}
        elif trc >= 140:
            result['trc'] = {'value': trc, 'level': 'mid_high', 'label': '中高TRC',
                             'capacity': '同一时间承载与接纳事物 2-3 件',
                             'traits': ['均衡偏多', '可兼顾'], 'risks': [], 'supports': ['全方位学习与多元发展']}
        elif trc >= 80:
            result['trc'] = {'value': trc, 'level': 'mid', 'label': '中TRC',
                             'capacity': '同一时间承载与接纳事物 1-2 件',
                             'traits': ['均衡', '适应'], 'risks': [], 'supports': ['根据阶段目标灵活安排']}
        elif trc > 0:
            result['trc'] = {'value': trc, 'level': 'low', 'label': '低TRC',
                             'capacity': '同一时间承载与接纳事物 1 件',
                             'traits': ['聚焦', '深耕', '单线程'],
                             'risks': ['切换任务耗能大'],
                             'supports': ['专注某一领域深耕', '一次只给一个目标', '减少多任务切换']}

    # --- ATD ---
    if atd is not None:
        if atd <= 36:
            result['atd'] = {'value': atd, 'level': 'sensitive', 'label': '注重感受型(快速)',
                             'traits': ['反应快', '敏感', '启动快'],
                             'focus': '注重感受 —— 情感、感觉、情绪',
                             'risks': ['快而粗', '情绪或语气容易影响状态'],
                             'supports': ['训练复述', '加入检查步骤', '在冲动前暂停']}
        elif atd <= 41:
            result['atd'] = {'value': atd, 'level': 'analytic', 'label': '注重分析型(均衡)',
                             'traits': ['均衡', '稳定适应'],
                             'focus': '注重分析 —— 了解、知识、经验、逻辑、因果关系',
                             'risks': [], 'supports': ['适合常规教学与工作节奏']}
        else:
            result['atd'] = {'value': atd, 'level': 'result', 'label': '注重结果型(沉稳)',
                             'traits': ['沉稳', '慢热', '深度消化'],
                             'focus': '注重结果 —— 目标、结果、不掺杂个人情绪、直接具象表达',
                             'risks': ['被催促会压力大', '易被误解为慢或不上心'],
                             'supports': ['提前预告', '分解任务', '给足预热和消化时间']}

    # --- 学习通道 ---
    if primary_channel:
        result['channel'] = {
            'primary': primary_channel,
            'label': f'{primary_channel}主导型',
            'scores': metrics.get('learning_channels', {}),
        }

    # --- 行为模式 ---
    if behavior_mode:
        mode_data = {
            '动机型': {'traits': ['动机驱动'], 'desc': '凡事讲求动机，先有目标意义再行动。目标明确，不宜强迫。善于交际，喜欢分享，具有领导气质。',
                       'risks': ['不喜欢被直接命令', '可能冲动'], 'supports': ['先讲意义和价值', '树立目标鼓励前冲', '以小见大发现伟大价值']},
            '构思型': {'traits': ['思考驱动'], 'desc': '做事前需要想清楚，喜欢构想推理分析。善用心像，需要自我思考和消化空间。具有创造力潜质。',
                       'risks': ['被打断时效率下降', '可能过度思考'], 'supports': ['给思考空间', '避免思绪干扰', '强化动机帮其想到做到']},
            '均衡型': {'traits': ['方向与方法平衡'], 'desc': '各方面表现较均衡，做事情不偏激，既有人生方向又知道如何去实现。',
                       'risks': [], 'supports': ['保持目标清晰', '给稳定反馈']},
        }
        result['behavior'] = {'type': behavior_mode, **(mode_data.get(behavior_mode, {}))}

    # --- 三优一阻 ---
    result['top_three'] = top3
    result['bottom_one'] = lowest

    # --- 纹型矩阵 ---
    if patterns:
        for area_label, code in patterns.items():
            if code in PATTERN_MATRIX:
                area_info = PATTERN_MATRIX[code].get(area_label, '')
                if area_info:
                    result['pattern_insights'].append({
                        'area': area_label,
                        'code': code,
                        'insight': area_info,
                    })

    # --- 证据追踪 (供 prompt 引用 & validator 校验) ---
    evidence = {
        'trc_source': f"OCR提取: TRC={trc}" if trc is not None else None,
        'atd_source': f"OCR提取: ATD={atd}" if atd is not None else None,
        'channel_source': f"学习通道: {json.dumps(metrics.get('learning_channels', {}), ensure_ascii=False)}, 主通道={primary_channel}" if primary_channel else None,
        'behavior_mode_source': f"OCR关键词匹配: {behavior_mode}" if behavior_mode else None,
        'brain_balance_source': f"OCR提取: {metrics.get('brain_balance', '')}" if metrics.get('brain_balance') else None,
        'patterns_found': [f"{area}: {code}" for area, code in patterns.items()] if patterns else [],
        'function_scores_count': len(func) if func else 0,
        'metrics_missing': [],
    }
    if trc is None: evidence['metrics_missing'].append('TRC')
    if atd is None: evidence['metrics_missing'].append('ATD')
    if not primary_channel: evidence['metrics_missing'].append('learning_channels')
    if not behavior_mode: evidence['metrics_missing'].append('behavior_mode')
    if not patterns: evidence['metrics_missing'].append('function_patterns')
    # 以下为可选指标，缺失不阻塞报告
    optional_missing = []
    if not metrics.get('brain_balance'): optional_missing.append('brain_balance')
    if not metrics.get('personality_type'): optional_missing.append('personality_type')
    evidence['metrics_missing_optional'] = optional_missing

    # --- 组合规则 ---
    if trc is not None and atd is not None:
        if trc >= 180 and atd <= 36:
            result['combos'].append({'type': 'exploration_fast', 'label': '快速探索型',
                                      'desc': '兴趣广、反应快、新鲜感强。容易快进快出，需要沉淀。',
                                      'supports': ['阶段性聚焦', '输出式学习', '小目标闭环']})
        elif trc < 80 and atd >= 42:
            result['combos'].append({'type': 'focused_slow', 'label': '专注深耕型',
                                      'desc': '慢热、专注、适合长期训练。少而精，给足时间，不频繁切换。',
                                      'supports': ['少而精', '给足时间', '不频繁切换']})
        elif trc >= 180 and atd >= 42:
            result['combos'].append({'type': 'broad_deep', 'label': '广度深度兼备型',
                                      'desc': '容量大但沉稳，既能多元又能深入。',
                                      'supports': ['保持节奏', '不催促', '给足消化时间']})
    if primary_channel == 'auditory' and atd is not None and atd <= 36:
        result['combos'].append({'type': 'fast_auditory', 'label': '快速听觉学习者',
                                  'desc': '听得快、反应快、讨论中更容易打开。容易受语气影响。',
                                  'supports': ['多鼓励', '多复述', '避免高压批评语气']})

    return result


def rule_summary(structure):
    """将 structured dict 转为人类可读的摘要文本。"""
    lines = []
    t = structure.get('trc')
    if t:
        lines.append(f"TRC={t['value']} ({t['label']}): {t.get('capacity','')} | 风险:{'、'.join(t.get('risks',[]))} | 支持:{'、'.join(t.get('supports',[]))}")
    a = structure.get('atd')
    if a:
        lines.append(f"ATD={a['value']} ({a['label']}): {a.get('focus','')} | 风险:{'、'.join(a.get('risks',[]))} | 支持:{'、'.join(a.get('supports',[]))}")
    ch = structure.get('channel')
    if ch:
        lines.append(f"主学习通道: {ch['label']} ({ch.get('scores',{})})")
    b = structure.get('behavior')
    if b:
        lines.append(f"行为模式: {b['type']} — {b.get('desc','')}")
    if structure.get('top_three'):
        lines.append(f"三优: {', '.join(structure['top_three'])} | 一阻: {structure.get('bottom_one','')}")
    for c in structure.get('combos', []):
        lines.append(f"组合: {c['label']} — {c.get('desc','')}")
    for p in structure.get('pattern_insights', []):
        lines.append(f"纹型 {p['area']}({p['code']}): {p['insight']}")
    return '\n'.join(lines)
