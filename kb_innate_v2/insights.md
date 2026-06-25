# 04 Innate Insight Base

## 1. 定位

Insight Base 负责将多个规则标签组合成“可解释的场景洞察”。

它不是简单复述指标，而是形成顾问式判断：

```text
数据组合
↓
行为倾向
↓
可能误解
↓
真实支持方向
```

---

# 2. 学习类 Insight

## INSIGHT_LEARNING_001 快速探索型学习者

```yaml
condition:
  trc_category: high
  atd_category: low

one_sentence:
  这是一个接收快、反应快、兴趣容易被打开，但需要帮助聚焦与沉淀的学习者。

behavior_decode:
  - 高TRC使其容易同时关注多个方向
  - 低ATD使其对新知识反应快、启动快
  - 两者组合后，容易表现为兴趣广、切换快、对重复训练耐受度低

misunderstanding:
  - 家长可能以为他不专注
  - 老师可能以为他不愿意坚持

support_direction:
  - 不要简单压制兴趣
  - 要帮助排序
  - 每阶段只保留一个主线目标
  - 用输出和项目闭环帮助沉淀
```

## INSIGHT_LEARNING_002 慢热深耕型学习者

```yaml
condition:
  trc_category: low
  atd_category: high

one_sentence:
  这是一个启动慢但能深度积累，适合少而精长期发展的学习者。

behavior_decode:
  - 低TRC让其更适合聚焦一件事
  - 高ATD让其需要更多预热和消化时间
  - 熟悉后可以持续深入

misunderstanding:
  - 容易被误解为反应慢
  - 容易被误解为不积极

support_direction:
  - 给足时间
  - 不催促
  - 任务分解
  - 稳定环境
```

## INSIGHT_LEARNING_003 听觉主导学习者

```yaml
condition:
  primary_channel: auditory

one_sentence:
  这个人更适合通过听讲、讨论、复述和表达来学习。

behavior_decode:
  - 声音和语言是重要输入通道
  - 讲出来有助于完成内化
  - 讨论能提升学习热情

risk:
  - 容易受语气影响
  - 嘈杂环境可能消耗注意力

support:
  - 学完讲一遍
  - 录音复习
  - 讨论式学习
  - 用正向语言反馈
```

## INSIGHT_LEARNING_004 视觉预热型学习者

```yaml
condition:
  primary_channel: visual
  thinking_area: low_or_middle

one_sentence:
  这个人需要先看到结构和画面，再进入理解和吸收。

behavior_decode:
  - 如果直接听讲，可能难以形成整体框架
  - 通过图像、视频、思维导图预热后，理解效率会明显提升

support:
  - 课前用图解预习
  - 用视频把新课变旧课
  - 用思维导图建立脉络
```

---

# 3. 家庭类 Insight

## INSIGHT_FAMILY_001 频道错位型亲子沟通

```yaml
condition:
  parent_channel != child_channel

one_sentence:
  亲子冲突不一定来自态度问题，可能只是双方习惯使用的沟通频道不同。

behavior_decode:
  - 听觉型父母喜欢讲
  - 视觉型孩子需要看
  - 体觉型孩子需要做
  - 如果父母只用自己的通道，孩子可能接收不到

support:
  - 听觉孩子：讲给他听，也让他说回来
  - 视觉孩子：画给他看，用表格和步骤
  - 体觉孩子：做给他看，陪他一起做
```

## INSIGHT_FAMILY_002 动机型孩子需要意义感

```yaml
condition:
  child_behavior_mode: 动机型

one_sentence:
  动机型孩子不是不听话，而是需要先理解这件事为什么值得做。

behavior_decode:
  - 没有目标感时容易抵触
  - 看到意义后行动力会明显提升

support:
  - 少说“你必须”
  - 多说“这件事对你有什么用”
  - 把任务转化成孩子自己的目标
```

## INSIGHT_FAMILY_003 逆思型家长的挑战式支持

```yaml
condition:
  parent_pattern: R

one_sentence:
  逆思型家长的优势是发现问题和风险，但表达不当时容易被孩子感受为否定。

behavior_decode:
  - 家长本意是帮孩子完善方案
  - 孩子可能听成“你又在挑我毛病”

support:
  - 用问题代替否定
  - 用“如果……会怎样”代替“你这样不对”
  - 把批判变成压力测试
```

---

# 4. 职业类 Insight

## INSIGHT_CAREER_001 创意多面手

```yaml
condition:
  trc_category: high
  thinking_right: high

one_sentence:
  这个人适合开放性、创意型、连接型任务，但需要执行收束机制。

strength:
  - 点子多
  - 连接能力强
  - 适合产品、策划、内容、咨询、市场

risk:
  - 后期执行可能松散
  - 容易不断提出新想法

support:
  - 配执行型搭档
  - 设置里程碑
  - 用阶段成果收束
```

## INSIGHT_CAREER_002 责任运营型

```yaml
condition:
  spirit_left: high
  thinking_left: high

one_sentence:
  这个人适合规则清晰、责任明确、需要组织和推进的岗位。

strength:
  - 计划性
  - 责任感
  - 逻辑管理
  - 适合运营、项目管理、流程管理

risk:
  - 可能对变化或模糊目标不适应

support:
  - 给清晰边界
  - 给标准流程
  - 给可衡量目标
```

---

# 5. 关系类 Insight

## INSIGHT_RELATIONSHIP_001 爱语频道错位

```yaml
condition:
  partner_a_channel != partner_b_channel

one_sentence:
  两个人不是不爱，而是表达爱和接收爱的频道不同。

behavior_decode:
  - 听觉型需要听到确认
  - 视觉型需要看到用心
  - 体觉型需要感受到陪伴和行动

support:
  - 用对方能接收的方式表达爱
  - 不只用自己的方式表达
```

## INSIGHT_RELATIONSHIP_002 快慢节奏关系

```yaml
condition:
  partner_a_atd_category != partner_b_atd_category

one_sentence:
  快节奏一方负责启动，慢节奏一方负责深化，关键是互相翻译节奏差异。

conflict:
  - 快者觉得慢者拖延
  - 慢者觉得快者催促

support:
  - 快者学会等待
  - 慢者及时反馈进度
  - 重大决定设置缓冲期
```

---

# 6. 企业类 Insight

## INSIGHT_ENTERPRISE_001 创新不足型团队

```yaml
condition:
  thinking_right_ratio: low
  spirit_right_ratio: low

one_sentence:
  团队执行可能稳定，但创新和连接能力需要补充。

risk:
  - 创意不足
  - 变革慢
  - 产品或战略想象力不足

support:
  - 引入思维右脑高的人才
  - 设立创新小组
  - 在创意阶段禁止过早否定
```

## INSIGHT_ENTERPRISE_002 执行强但保守型团队

```yaml
condition:
  spirit_left_ratio: high
  thinking_left_ratio: high
  trc_low_ratio: high

one_sentence:
  这是一个稳定、规则强、执行可靠，但可能偏保守的团队。

support:
  - 保留稳定优势
  - 增加外部创新刺激
  - 通过试点降低变化风险
```
