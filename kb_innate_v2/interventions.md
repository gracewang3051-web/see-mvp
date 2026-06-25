# 06 Intervention Base

## 1. 定位

Intervention Base 是支持方案库。

当前版本只基于“先天优势测评”提供支持方案，不进入后天思维画像或深层心理成因分析。

它回答：

```text
根据先天特质，当前如何支持这个人更好发挥？
```

不回答：

```text
后天模式如何形成？
先天后天哪里冲突？
完整元认知训练如何设计？
```

---

# 2. 学习支持方案

## INTERVENTION_LEARNING_001 快速探索型学习者支持

```yaml
trigger:
  trc_category: high
  atd_category: low

goal:
  帮助其在保持好奇心的同时建立聚焦和沉淀能力

phase_1:
  name: 排序
  actions:
    - 把当前想做的事情列出来
    - 选出本周最重要的1件
    - 其他兴趣放入“待探索清单”

phase_2:
  name: 闭环
  actions:
    - 每个学习任务必须有一个小成果
    - 用讲解、作品、笔记、录音等方式输出

phase_3:
  name: 复盘
  actions:
    - 每周回顾：我完成了什么？我又被什么吸引了？下周主线是什么？

parent_actions:
  - 不压制兴趣
  - 帮助排序
  - 用温和提醒代替批评分心
```

## INTERVENTION_LEARNING_002 慢热深耕型学习者支持

```yaml
trigger:
  trc_category: low
  atd_category: high

goal:
  帮助其在稳定节奏中建立能力感

actions:
  - 提前预告新任务
  - 每次只安排一个重点
  - 给出清晰步骤
  - 允许较长适应期
  - 关注月度进步而非即时反应
```

## INTERVENTION_LEARNING_003 视觉预热学习流程

```yaml
trigger:
  primary_channel: visual
  or:
    auditory_low: true
    thinking_slow: true

goal:
  降低课堂即时理解压力

actions:
  - 课前15分钟视频预习
  - 用图解资料建立整体框架
  - 用思维导图整理新课
  - 把新课变成“见过一次的旧知识”
```

## INTERVENTION_LEARNING_004 听觉主导学习流程

```yaml
trigger:
  primary_channel: auditory

goal:
  利用听觉优势提升吸收和复习效率

actions:
  - 听课后马上复述
  - 用录音复习重点
  - 和同学或家长讨论
  - 把知识讲给别人听
```

---

# 3. 家庭支持方案

## INTERVENTION_FAMILY_001 家庭频道转换

```yaml
trigger:
  family_channel_mismatch: true

goal:
  让家庭成员用对方能接收的频道沟通

actions:
  visual_child:
    - 用图表、清单、步骤说明
    - 少用长篇口头说教

  auditory_child:
    - 讲清楚原因
    - 让孩子说出理解

  kinesthetic_child:
    - 做给孩子看
    - 陪孩子一起操作
    - 在运动或散步中沟通
```

## INTERVENTION_FAMILY_002 动机型孩子目标点燃

```yaml
trigger:
  child_behavior_mode: 动机型

goal:
  将外部任务转化为孩子自己的意义目标

actions:
  - 每个任务先讲为什么
  - 连接孩子在意的目标
  - 设置可展示成果
  - 多肯定过程中的主动性
```

## INTERVENTION_FAMILY_003 高敏感听觉家庭沟通

```yaml
trigger:
  family_auditory_high: true
  atd_low_members: true

goal:
  减少语气伤害，提升语言滋养

actions:
  - 家庭会议时轮流发言
  - 不打断
  - 避免高声争论
  - 重要反馈先肯定再建议
  - 情绪激动时暂停沟通
```

---

# 4. 职业支持方案

## INTERVENTION_CAREER_001 创意多面手岗位支持

```yaml
trigger:
  trc_category: high
  thinking_right: high

goal:
  让创意转化为可交付成果

actions:
  - 给开放性任务
  - 配执行型搭档
  - 设置里程碑
  - 每阶段必须输出成果
```

## INTERVENTION_CAREER_002 责任运营型岗位支持

```yaml
trigger:
  spirit_left: high
  thinking_left: high

goal:
  发挥其规则、计划、管理优势

actions:
  - 给清晰职责
  - 给流程标准
  - 给予组织和协调角色
  - 用稳定反馈激励
```

---

# 5. 关系支持方案

## INTERVENTION_RELATIONSHIP_001 爱语翻译练习

```yaml
trigger:
  partner_channel_mismatch: true

goal:
  学会用对方能接收的方式表达爱

actions:
  auditory_partner:
    - 每天一句具体肯定
    - 重要事情说出来

  visual_partner:
    - 用行动留下可见证据
    - 保持仪式感和细节

  kinesthetic_partner:
    - 拥抱
    - 陪伴做事
    - 一起运动或散步
```

---

# 6. 企业支持方案

## INTERVENTION_ENTERPRISE_001 团队沟通协议

```yaml
trigger:
  enterprise_report: true

goal:
  减少因通道差异造成的信息损耗

actions:
  - 重要信息同时用邮件、会议、演示三通道传递
  - 决策会提前发材料，照顾高ATD成员
  - 创意会前半段禁止过早否定
  - 复盘会先讲感受，再讲问题，再讲行动
```

## 7. 使用边界

1. 当前 Intervention 只提供支持策略，不做心理治疗。
2. 如果出现严重心理风险，应建议寻求专业支持。
3. 所有建议都必须与先天数据或 Insight 对应。
4. 不允许用干预方案替代医学、心理、法律建议。
