"""SEE Innate RAG V2 — 规则引擎 + 检索器

流程: OCR文本 → 指标提取 → 规则匹配 → 检索(Insight/Narrative/Intervention) → Prompt组装
"""

import json, re, os

KB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'kb_innate_v2')

def _load(path):
    with open(os.path.join(KB_DIR, path), 'r') as f:
        return f.read()


# ============================================================
# 1. 指标提取
# ============================================================

def extract_metrics(ocr_text):
    """从 OCR 文本中解析关键指标。返回 dict，缺失字段为 None。"""
    m = {}

    # TRC/ATD — 优先标签，找不到则找含 >=2 个大数字的行
    trc_m = re.search(r'TRC[：:\s]*(\d{2,4})', ocr_text, re.IGNORECASE)
    if trc_m:
        m['trc'] = int(trc_m.group(1))
    else:
        for line in ocr_text.split('\n'):
            # 跳过百分比行和功能区行（含 Lu/Ws/Wc 等）
            if '%' in line or re.search(r'\b(Lu|Ws|Wc|Wsc|Wl|We|Wi|Wpe|Wd|Xn|R)\b', line):
                continue
            nums = re.findall(r'\b(\d{2,4})\b', line)
            # TRC 通常 150±50 (三位数)，ATD 通常 25-45 (两位数)
            if len(nums) >= 2 and int(nums[0]) >= 80:
                m['trc'] = int(nums[0])
                m['atd'] = int(nums[1])
                break

    # ATD — 如果上面没设，再单独找
    if m.get('atd') is None:
        atd_m = re.search(r'ATD[：:\s]*(\d{1,3})', ocr_text, re.IGNORECASE)
        if not atd_m:
            atd_m = re.search(r'反应[灵敏度速度].*?(\d{1,3})', ocr_text)
        if atd_m:
            m['atd'] = int(atd_m.group(1))

    # 行为模式（支持无空格格式 动机型 和 有空格格式 动机 型）
    for kw in ['动机型', '动机 型', '构思型', '构思 型', '均衡型', '均衡 型']:
        if kw.replace(' ', '') in ocr_text.replace(' ', ''):
            m['behavior_mode'] = kw.replace(' ', '')
            break

    # 脑平衡
    for kw in ['均衡型', '均衡 型', '左脑型', '右脑型']:
        clean = kw.replace(' ', '')
        if clean in ocr_text.replace(' ', ''):
            m['brain_balance'] = clean
            break

    # 纹型/人格类型
    pm = re.search(r'(?:纹型|人格类型|personality)[：:\s]*(\w+)', ocr_text)
    if pm:
        m['personality_type'] = pm.group(1)

    # 学习通道百分比
    ch = {}
    # 优先：找一行有三个百分比的（常见格式：38.89% 32.41% 28.70%）
    pct_line = re.search(r'(\d+\.?\d*)%\s+(\d+\.?\d*)%\s+(\d+\.?\d*)%', ocr_text)
    if pct_line:
        vals = [float(pct_line.group(i)) for i in (1,2,3)]
        # 假设顺序：听觉、视觉、体觉（SEE 标准格式）
        ch = {'auditory': vals[0], 'visual': vals[1], 'kinesthetic': vals[2]}
    else:
        # 备用：带标签匹配（如 听觉:38%）
        for label, key in [('听觉', 'auditory'), ('视觉', 'visual'), ('体觉', 'kinesthetic')]:
            pct = re.search(rf'{label}(?!左|右)[^0-9]*?(\d+\.?\d+)\s*%', ocr_text)
            if pct:
                ch[key] = float(pct.group(1))
    if ch:
        m['learning_channels'] = ch
        m['primary_channel'] = max(ch, key=ch.get)

    # 功能区分数 (10项: 精神左右、思维左右、体觉左右、听觉左右、视觉左右)
    area_map = [
        ('精神左', 'spirit_left'), ('精神右', 'spirit_right'),
        ('思维左', 'thinking_left'), ('思维右', 'thinking_right'),
        ('体觉左', 'kinesthetic_left'), ('体觉右', 'kinesthetic_right'),
        ('听觉左', 'auditory_left'), ('听觉右', 'auditory_right'),
        ('视觉左', 'visual_left'), ('视觉右', 'visual_right'),
    ]
    func = {}
    for cn, en in area_map:
        s = re.search(rf'{cn}[^0-9]*?(\d+)', ocr_text)
        if s:
            func[en] = int(s.group(1))
    if func:
        m['function_scores'] = func
        sorted_areas = sorted(func, key=func.get, reverse=True)
        m['top_three_areas'] = sorted_areas[:3]
        m['lowest_area'] = sorted_areas[-1]

    # 左侧/右侧差值
    if func:
        left_keys = [k for k in func if 'left' in k]
        right_keys = [k for k in func if 'right' in k]
        if left_keys and right_keys:
            left_avg = sum(func[k] for k in left_keys) / len(left_keys)
            right_avg = sum(func[k] for k in right_keys) / len(right_keys)
            m['left_right_diff'] = left_avg - right_avg

    return m


# ============================================================
# 2. 规则引擎
# ============================================================

def apply_rules(metrics):
    """根据指标匹配规则，返回 {label, traits, behaviors, risks, supports} 列表。"""
    rules = []
    trc = metrics.get('trc')
    atd = metrics.get('atd')
    behavior_mode = metrics.get('behavior_mode')
    primary_channel = metrics.get('primary_channel', '')
    func = metrics.get('function_scores', {})
    top3 = metrics.get('top_three_areas', [])
    lowest = metrics.get('lowest_area')

    # TRC 规则
    if trc is not None:
        if trc > 160:
            rules.append({
                'id': 'RULE_TRC_HIGH', 'label': '高TRC', 'category': 'trc_high',
                'traits': ['多元', '发散', '多线程'],
                'behaviors': ['兴趣广', '想法多', '容易同时关注多个方向'],
                'risks': ['容易分散', '不喜欢重复', '需要收束'],
                'supports': ['建立优先级', '用阶段性目标聚焦', '用项目制承载多元兴趣']
            })
        elif trc < 100:
            rules.append({
                'id': 'RULE_TRC_LOW', 'label': '低TRC', 'category': 'trc_low',
                'traits': ['聚焦', '深耕', '单线程'],
                'behaviors': ['更适合长期专注一件事', '不喜欢频繁切换任务'],
                'risks': [],
                'supports': ['一次只给一个目标', '减少同时安排多个兴趣或任务']
            })
        else:
            rules.append({
                'id': 'RULE_TRC_MIDDLE', 'label': '中TRC', 'category': 'trc_middle',
                'traits': ['均衡', '适应'],
                'behaviors': ['可兼顾广度与深度'],
                'risks': [],
                'supports': ['根据阶段目标灵活安排']
            })

    # ATD 规则
    if atd is not None:
        if atd <= 36:
            rules.append({
                'id': 'RULE_ATD_LOW', 'label': '低ATD(快速响应)', 'category': 'atd_low',
                'traits': ['反应快', '敏感', '启动快'],
                'behaviors': ['一点就通', '对环境刺激敏锐', '容易快速判断'],
                'risks': ['快而粗', '情绪或语气容易影响状态'],
                'supports': ['训练复述', '加入检查', '在冲动前暂停']
            })
        elif atd >= 42:
            rules.append({
                'id': 'RULE_ATD_HIGH', 'label': '高ATD(慢热)', 'category': 'atd_high',
                'traits': ['沉稳', '慢热', '深度消化'],
                'behaviors': ['新任务启动慢', '熟悉后后劲足'],
                'risks': ['被催促会压力大', '容易被误解为慢或不上心'],
                'supports': ['提前预告', '分解任务', '给足预热和消化时间']
            })
        else:
            rules.append({
                'id': 'RULE_ATD_MIDDLE', 'label': '中ATD(均衡)', 'category': 'atd_middle',
                'traits': ['均衡', '稳定适应'],
                'behaviors': [],
                'risks': [],
                'supports': ['适合常规教学与工作节奏']
            })

    # 学习通道规则
    if primary_channel:
        rules.append({
            'id': f'RULE_CHANNEL_{primary_channel.upper()}',
            'label': f'{primary_channel}主导型学习通道',
            'category': f'channel_{primary_channel}',
            'traits': [primary_channel],
            'behaviors': [],
            'risks': [],
            'supports': []
        })

    # 行为模式规则
    if behavior_mode:
        mode_labels = {
            '动机型': {'traits': ['动机驱动'], 'behaviors': ['需要知道为什么做', '目标感强时行动快'], 'risks': ['不喜欢被直接命令'], 'supports': ['先讲意义', '给愿景', '用目标驱动行动']},
            '构思型': {'traits': ['思考驱动'], 'behaviors': ['做事前需要想清楚', '喜欢构想推理分析'], 'risks': ['被打断时效率下降'], 'supports': ['给思考空间', '帮助分解目标']},
            '均衡型': {'traits': ['方向与方法平衡'], 'behaviors': ['不偏激'], 'risks': [], 'supports': ['保持目标清晰', '给稳定反馈']},
        }
        d = mode_labels.get(behavior_mode, {})
        rules.append({
            'id': f'RULE_BEHAVIOR_{behavior_mode}',
            'label': f'{behavior_mode}',
            'category': f'behavior_{behavior_mode}',
            'traits': d.get('traits', []),
            'behaviors': d.get('behaviors', []),
            'risks': d.get('risks', []),
            'supports': d.get('supports', [])
        })

    # 三优一阻
    if top3 and lowest:
        rules.append({
            'id': 'RULE_3_STRENGTHS_1_BLOCK',
            'label': '三优一阻',
            'category': 'strengths_block',
            'strengths': top3,
            'blocker': lowest,
            'traits': [],
            'behaviors': [],
            'risks': [],
            'supports': []
        })

    # 功能区规则
    area_labels = {
        'spirit_right': {'label': '精神右脑优势', 'traits': ['个人目标', '愿景', '自我实现'], 'behaviors': ['需要意义感', '被愿景点燃后动力强']},
        'spirit_left': {'label': '精神左脑优势', 'traits': ['责任', '规则', '计划', '集体目标'], 'behaviors': ['关注结构和执行']},
        'thinking_right': {'label': '思维右脑优势', 'traits': ['构思', '创意', '想象', '未来画面'], 'behaviors': ['喜欢开放性任务']},
        'thinking_left': {'label': '思维左脑优势', 'traits': ['逻辑', '分析', '因果', '结构'], 'behaviors': ['喜欢结构和推理任务']},
    }
    for area, info in area_labels.items():
        if area in top3:
            rules.append({
                'id': f'RULE_{area.upper()}_HIGH',
                'label': info['label'],
                'category': f'area_{area}',
                'traits': info['traits'],
                'behaviors': info['behaviors'],
                'risks': [],
                'supports': []
            })

    # 组合规则
    if trc is not None and atd is not None:
        if trc > 160 and atd <= 36:
            rules.append({
                'id': 'COMBO_HIGH_TRC_LOW_ATD', 'label': '快速探索型',
                'category': 'combo',
                'traits': ['快速探索'],
                'behaviors': ['兴趣广', '反应快', '新鲜感强'],
                'risks': ['容易快进快出', '需要沉淀'],
                'supports': ['阶段性聚焦', '输出式学习', '小目标闭环']
            })
        elif trc < 100 and atd >= 42:
            rules.append({
                'id': 'COMBO_LOW_TRC_HIGH_ATD', 'label': '专注深耕型',
                'category': 'combo',
                'traits': ['专注深耕'],
                'behaviors': ['慢热', '专注', '适合长期训练'],
                'risks': [],
                'supports': ['少而精', '给足时间', '不频繁切换']
            })

    if primary_channel == 'auditory' and atd is not None and atd <= 36:
        rules.append({
            'id': 'COMBO_AUDITORY_HIGH_ATD_LOW', 'label': '快速听觉学习者',
            'category': 'combo',
            'traits': ['快速听觉学习'],
            'behaviors': ['听得快', '反应快', '讨论中更容易打开'],
            'risks': ['容易受语气影响'],
            'supports': ['多鼓励', '多复述', '避免高压批评语气']
        })

    return rules


# ============================================================
# 3. 检索
# ============================================================

# 知识文件作为静态资源加载
_ONTOLOGY = None
_RULES_DOC = None
_INSIGHTS = None
_NARRATIVES = None
_INTERVENTIONS = None
_FRAMEWORKS = None

def _kb():
    global _ONTOLOGY, _RULES_DOC, _INSIGHTS, _NARRATIVES, _INTERVENTIONS, _FRAMEWORKS
    if _ONTOLOGY is None:
        _ONTOLOGY = _load('ontology.md')
        _RULES_DOC = _load('rules.md')
        _INSIGHTS = _load('insights.md')
        _NARRATIVES = _load('narratives.md')
        _INTERVENTIONS = _load('interventions.md')
        _FRAMEWORKS = _load('report_frameworks.md')
    return {
        'ontology': _ONTOLOGY,
        'rules': _RULES_DOC,
        'insights': _INSIGHTS,
        'narratives': _NARRATIVES,
        'interventions': _INTERVENTIONS,
        'frameworks': _FRAMEWORKS,
    }


def retrieve_insights(rule_outputs, report_type='learning'):
    """基于匹配规则检索相关 Insight 片段。"""
    kb = _kb()
    insights_text = kb['insights']

    # 从 insight 文档中提取匹配的段落
    sections = []
    section_map = {
        'learning': r'(?:^#{1,3}\s.*?学习|INSIGHT_LEARNING)',
        'family': r'(?:^#{1,3}\s.*?家庭|INSIGHT_FAMILY)',
        'career': r'(?:^#{1,3}\s.*?职业|INSIGHT_CAREER)',
        'relationship': r'(?:^#{1,3}\s.*?关系|INSIGHT_RELATIONSHIP)',
        'enterprise': r'(?:^#{1,3}\s.*?企业|INSIGHT_ENTERPRISE)',
    }

    # 提取相关场景的 insight 片段
    for rule in rule_outputs:
        cat = rule.get('category', '')
        if 'trc_high' in cat:
            sections.append(_extract_section(insights_text, '快速探索|高TRC'))
        elif 'trc_low' in cat:
            sections.append(_extract_section(insights_text, '慢热深耕|低TRC'))
        if 'atd_low' in cat:
            sections.append(_extract_section(insights_text, '快速|低ATD|听觉'))
        if 'atd_high' in cat:
            sections.append(_extract_section(insights_text, '慢热|高ATD'))
        if 'channel' in cat:
            sections.append(_extract_section(insights_text, '听觉主导|视觉预热|体觉'))
        if 'behavior' in cat:
            sections.append(_extract_section(insights_text, '动机|构思'))
        if 'combo' in cat:
            sections.append(_extract_section(insights_text, rule.get('label', '')))

    # 过滤空值去重，保留前 5 条最相关
    seen = set()
    result = []
    for s in sections:
        if s and s not in seen:
            seen.add(s)
            result.append(s)
    return result[:5]


def select_narratives(rule_outputs, report_type='learning'):
    """基于规则输出选择顾问语言模板。"""
    kb = _kb()
    narr = kb['narratives']

    selected = []
    for rule in rule_outputs:
        cat = rule.get('category', '')
        if 'trc_high' in cat:
            selected.append(_extract_section(narr, '窗口|高TRC'))
        if 'atd_high' in cat:
            selected.append(_extract_section(narr, '慢热|高ATD'))
        if 'channel' in cat:
            selected.append(_extract_section(narr, '频道|爱语'))
        if 'behavior' in cat:
            selected.append(_extract_section(narr, '动机型孩子'))
        if 'area' in cat:
            selected.append(_extract_section(narr, '逆思|频道'))
        if 'strengths_block' in cat:
            selected.append(_extract_section(narr, '频道|听不懂'))

    seen = set()
    result = []
    for s in selected:
        if s and s not in seen:
            seen.add(s)
            result.append(s)
    return result[:4]


def select_interventions(rule_outputs, report_type='learning'):
    """基于规则输出选择支持方案。"""
    kb = _kb()
    inter = kb['interventions']

    selected = []
    for rule in rule_outputs:
        cat = rule.get('category', '')
        if 'trc_high' and 'atd_low' in cat or 'combo' in cat and 'HIGH_TRC_LOW_ATD' in rule.get('id', ''):
            selected.append(_extract_section(inter, '快速探索型学习者'))
        elif 'trc_low' in cat and 'atd_high' in cat or 'combo' in cat and 'LOW_TRC_HIGH_ATD' in rule.get('id', ''):
            selected.append(_extract_section(inter, '慢热深耕型学习者'))
        if 'atd_low' in cat:
            selected.append(_extract_section(inter, '高敏感听觉'))
        if 'channel_visual' in cat:
            selected.append(_extract_section(inter, '视觉预热|视觉主导'))
        elif 'channel_auditory' in cat:
            selected.append(_extract_section(inter, '听觉主导学习'))
        elif 'channel_kinesthetic' in cat:
            selected.append(_extract_section(inter, '体觉'))
        if 'behavior_motivation' in cat or '动机' in rule.get('label', ''):
            selected.append(_extract_section(inter, '动机型孩子目标'))
        if 'area' in cat:
            selected.append(_extract_section(inter, '创意多面手|责任运营'))
        if 'strengths_block' in cat:
            selected.append(_extract_section(inter, '家庭频道'))

    seen = set()
    result = []
    for s in selected:
        if s and s not in seen:
            seen.add(s)
            result.append(s)
    return result[:4]


def _extract_section(text, pattern):
    """从知识文本中模糊检索匹配片段。"""
    parts = text.split('\n---\n')
    for part in parts:
        if re.search(pattern, part, re.IGNORECASE):
            return part.strip()
    # fallback: 按 ## 标题检索
    blocks = re.split(r'\n(?=## )', text)
    for block in blocks:
        if re.search(pattern, block, re.IGNORECASE):
            return block.strip()[:800]
    return ''


# ============================================================
# 4. Prompt 组装
# ============================================================

REPORT_TYPES = {
    'portrait': {
        'name': '先天思维特质报告',
        'template': '通用报告结构',
    },
    'learning': {
        'name': '学习方式分析报告',
        'template': '学习方式报告',
    },
    'emotion': {
        'name': '情绪模式洞察报告',
        'template': '通用报告结构',
    },
    'potential': {
        'name': '潜能发展方向报告',
        'template': '生命成长报告',
    },
}


def build_prompt(context, report_type='learning'):
    """
    组装结构化 prompt。

    context = {
        'ocr_text': '...',       # OCR 原始文本
        'metrics': {...},         # 解析后的指标
        'rule_outputs': [...],    # 匹配的规则
        'insights': [...],        # 检索到的 insight
        'narratives': [...],      # 检索到的 narrative
        'interventions': [...],   # 检索到的 intervention
    }
    """
    kb = _kb()
    rt = REPORT_TYPES.get(report_type, REPORT_TYPES['portrait'])
    metrics = context.get('metrics', {})
    rule_outputs = context.get('rule_outputs', [])
    insights = context.get('insights', [])
    narratives = context.get('narratives', [])
    interventions = context.get('interventions', [])

    # 知识上下文（精简版，不塞全文）
    kb_context = []

    if insights:
        kb_context.append("## 匹配的洞察\n" + "\n\n".join(f"### 洞察 {i+1}\n{s}" for i, s in enumerate(insights[:3])))

    if narratives:
        kb_context.append("## 顾问表达参考\n" + "\n\n".join(f"### 表达 {i+1}\n{s}" for i, s in enumerate(narratives[:2])))

    if interventions:
        kb_context.append("## 支持方案库\n" + "\n\n".join(f"### 方案 {i+1}\n{s}" for i, s in enumerate(interventions[:2])))

    # 规则按区域分组
    zones = {}
    for r in rule_outputs:
        cat = r.get('category', '')
        if cat in ('trc_high', 'trc_middle', 'trc_low', 'atd_low', 'atd_middle', 'atd_high'):
            zone = '⚡ 能量引擎'
        elif cat.startswith('channel_'):
            zone = '👂 学习通道'
        elif cat.startswith('behavior_'):
            zone = '🧠 行为模式'
        elif cat.startswith('area_') or cat == 'strengths_block':
            zone = '🗺️ 功能区地图'
        else:
            zone = '🔗 综合判断'
        zones.setdefault(zone, []).append(r)

    nl = '\n'
    zone_blocks = []
    zone_labels = {
        '⚡ 能量引擎': f"""**原始数据** → TRC:{metrics.get('trc','?')} ATD:{metrics.get('atd','?')}
**规则** → TRC>160为高(多元发散) <100为低(专注深耕) | ATD≤36为快(敏锐) ≥42为慢(沉稳)
**判定** → """,
        '👂 学习通道': f"""**原始数据** → {json.dumps(metrics.get('learning_channels',{}), ensure_ascii=False)}
**规则** → 取百分比最高通道为优势通道
**判定** → """,
        '🧠 行为模式': f"""**原始数据** → {metrics.get('behavior_mode','?')}
**规则** → 动机型=先有意义再行动 | 构思型=先想清楚再行动 | 均衡型=方向与方法平衡
**判定** → """,
        '🗺️ 功能区地图': f"""**原始数据** → {json.dumps(metrics.get('function_scores',{}), ensure_ascii=False)}
**规则** → 取前三为优势区，最后一为成长提醒区
**判定** → """,
        '🔗 综合判断': '**多区域交叉判断** → ',
    }
    for zone_label, rules in zones.items():
        header = zone_labels.get(zone_label, '')
        items = []
        for r in rules:
            parts = [f"**{r.get('label','')}**"]
            if r.get('traits'): parts.append('特质: ' + '、'.join(r['traits']))
            if r.get('risks'): parts.append('风险: ' + '、'.join(r['risks']))
            if r.get('supports'): parts.append('支持: ' + '、'.join(r['supports']))
            if r.get('strengths'):
                parts.append(f"三优: {', '.join(r['strengths'])} | 一阻: {r['blocker']}")
            items.append(' | '.join(parts))
        zone_blocks.append(header + nl.join(items))

    kb_header = ('## 匹配的知识库' + nl + nl.join(kb_context)) if kb_context else ''

    system_prompt = f"""你是 SEE 先天优势解码报告生成助手。你必须严格基于下方的规则引擎输出来生成报告。

## 指标含义（理解数据的基础）
{kb['ontology'][:1500]}

## ⚠️ 强制规则（违反即为错误）
1. 报告中提到的学习通道、行为模式、功能区优劣，必须与「分区判定」一致，不得使用未提及的标签
2. 开头先做行为解码，不要先堆指标
3. 每个结论必须对应分区判定中的数据依据
4. 不使用"好/坏、聪明/不聪明、一定、注定"等表达
5. 低分区写成"成长提醒"或"支持需求"，不能写成缺陷
6. 每个风险点必须匹配至少一个支持方案，从下方匹配的支持方案中选取
7. 用顾问语言：温和、解释性强、避免贴标签

{kb_header}

## 报告模板
{kb['frameworks'][:800]}
"""

    user_prompt = f"""## 用户测评数据（仅供参考，以分区判定为准）
{context.get('ocr_text', '')[:2000]}

## 分区判定（权威分析，报告必须基于此）

{nl.join(zone_blocks)}

## 任务
生成一份 **{rt['name']}**（Markdown格式，800-1200字），严格遵循分区判定。

结构：
1. 行为解码（先讲行为表现，不堆指标）
2. 先天特质地图（只使用分区判定中的标签）
3. 优势发挥分析
4. 成长提醒（不写缺陷）
5. 支持方案（可执行建议，从下方匹配方案中选取）
6. 行动清单（3-5条短期可执行动作）
"""

    return system_prompt, user_prompt


def process(ocr_text, report_type='learning', structured_data=None):
    """一站式处理：OCR 文本 → 结构化 prompt。返回给 server.py 调用。

    返回: {
        'system_prompt': str,
        'user_prompt': str,
        'debug': { 'metrics': ..., 'rule_outputs': [...], 'insights': ..., 'narratives': ..., 'interventions': ... }
    }
    """
    # 支持两种输入
    if structured_data:
        metrics = structured_data
    else:
        metrics = extract_metrics(ocr_text)

    rule_outputs = apply_rules(metrics)
    insights = retrieve_insights(rule_outputs, report_type)
    narratives = select_narratives(rule_outputs, report_type)
    interventions = select_interventions(rule_outputs, report_type)

    context = {
        'ocr_text': ocr_text,
        'metrics': metrics,
        'rule_outputs': rule_outputs,
        'insights': insights,
        'narratives': narratives,
        'interventions': interventions,
    }
    system_prompt, user_prompt = build_prompt(context, report_type)

    return {
        'system_prompt': system_prompt,
        'user_prompt': user_prompt,
        'debug': {
            'metrics': metrics,
            'rule_outputs': rule_outputs,
            'insights_count': len(insights),
            'narratives_count': len(narratives),
            'interventions_count': len(interventions),
        }
    }
