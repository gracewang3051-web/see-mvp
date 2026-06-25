# 09 Claude Code Implementation Spec

## 1. 目标

将 SEE_Innate_RAG_System_V1 工程包接入现有 RAG 系统，替换原始手册型知识库。

目标是让系统按照以下链路生成报告：

```text
测评数据 JSON
↓
Rule Engine
↓
Insight Retrieval
↓
Narrative Selection
↓
Intervention Selection
↓
Report Framework Filling
```

## 2. 推荐目录结构

```text
see_rag/
│
├── knowledge_base/
│   ├── innate_ontology/
│   ├── innate_rule_base/
│   ├── innate_insight_base/
│   ├── narrative_base/
│   ├── intervention_base/
│   └── report_framework/
│
├── parser/
│   ├── image_to_json.py
│   ├── schema_validator.py
│   └── normalizer.py
│
├── engine/
│   ├── rule_engine.py
│   ├── insight_router.py
│   ├── narrative_selector.py
│   ├── intervention_selector.py
│   └── report_builder.py
│
├── prompts/
│   ├── extraction_prompt.md
│   ├── report_generation_prompt.md
│   └── quality_check_prompt.md
│
└── tests/
    ├── sample_profile.json
    └── expected_outputs/
```

## 3. 数据处理流程

### Step 1：结构化输入

输入必须先转换成标准 JSON。

禁止直接把图片丢给报告生成器。

### Step 2：字段校验

必须校验：

```text
TRC 是否为数字
ATD 是否为数字
学习通道总和是否接近100
五大功能区是否完整
报告类型是否明确
```

### Step 3：规则匹配

规则引擎输出：

```json
{
  "rule_outputs": {
    "trc_category": "high",
    "atd_category": "low",
    "primary_channel": "auditory",
    "behavior_mode": "motivation",
    "top_three_areas": [],
    "lowest_area": ""
  }
}
```

### Step 4：Insight 检索

根据 rule_outputs 检索 Insight。

示例：

```text
high_trc + low_atd → 快速探索型学习者
auditory_primary → 听觉主导学习者
motivation_mode → 动机型意义驱动
```

### Step 5：Narrative 选择

选择适合报告对象的顾问语言。

儿童报告：生活化、温和、家长可理解。

企业报告：组织化、结构化、避免人格判断。

### Step 6：Intervention 选择

每个风险或消耗点必须匹配一个支持方案。

### Step 7：模板填充

按照 report_type 选择模板。

## 4. 报告生成 Prompt

```text
你是 SEE 先天优势解码报告生成助手。

你必须基于以下内容生成报告：
1. 用户结构化测评数据
2. Rule Engine 输出
3. Retrieved Insights
4. Selected Narratives
5. Selected Interventions
6. Report Framework

生成规则：
- 开头先做行为解码，不要先堆指标。
- 每个结论必须对应数据依据或规则依据。
- 不使用“好/坏、聪明/不聪明、一定、注定”等表达。
- 低分区写成“支持需求”或“成长提醒”，不能写成缺陷。
- 当前版本只基于先天优势测评，不做后天思维画像或差异分析。
- 如果用户提供行为现象，可以解释为“从先天特质角度可能如何理解”，不要做诊断。
- 输出必须符合所选 Report Framework。
```

## 5. 质量检查 Prompt

```text
请检查这份 SEE 报告是否符合以下标准：

1. 是否先做行为解码？
2. 是否每个结论都有数据依据？
3. 是否把低分区写成缺陷？
4. 是否出现智商、医学、心理诊断或命运判断？
5. 是否越界分析后天思维画像？
6. 是否每个风险都有支持方案？
7. 是否符合当前报告类型？
8. 是否使用了适合对象的语言？
```

## 6. 最小可用版本

优先实现：

```text
学习方式报告
家庭合盘报告
职业规划报告
```

因为这三类最能验证：

```text
个人数据解码
家庭系统解码
职业场景解码
```

## 7. 替换旧知识库建议

旧知识库：

```text
培训手册.md
应用手册.md
```

不要直接删除，建议移入：

```text
archive/original_manuals/
```

新知识库使用：

```text
SEE_Innate_RAG_System_V1/
```

## 8. 版本控制

```text
v1.0：先天优势测评 RAG
v1.1：补充更多真实顾问话术
v1.2：补充更多案例模式
v2.0：接入后天思维画像
v3.0：接入先天-后天差异分析与元认知训练
```
