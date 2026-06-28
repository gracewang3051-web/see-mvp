"""Layer 1.5: TF-IDF 知识检索 (保持现有逻辑)"""

import os, re

KB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'kb_innate_v2')


def _load(path):
    with open(os.path.join(KB_DIR, path), 'r') as f:
        return f.read()


# 惰性加载
_ONTOLOGY = _RULES_DOC = _INSIGHTS = _NARRATIVES = _INTERVENTIONS = _FRAMEWORKS = None


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
        'ontology': _ONTOLOGY, 'rules': _RULES_DOC, 'insights': _INSIGHTS,
        'narratives': _NARRATIVES, 'interventions': _INTERVENTIONS, 'frameworks': _FRAMEWORKS,
    }


def retrieve(structure, report_type='learning'):
    """根据规则输出检索相关知识片段。"""
    kb = _kb()
    insights_text = kb['insights']
    narr = kb['narratives']
    inter = kb['interventions']

    # --- 检索 insights ---
    selected_insights = []
    trc = structure.get('trc', {})
    atd = structure.get('atd', {})
    channel = structure.get('channel', {})
    behavior = structure.get('behavior', {})

    if trc and trc.get('level') in ('high', 'ultra_high'):
        selected_insights.append(_extract_section(insights_text, '快速探索|高TRC'))
    elif trc and trc.get('level') == 'low':
        selected_insights.append(_extract_section(insights_text, '慢热深耕|低TRC'))
    if atd and atd.get('level') == 'sensitive':
        selected_insights.append(_extract_section(insights_text, '快速|低ATD|听觉'))
    elif atd and atd.get('level') == 'result':
        selected_insights.append(_extract_section(insights_text, '慢热|高ATD'))
    if channel and channel.get('primary'):
        selected_insights.append(_extract_section(insights_text, '听觉主导|视觉预热|体觉'))
    if behavior and behavior.get('type'):
        selected_insights.append(_extract_section(insights_text, '动机|构思'))
    for combo in structure.get('combos', []):
        selected_insights.append(_extract_section(insights_text, combo.get('label', '')))

    selected_insights = _dedup(selected_insights)[:4]

    # --- 检索 narratives ---
    selected_narr = []
    if trc and trc.get('level') in ('high', 'ultra_high'):
        selected_narr.append(_extract_section(narr, '窗口|高TRC'))
    if atd and atd.get('level') == 'result':
        selected_narr.append(_extract_section(narr, '慢热|高ATD'))
    if channel and channel.get('primary'):
        selected_narr.append(_extract_section(narr, '频道|爱语'))
    if behavior and behavior.get('type'):
        selected_narr.append(_extract_section(narr, '动机型孩子'))
    selected_narr = _dedup(selected_narr)[:3]

    # --- 检索 interventions ---
    selected_inter = []
    for combo in structure.get('combos', []):
        if 'fast' in combo.get('type', ''):
            selected_inter.append(_extract_section(inter, '快速探索型学习者'))
        elif 'focused' in combo.get('type', ''):
            selected_inter.append(_extract_section(inter, '慢热深耕型学习者'))
    if channel and channel.get('primary') == 'visual':
        selected_inter.append(_extract_section(inter, '视觉预热|视觉主导'))
    elif channel and channel.get('primary') == 'auditory':
        selected_inter.append(_extract_section(inter, '听觉主导学习'))
    elif channel and channel.get('primary') == 'kinesthetic':
        selected_inter.append(_extract_section(inter, '体觉'))
    if behavior and behavior.get('type') == '动机型':
        selected_inter.append(_extract_section(inter, '动机型孩子目标'))
    selected_inter = _dedup(selected_inter)[:3]

    return {
        'insights': selected_insights,
        'narratives': selected_narr,
        'interventions': selected_inter,
        'frameworks': kb['frameworks'][:1200],
        'ontology': kb['ontology'][:800],
    }


def _extract_section(text, pattern):
    for part in text.split('\n---\n'):
        if re.search(pattern, part, re.IGNORECASE):
            return part.strip()
    blocks = re.split(r'\n(?=## )', text)
    for block in blocks:
        if re.search(pattern, block, re.IGNORECASE):
            return block.strip()[:800]
    return ''


def _dedup(items):
    seen, result = set(), []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result
