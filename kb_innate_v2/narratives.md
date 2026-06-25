# 05 Narrative Base

## 1. 定位

Narrative Base 是顾问表达库。

它负责把规则和洞察转化为用户能理解、能共情、能行动的语言。

```text
专业判断
↓
顾问语言
↓
用户理解
```

## 2. 总表达原则

不要只说：

```text
这个孩子听觉弱。
```

要说：

```text
如果课堂主要靠老师讲一遍，他可能还没来得及形成画面和结构，信息就已经过去了。
```

不要只说：

```text
高TRC容易分散。
```

要说：

```text
他的大脑像同时打开了很多窗口，不是没有兴趣，而是兴趣太容易被点亮，需要有人帮他把窗口排序。
```

## 3. 学习叙事

### NARRATIVE_LEARNING_001 听不懂循环

```yaml
condition:
  thinking_low_or_slow
  auditory_low_or_not_primary

consultant_language:
  课堂听一遍并不等于他真的完成了吸收。对这类孩子来说，新知识如果没有提前预热，很容易出现“听不懂—不想听—漏洞变大—更不想学”的循环。

parent_translation:
  这不是态度问题，而是学习输入和处理方式不匹配。

support_language:
  我们要做的不是逼他多听几遍，而是先把新知识变成他能看见、能理解、能重复接触的内容。
```

### NARRATIVE_LEARNING_002 高TRC窗口叙事

```yaml
condition:
  trc_category: high

consultant_language:
  他的脑子像同时打开了很多窗口，看到一个新东西就容易被点亮。这种孩子不是没有兴趣，而是兴趣来得太快、太多，需要训练“先完成一个窗口，再打开下一个窗口”。

support_language:
  家长要做的不是关掉他的好奇心，而是帮他排序。
```

### NARRATIVE_LEARNING_003 高ATD慢热叙事

```yaml
condition:
  atd_category: high

consultant_language:
  他不是学不会，而是需要更长的预热和消化时间。一旦进入状态，反而容易稳定积累。

support_language:
  不要用“快一点”刺激他，而要给他步骤、时间和可预期节奏。
```

## 4. 家庭叙事

### NARRATIVE_FAMILY_001 频道错位

```yaml
condition:
  parent_child_channel_mismatch

consultant_language:
  很多亲子冲突不是谁不爱谁，而是父母用自己的频道在表达，孩子却需要另一种频道来接收。

examples:
  - 听觉父母一直讲，体觉孩子需要做给他看
  - 视觉孩子需要步骤图，听觉父母却一直口头解释
```

### NARRATIVE_FAMILY_002 逆思不是反对

```yaml
condition:
  family_member_pattern: R

consultant_language:
  逆思型成员常常不是故意反对，而是天生会先看到漏洞和风险。如果表达方式太直接，家人就容易感受到被否定。

support_language:
  把“你这样不行”改成“如果这样做，可能会遇到什么风险？”
```

### NARRATIVE_FAMILY_003 动机型孩子

```yaml
condition:
  child_behavior_mode: 动机型

consultant_language:
  对动机型孩子来说，“为什么做”比“做什么”更重要。没有意义感时，他会关机；意义被点亮后，他会自己启动。
```

## 5. 关系叙事

### NARRATIVE_RELATIONSHIP_001 爱语翻译

```yaml
condition:
  partner_channel_mismatch

consultant_language:
  两个人不是不爱，而是一个人在用自己的方式表达爱，另一个人却没有用自己的频道接收到爱。

support_language:
  智慧的爱不是只用我的方式爱你，而是学习用你能接收到的方式爱你。
```

## 6. 企业叙事

### NARRATIVE_ENTERPRISE_001 执行强但创新弱

```yaml
condition:
  team_left_brain_high
  thinking_right_low

consultant_language:
  这个团队的基本盘很稳，适合把确定的事情做扎实。但如果公司进入创新或转型阶段，就需要补充能把事物连接起来、把未来想象出来的人。
```

## 7. 使用要求

1. Narrative 必须由 Rule 或 Insight 触发。
2. 不允许模型临时编造过度夸张的比喻。
3. 顾问语言要温和、解释性强，避免贴标签。
4. 家长报告要减少术语，增加生活化翻译。
5. 企业报告要减少人格评价，增加组织结构语言。
