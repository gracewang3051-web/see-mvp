# 02 Innate Ontology

## 1. 定位

Innate Ontology 是 SEE 当前阶段的先天优势本体层。

它负责定义：

```text
先天测评中有哪些对象？
这些对象代表什么？
它们如何进入规则、洞察和报告？
```

## 2. 顶层对象

```yaml
PersonInnateProfile:
  description: 个体先天优势画像
  fields:
    - core_metrics
    - pattern_profile
    - behavior_mode
    - learning_channel
    - function_area_profile
    - brain_balance
    - derived_traits
```

## 3. 标准输入 Schema

```json
{
  "profile": {
    "name": "",
    "age": null,
    "gender": "",
    "role": "",
    "report_type": ""
  },
  "core_metrics": {
    "trc": null,
    "atd": null,
    "behavior_mode": "",
    "personality_type": "",
    "brain_balance": ""
  },
  "learning_channels": {
    "auditory": null,
    "visual": null,
    "kinesthetic": null,
    "primary_channel": ""
  },
  "function_scores": {
    "spirit_left": {"score": null, "pattern": ""},
    "spirit_right": {"score": null, "pattern": ""},
    "thinking_left": {"score": null, "pattern": ""},
    "thinking_right": {"score": null, "pattern": ""},
    "kinesthetic_left": {"score": null, "pattern": ""},
    "kinesthetic_right": {"score": null, "pattern": ""},
    "auditory_left": {"score": null, "pattern": ""},
    "auditory_right": {"score": null, "pattern": ""},
    "visual_left": {"score": null, "pattern": ""},
    "visual_right": {"score": null, "pattern": ""}
  },
  "derived": {
    "top_three_areas": [],
    "lowest_area": "",
    "left_right_differences": {},
    "risk_flags": []
  }
}
```

## 4. 核心指标

### TRC

```yaml
id: innate.trc
name: TRC / 学习潜能 / 大脑活跃总值
meaning: 同一时间连接、承载与接纳信息的容量
interprets:
  - information_capacity
  - divergence_vs_focus
  - multi_task_tendency
  - learning_breadth
not_equal_to:
  - 智商
  - 成绩
  - 好坏
```

### ATD

```yaml
id: innate.atd
name: ATD / 反应速度 / 反应灵敏度
meaning: 对外界刺激的反应度、敏锐度、学习速度与效率
interprets:
  - response_speed
  - sensitivity
  - learning_rhythm
  - emotional_reactivity
rule_direction:
  lower: 反应更快，敏锐度更高
  higher: 更沉稳，启动和消化需要时间
```

## 5. 行为模式

```yaml
BehaviorMode:
  motivation:
    name: 动机型
    core: 先有目标、意义、愿景，再行动
    needs:
      - 目标感
      - 价值感
      - 被认可
  ideation:
    name: 构思型
    core: 先构想、分析、推理，再行动
    needs:
      - 思考空间
      - 自我消化时间
      - 可拆解路径
  balanced:
    name: 均衡型
    core: 方向与方法相对平衡
    needs:
      - 清晰目标
      - 稳定节奏
```

## 6. 学习通道

```yaml
LearningChannel:
  auditory:
    name: 听觉型
    input: 声音、语言、讨论、讲解
    methods:
      - 听讲
      - 讨论
      - 复述
      - 有声书
      - 讲给别人听
  visual:
    name: 视觉型
    input: 图像、文字、颜色、空间、结构
    methods:
      - 图表
      - 思维导图
      - 视频示范
      - 色彩标记
  kinesthetic:
    name: 体觉型
    input: 动作、操作、体验、身体参与
    methods:
      - 动手做
      - 实验
      - 角色扮演
      - 运动中学习
```

## 7. 五大功能区

```yaml
FunctionArea:
  spirit:
    lobe: 前额叶
    theme: 起心动念
    left:
      name: 精神左脑
      meaning: 沟通管理、计划判断、集体目标、责任规则
    right:
      name: 精神右脑
      meaning: 目标憧憬、个人目标、自我实现、愿景创造

  thinking:
    lobe: 后额叶
    theme: 思考路径
    left:
      name: 思维左脑
      meaning: 逻辑推理、因果、规则、结构化分析
    right:
      name: 思维右脑
      meaning: 空间心像、构思拟想、创意、未来设想

  kinesthetic:
    lobe: 顶叶
    theme: 行动参与
    left:
      name: 体觉左脑
      meaning: 精细操作、计划行动、执行与动手
    right:
      name: 体觉右脑
      meaning: 大动作、身体感受、表现力、体验

  auditory:
    lobe: 颞叶
    theme: 倾听与情感接收
    left:
      name: 听觉左脑
      meaning: 语言理解、逻辑倾听、声音辨识
    right:
      name: 听觉右脑
      meaning: 音乐感知、情绪语调、共情感受

  visual:
    lobe: 枕叶
    theme: 观察与图像
    left:
      name: 视觉左脑
      meaning: 细节观察、文字阅读、标准辨识
    right:
      name: 视觉右脑
      meaning: 空间感知、图像想象、审美感受
```

## 8. 纹型编码

```yaml
PatternCodes:
  Wt: 目标型
  Ws: 权威型
  We: 联想型
  Wc: 整合型
  Wd: 洞悉型
  Wi: 和谐型
  Wpe: 完美型
  Wl: 优越型
  Lu: 模仿型
  Lf: 原则型
  R: 逆思型
  X: 开放/安全型
  Xn: 掌控型
```

## 9. 派生特质

```yaml
DerivedTraits:
  cognitive:
    - 发散性
    - 专注性
    - 逻辑性
    - 构思力
    - 整合力
  rhythm:
    - 快速反应
    - 慢热深耕
    - 稳定适应
  motivation:
    - 自我实现驱动
    - 责任规则驱动
    - 目标意义驱动
    - 外部榜样驱动
  communication:
    - 听觉表达
    - 视觉表达
    - 体觉表达
  behavior:
    - 行动力
    - 计划性
    - 创造性
    - 模仿性
    - 反向思考
```
