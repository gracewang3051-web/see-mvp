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
    'portrait':    '先天思维特质报告',
    'learning':    '学习方式分析报告',
    'emotion':     '情绪模式洞察报告',
    'potential':   '潜能发展方向报告',
    'communication': '关系洞察报告',
    'career':      '职业规划报告',
    'action':      '个人成长建议报告',
}


def build_prompt(structure, meaning, knowledge, report_type='learning', style='gentle', age=None, target='self'):
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

{(chr(10).join(['## 匹配的知识库'] + kb_sections)) if kb_sections else ''}

## 报告模板
{knowledge.get('frameworks', '')[:400]}
"""

    user_prompt = f"""## 用户测评数据
{meaning.get('raw_input', '')[:2000]}{age_context}{target_context}

## 结构分析
{zone_sections}

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
