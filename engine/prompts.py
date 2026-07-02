"""Layer 3: 表达层 — 多种咨询师风格 Prompt 注册表"""

# ============================================================
# 咨询师风格
# ============================================================
STYLES = {
    "gentle": """你是一位温和细腻的教育顾问。

【语言特点】
- 多用「我注意到...」「很有意思的特点是...」「可能你会发现...」
- 每个判断前加缓冲语，像朋友聊天，不学术不冷硬
- 用生活场景举例，让读者觉得「对，就是这样」
- 先说理解，再说建议

【禁止】
- 直接下判断（❌「这是弱点」→ ✅「这个部分目前相对不常用」）
- 使用「智商」「一定」「注定」「不聪明」""",

    "direct": """你是一位经验丰富的生涯规划师。

【语言特点】
- 直接给出核心结论，语言简洁有力
- 用结构化列表，少用修饰词
- 每个建议都可执行、可衡量
- 像一份专业咨询报告，干净利落

【禁止】
- 啰嗦铺垫
- 模棱两可的表达""",

    "parent": """你是一位懂妈妈心的亲子教育顾问。

【语言特点】
- 用妈妈能听懂的日常语言
- 多举具体例子（「比如写作业的时候...」「比如你催他快一点的时候...」）
- 先说「你看到的不是问题，是特点」
- 暖色调，有共鸣感，让家长觉得「终于有人懂我的孩子了」
- 用「宝贝」「孩子」等亲切称呼

【禁止】
- 冰冷的专业术语
- 让家长感觉自己做错了""",

    "educator": """你是一位严谨的教育分析师。

【语言特点】
- 引用发展心理学和认知科学框架
- 用「从认知发展的视角来看...」「在多元智能理论框架下...」
- 给学校环境和家庭环境的分开建议
- 结构清晰，有理有据

【禁止】
- 未经理论支撑的个人意见
- 模糊笼统的建议""",

    "coach": """你是一位充满能量的成长教练。

【语言特点】
- 语调积极、有力量感
- 多用「你的天赋在于...」「你的超能力是...」
- 把挑战转化为成长机会
- 像一位激发潜能的导师，让人读完充满动力
- 用感叹号和短句制造节奏感

【禁止】
- 消极表述
- 让人泄气的评价""",
}

# ============================================================
# 报告类型映射
# ============================================================
REPORT_TYPES = {
    'portrait':    '个人成长解读',
    'portrait-see-ai': '个人成长解读',
    'personal':    '个人成长解读',
    'child':       '孩子学习力解读',
    'family':      '家庭合盘解读',
    'team':        '团队合盘解读',
    'learning':    '学习方式分析报告',
    'emotion':     '情绪模式洞察报告',
    'potential':   '潜能发展方向报告',
    'communication': '关系洞察报告',
    'career':      '职业规划报告',
    'action':      '个人成长建议报告',
}

PORTRAIT_TYPES = {'portrait', 'portrait-see-ai', 'personal', 'child', 'family', 'team'}


def build_prompt(structure, meaning, knowledge, report_type='learning', style='gentle', age=None, target='self', preprocessing=None):
    """组装最终 prompt。

    Args:
        structure: rules.apply_rules() 的输出
        meaning: interpreter.interpret() 的输出
        knowledge: retrieval.retrieve() 的输出
        report_type: 报告类型
        style: 咨询师风格 (gentle/direct/parent/educator/coach)
        age: 年龄(可选)
    """
    style_instruction = STYLES.get(style, STYLES['gentle'])
    style_label = style_instruction.split('\n')[0].replace('你是一位', '').strip()
    rt_name = REPORT_TYPES.get(report_type, '报告')
    if preprocessing is None:
        preprocessing = {}

    # 新规预处理数据序列化
    import json
    prep_data = ''
    if preprocessing:
        prep_parts = []
        pf = preprocessing.get('pattern_family', {})
        if pf and pf.get('main'):
            prep_parts.append(f"主性格: {pf['main']['label']}（{pf['main']['code']}）")
            if pf.get('auxiliary'):
                prep_parts.append(f"辅助性格: {pf['auxiliary']['label']}")
            if pf.get('full_brain'):
                prep_parts.append(f"全脑性格: {pf['full_brain']}")
        fa = preprocessing.get('function_areas', {})
        if fa and fa.get('ranked'):
            rank_str = ' > '.join(f"{a['name']}({a['total']}分)" for a in fa['ranked'])
            prep_parts.append(f"功能区排序: {rank_str}")
            if fa.get('advantage'):
                prep_parts.append(f"优势区: {fa['advantage']['name']}")
            if fa.get('warning'):
                prep_parts.append(f"警示区: {fa['warning']['name']}")
        lc = preprocessing.get('learning_channels', {})
        if lc and lc.get('ranked'):
            ch_str = ' > '.join(f"{c['name']}({c['score']})" for c in lc['ranked'])
            prep_parts.append(f"学习通道排序: {ch_str}")
        lat = preprocessing.get('lateralization', [])
        if lat:
            lat_str = '; '.join(f"{l['name']}: {l['label']}(左{l['left']}/右{l['right']})" for l in lat)
            prep_parts.append(f"偏侧化: {lat_str}")
        prep_data = '\n'.join(prep_parts)

    # 年龄影响: 自动调整报告类型和语言
    age_context = ''
    if age is not None:
        if age < 12:
            age_context = f'\n\n## 年龄信息\n报告对象年龄: {age} 岁（儿童）。请用家长能理解的温和语言，侧重学习方式和亲子关系，报告名为「儿童学习方式分析报告」。'
            if report_type == 'portrait':
                rt_name = f'{age}岁儿童先天特质报告'
        elif age < 18:
            age_context = f'\n\n## 年龄信息\n报告对象年龄: {age} 岁（青少年）。请兼顾孩子本人和家长，既给孩子能看懂的建议，也给家长参考。侧重学习方法与潜能发展。'
        elif age < 25:
            age_context = f'\n\n## 年龄信息\n报告对象年龄: {age} 岁（青年）。语言风格可直接面向本人，侧重学业/职业规划与自我认知。'
        else:
            age_context = f'\n\n## 年龄信息\n报告对象年龄: {age} 岁（成人）。语言风格面向本人，侧重职业发展、关系经营与自我成长。'

    # 报告对象叠加
    target_prompts = {
        'self':   '## 报告对象\n这是一份给本人的报告。用「你」称呼读者，语气亲切直接，像和本人面对面交谈。建议要具体可执行。',
        'parent': '## 报告对象\n这是一份给家长的解读报告。用「您的孩子」称呼报告对象。语气温和有共鸣，先共情再给建议。不要指责家长，不要说「你做得不对」。多用生活化例子（比如写作业时、上学路上）。',
        'other':  '## 报告对象\n这是一份代他人解读的报告（如老师为学生、顾问为客户）。语气中立客观，用第三人称「这位...」描述。侧重于专业分析和可操作建议，避免过度情感化的表达。明确标注这是「基于第三方视角的解读」。',
        'global': '## 报告对象\n这是一份面向所有相关人员的综合报告。报告需要同时让本人、家人、老师/同事都能看懂和受益。结构清晰，分不同章节给不同读者：给本人的建议、给家人的建议、给老师/管理者的建议。语言兼顾温暖和理性。',
    }
    target_context = '\n\n' + target_prompts.get(target, target_prompts['self'])

    # 构建分区域判定
    zone_sections = _build_zone_sections(structure)

    # 构建知识片段
    kb_sections = []
    if knowledge.get('insights'):
        kb_sections.append('## 参考洞察\n' + '\n\n'.join(
            f'### {i+1}\n{s}' for i, s in enumerate(knowledge['insights'][:3])))
    if knowledge.get('narratives'):
        kb_sections.append('## 顾问表达参考\n' + '\n\n'.join(
            f'### {i+1}\n{s}' for i, s in enumerate(knowledge['narratives'][:2])))
    if knowledge.get('interventions'):
        kb_sections.append('## 支持方案库\n' + '\n\n'.join(
            f'### {i+1}\n{s}' for i, s in enumerate(knowledge['interventions'][:2])))

    system_prompt = f"""{style_instruction}

## 指标体系（理解数据的基础）
{knowledge.get('ontology', '')[:600]}

## ⚠️ 强制规则
1. 报告中提到的学习通道、行为模式、功能区优劣必须与分区判定一致
2. 开头先做行为解码，不要先堆指标
3. 低分区写成「成长提醒」或「支持需求」，不能写成缺陷
4. 每个风险点必须匹配支持方案
5. 用顾问语言：温和、解释性强、避免贴标签
6. 缺失的指标必须显式说明「当前资料不足以判断」，禁止编造
7. 报告中的纹型编码最多出现 1-2 次，其余全部用行为描述替代

{(chr(10).join(['## 匹配的知识库'] + kb_sections)) if kb_sections else ''}

## 报告模板
{knowledge.get('frameworks', '')[:400]}
"""

    # 构建证据区域
    evidence = structure.get('evidence', {})
    evidence_section = _build_evidence_section(evidence)

    is_portrait = report_type in PORTRAIT_TYPES

    if is_portrait:
        # 四份新报告模板选择
        template_map = {
            'portrait': 'personal', 'portrait-see-ai': 'personal',
            'personal': 'personal', 'child': 'child', 'family': 'family', 'team': 'team'
        }
        tmpl = template_map.get(report_type, 'personal')
        report_sections = _build_new_report_sections(tmpl, prep_data, structure, meaning, knowledge, style_label, rt_name, age_context, target_context)
        user_prompt = report_sections
    else:
        user_prompt = f"""## 用户测评数据
{meaning.get('raw_input', '')[:2000]}{age_context}{target_context}

## 结构分析
{zone_sections}

{_build_evidence_section(evidence) if evidence_section else ''}

## 行为解释
{meaning.get('behavior_decode', '')}

## 任务
你是一位{style_label}。请生成一份 **{rt_name}**（Markdown格式，800-1200字）。

结构：
1. 行为解码（先讲行为表现，不堆指标）
2. 先天特质地图（用纹型解读中的行为描述来解释特质，如「在决策时容易多个选项间权衡」而非「WC型」。全文最多出现 1-2 次纹型编码（如 Wc、Lu），其余全部用行为描述替代。纹型编码仅在解释「这个行为模式从纹型角度怎么理解」时使用一次）
3. 优势发挥分析
4. 成长提醒（不写缺陷）
5. 支持方案（可执行建议）

## ⚠️ 严禁事项
- ❌ 编造未被提取的数据（纹型、数值、年龄、家庭背景等）
- ❌ 用纹型编码给读者贴标签
- ❌ 使用「智商」「注定」「绝对是」「一定是」等绝对化断言
- ❌ 低分区写成「缺陷」或「弱点」
- ❌ 跳过推理直接给结论
"""
    return system_prompt, user_prompt


def _build_zone_sections(structure):
    """构建分区判定区域。"""
    from engine.rules import rule_summary
    summary = rule_summary(structure)

    # 纹型洞察
    pattern_lines = []
    for p in structure.get('pattern_insights', []):
        pattern_lines.append(f"- {p['area']}({p['code']}): {p['insight']}")

    sections = []
    sections.append(f"## 结构数据\n{summary}")
    if pattern_lines:
        sections.append(f"## 纹型解读\n" + '\n'.join(pattern_lines))
    return '\n\n'.join(sections)


def _build_evidence_section(evidence):
    """构建数据证据追踪区域，供 prompt 和 validator 使用。"""
    if not evidence:
        return ''
    lines = []
    lines.append('## 数据证据追踪')
    if evidence.get('trc_source'):
        lines.append(f"- {evidence['trc_source']}")
    if evidence.get('atd_source'):
        lines.append(f"- {evidence['atd_source']}")
    if evidence.get('channel_source'):
        lines.append(f"- {evidence['channel_source']}")
    if evidence.get('behavior_mode_source'):
        lines.append(f"- {evidence['behavior_mode_source']}")
    if evidence.get('brain_balance_source'):
        lines.append(f"- {evidence['brain_balance_source']}")
    if evidence.get('patterns_found'):
        lines.append(f"- 纹型编码匹配: {', '.join(evidence['patterns_found'])}")
    if evidence.get('function_scores_count'):
        lines.append(f"- 功能区得分: {evidence['function_scores_count']} 项")
    missing = evidence.get('metrics_missing', [])
    if missing:
        lines.append(f"- ⚠️ 核心指标缺失: {', '.join(missing)}（报告中应标注「当前资料不足以判断」）")
    optional_missing = evidence.get('metrics_missing_optional', [])
    if optional_missing:
        lines.append(f"- 可选指标缺失: {', '.join(optional_missing)}（若有可补充）")
    return '\n'.join(lines)


def _build_new_report_sections(tmpl, prep_data, structure, meaning, knowledge, style_label, rt_name, age_context, target_context):
    """构建四份新报告的 prompt 段落 (see_report_spec.md)"""
    import json

    metrics = structure.get('evidence', {})
    trc = structure.get('trc', {})
    atd = structure.get('atd', {})

    trc_val = trc.get('value', '未知') if trc else '未知'
    atd_val = atd.get('value', '未知') if atd else '未知'
    trc_label = trc.get('label', '') if trc else ''
    atd_label = atd.get('label', '') if atd else ''

    common = f"""## 预处理数据
{prep_data}

TRC={trc_val}（{trc_label}） ATD={atd_val}（{atd_label}）

## 任务
你是一位{style_label}。请生成一份 **{rt_name}**（Markdown格式，800-1500字）。
{age_context}{target_context}

## ⚠️ 强制规则
- 所有结论基于预处理数据，不编造
- 纹型编码仅在最必要时出现1-2次
- 低分区写「成长提醒/支持需求」，非缺陷
- 禁止「智商/注定/绝对/一定是」
- 每份报告结尾必须有一句「一句话看见」金句"""

    report_templates = {
        'personal': f"""{common}

## 报告结构
### 一、能量引擎
TRC={trc_val}（{trc_label}）。ATD={atd_val}（{atd_label}）。请根据数值区间自动输出对应类型：高TRC(>160)发散探索型/中TRC(100-160)均衡适应型/低TRC(<100)专注深耕型。ATD同理：低ATD(≤36)敏捷启动型/中ATD(37-41)均衡适应型/高ATD(≥42)沉稳深耕型。

### 二、主性格画像
基于预处理的主性格/辅助性格/全脑性格撰写。

### 三、核心驱动力（精神功能）
从功能区排序中提取精神功能区数据，解读左右脑分布。精神右脑高=自我实现者，精神左脑高=责任担当者。

### 四、能力结构（思维功能）
解读思维功能区，思维左脑高=逻辑架构师，思维右脑高=创意愿景师。

### 五、最优通道（三感分析）
从学习通道排序中提取最优通道及建议。

### 六、各功能区左右脑特征
基于偏侧化数据，逐功能区列表。

### 七、警示提醒
最低分区=警示区，给出针对性建议。

### 八、成长路径
天赋组合=主性格+优势区+最优通道。主场发挥/客场管理/一句话看见。""",

        'child': f"""{common}

## 报告结构（用温暖语气，面向家长）
### 一、孩子的学习风格
TRC={trc_val}，ATD={atd_val}。用家长能懂的语言解释。

### 二、主性格画像
孩子的主性格/辅助性格/全脑性格，翻译为家长语言。

### 三、孩子的最佳学习通道
从学习通道排序提取。第一通道及使用建议，第二第三通道作为辅助。

### 四、孩子的内驱方式（精神功能）
精神右脑高=被「我想做」驱动，精神左脑高=被「我应该做」驱动。

### 五、孩子的行为特点（体觉功能）
体觉高=需要动中学，体觉低=能安静但行动力偏弱。

### 六、孩子的沟通特点（听觉功能）
听觉左脑高=能听内容抓重点，听觉右脑高=对批评敏感。

### 七、给家长的建议
学习方式/节奏/动机/环境/沟通 五个维度 + 一句话看见。""",

        'family': f"""{common}
⚠️ 如果没有提供多位家庭成员的结构化数据，只基于可用的单人数据进行家庭关系分析，不要编造父亲/母亲/孩子的具体数值。

## 报告结构（用理解语气，面向家庭成员）
### 一、家庭能量场
基于可用数据分析能量类型。

### 二、家庭沟通频道匹配
三感通道分布 + 沟通解码（视觉型/听觉型/体觉型的不同需求）。

### 三、家庭节奏匹配
ATD分布与冲突预警/解决策略。

### 四、家庭角色分工建议
基于精神功能特点分配CEO/CFO/创新官/COO角色。

### 五、家庭共同成长建议
家庭会议/轮流策划/翻译机制 + 一句话看见。""",

        'team': f"""{common}
⚠️ 如果没有提供多位成员的详细数据，只基于可用数据给出团队风格倾向分析，不要编造具体成员信息或百分比分布。

## 报告结构（用专业语气，面向团队管理者）
### 一、团队天赋画像总览
基于可用数据给出团队风格倾向。

### 二、团队三感通道分布
视觉/听觉/体觉占比 + 沟通建议。

### 三、团队协作风险预警
基于ATD/通道/偏侧化差异的冲突风险及建议。

### 四、团队协作公约建议
信息传递/会议效率/冲突解决/优势互补规则。

### 五、团队发展建议
招聘/培训/流程优化建议 + 一句话看见。""",
    }
    return report_templates.get(tmpl, report_templates['personal'])
