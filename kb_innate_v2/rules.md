# 03 Innate Rule Base

## 1. 定位

Innate Rule Base 负责把先天测评数据转化为稳定的中间判断。

```text
测评字段
↓
规则匹配
↓
特质标签
↓
场景洞察
```

## 2. TRC 规则

```yaml
- id: RULE_TRC_LOW
  condition:
    trc: "<100"
  output:
    label: 低TRC
    trait:
      - 聚焦
      - 深耕
      - 单线程
    behavior_tendency:
      - 更适合长期专注一件事
      - 不喜欢频繁切换任务
    support:
      - 一次只给一个目标
      - 减少同时安排多个兴趣或任务
    caution:
      - 不代表智商低
      - 不代表能力弱

- id: RULE_TRC_MIDDLE
  condition:
    trc: "100-160"
  output:
    label: 中TRC
    trait:
      - 均衡
      - 适应
    behavior_tendency:
      - 可兼顾广度与深度
    support:
      - 根据阶段目标灵活安排

- id: RULE_TRC_HIGH
  condition:
    trc: ">160"
  output:
    label: 高TRC
    trait:
      - 多元
      - 发散
      - 多线程
    behavior_tendency:
      - 兴趣广
      - 想法多
      - 容易同时关注多个方向
    risk:
      - 容易分散
      - 不喜欢重复
      - 需要收束
    support:
      - 建立优先级
      - 用阶段性目标聚焦
      - 用项目制承载多元兴趣
```

## 3. ATD 规则

```yaml
- id: RULE_ATD_LOW
  condition:
    atd: "<=36"
  output:
    label: 低ATD
    trait:
      - 反应快
      - 敏感
      - 启动快
    behavior_tendency:
      - 一点就通
      - 对环境刺激敏锐
      - 容易快速判断
    risk:
      - 快而粗
      - 情绪或语气容易影响状态
    support:
      - 训练复述
      - 加入检查
      - 在冲动前暂停

- id: RULE_ATD_MIDDLE
  condition:
    atd: "37-41"
  output:
    label: 中ATD
    trait:
      - 均衡
      - 稳定适应
    support:
      - 适合常规教学与工作节奏

- id: RULE_ATD_HIGH
  condition:
    atd: ">=42"
  output:
    label: 高ATD
    trait:
      - 沉稳
      - 慢热
      - 深度消化
    behavior_tendency:
      - 新任务启动慢
      - 熟悉后后劲足
    risk:
      - 被催促会压力大
      - 容易被误解为慢或不上心
    support:
      - 提前预告
      - 分解任务
      - 给足预热和消化时间
```

## 4. 学习通道规则

```yaml
- id: RULE_CHANNEL_AUDITORY
  condition:
    primary_channel: auditory
  output:
    label: 听觉主导
    behavior:
      - 通过听讲、讨论、复述吸收更快
      - 对语气和声音环境敏感
    support:
      - 多讲出来
      - 多讨论
      - 用录音、有声书、讲解视频
      - 复习时让其讲给别人听

- id: RULE_CHANNEL_VISUAL
  condition:
    primary_channel: visual
  output:
    label: 视觉主导
    behavior:
      - 通过图像、文字、颜色、结构吸收更快
      - 对环境整洁和视觉线索敏感
    support:
      - 用图表
      - 用思维导图
      - 用视频和示范
      - 用色彩标记重点

- id: RULE_CHANNEL_KINESTHETIC
  condition:
    primary_channel: kinesthetic
  output:
    label: 体觉主导
    behavior:
      - 通过动手、操作、体验吸收更快
      - 久坐听讲效率低
    support:
      - 动手做
      - 用实验
      - 角色扮演
      - 允许适度身体活动
```

## 5. 行为模式规则

```yaml
- id: RULE_BEHAVIOR_MOTIVATION
  condition:
    behavior_mode: 动机型
  output:
    label: 动机型
    behavior:
      - 需要知道为什么要做
      - 目标感强时行动快
      - 不喜欢被直接命令
    support:
      - 先讲意义
      - 给愿景
      - 给展示机会
      - 用目标驱动行动

- id: RULE_BEHAVIOR_IDEATION
  condition:
    behavior_mode: 构思型
  output:
    label: 构思型
    behavior:
      - 做事前需要想清楚
      - 喜欢构想、推理和分析
      - 被打断时效率下降
    support:
      - 给思考空间
      - 帮助分解目标
      - 用行动替代过度思考

- id: RULE_BEHAVIOR_BALANCED
  condition:
    behavior_mode: 均衡型
  output:
    label: 均衡型
    behavior:
      - 方向与方法较平衡
      - 不偏激
    support:
      - 保持目标清晰
      - 给稳定反馈
```

## 6. 功能区规则

```yaml
- id: RULE_SPIRIT_RIGHT_HIGH
  condition:
    spirit_right: top_area
  output:
    label: 精神右脑优势
    trait:
      - 个人目标
      - 愿景
      - 自我实现
    behavior:
      - 需要意义感
      - 被愿景点燃后动力强
    support:
      - 讲清楚价值
      - 连接个人目标

- id: RULE_SPIRIT_LEFT_HIGH
  condition:
    spirit_left: top_area
  output:
    label: 精神左脑优势
    trait:
      - 责任
      - 规则
      - 计划
      - 集体目标
    support:
      - 给规则
      - 给责任角色
      - 让其参与管理与组织

- id: RULE_THINKING_LEFT_HIGH
  condition:
    thinking_left: top_area
  output:
    label: 思维左脑优势
    trait:
      - 逻辑
      - 分析
      - 因果
      - 结构
    support:
      - 用结构化资料
      - 给推理任务

- id: RULE_THINKING_RIGHT_HIGH
  condition:
    thinking_right: top_area
  output:
    label: 思维右脑优势
    trait:
      - 构思
      - 创意
      - 想象
      - 未来画面
    support:
      - 给创意空间
      - 允许构想和表达

- id: RULE_KINESTHETIC_LEFT_LOW
  condition:
    kinesthetic_left: lowest_area
  output:
    label: 体觉左脑弱势提醒
    behavior:
      - 书写或精细操作可能消耗大
      - 纯重复操作容易疲惫
    support:
      - 减少无效抄写
      - 用工具辅助
      - 分段完成任务

- id: RULE_AUDITORY_LOW
  condition:
    auditory_left: low
    auditory_right: low
  output:
    label: 听觉弱势提醒
    behavior:
      - 单纯听讲效率可能不高
      - 容易漏掉口头信息
    support:
      - 书面确认
      - 图像辅助
      - 课前预习
```

## 7. 三优一阻规则

```yaml
- id: RULE_3_STRENGTHS_1_BLOCK
  logic:
    - 将10个功能区分值排序
    - 取前三个为优势区
    - 取最低一个为阻碍/成长提醒区
  output:
    model: 三优一阻
    interpretation:
      strengths: 主场优势
      blocker: 客场消耗点
    usage:
      - 学习报告
      - 职业报告
      - 生命成长报告
```

## 8. 组合规则

```yaml
- id: COMBO_HIGH_TRC_LOW_ATD
  condition:
    trc_category: high
    atd_category: low
  output:
    label: 快速探索型
    behavior:
      - 兴趣广
      - 反应快
      - 新鲜感强
    risk:
      - 容易快进快出
      - 需要沉淀
    support:
      - 阶段性聚焦
      - 输出式学习
      - 小目标闭环

- id: COMBO_LOW_TRC_HIGH_ATD
  condition:
    trc_category: low
    atd_category: high
  output:
    label: 专注深耕型
    behavior:
      - 慢热
      - 专注
      - 适合长期训练
    support:
      - 少而精
      - 给足时间
      - 不频繁切换

- id: COMBO_AUDITORY_HIGH_ATD_LOW
  condition:
    primary_channel: auditory
    atd_category: low
  output:
    label: 快速听觉学习者
    behavior:
      - 听得快
      - 反应快
      - 讨论中更容易打开
    risk:
      - 容易受语气影响
    support:
      - 多鼓励
      - 多复述
      - 避免高压批评语气
```
