# OCR 文本位置识别模板

适用于桌面样本 `1280x1920` 的 SEE 先天特质报告。该模板不是全文 OCR，而是“先切块、再识别、再映射字段”的固定版式方案。

## 基准

- 参考尺寸: `1280 x 1920`
- 坐标格式: `(x, y, width, height)`
- 缩放规则: 按图片宽高比例线性缩放

## 区域表

### 总览区

| Key | 坐标 | 内容 |
|---|---:|---|
| `learning_potential_trc_label` | `(176, 436, 230, 61)` | 学习潜能 TRC 标题 |
| `learning_potential_trc_value` | `(176, 498, 230, 68)` | TRC 数值 |
| `reaction_speed_atd_label` | `(411, 436, 225, 61)` | 反应速度 ATD 标题 |
| `reaction_speed_atd_value` | `(411, 498, 225, 68)` | ATD 数值 |
| `personality_type_label` | `(640, 436, 230, 61)` | 性格类型标题 |
| `personality_type_value` | `(640, 498, 230, 68)` | 性格类型值 |
| `trc_average_label` | `(896, 436, 231, 61)` | TRC 平均值标题 |
| `trc_average_value` | `(896, 498, 231, 68)` | TRC 平均值 |

### 学习通道区

| Key | 坐标 | 内容 |
|---|---:|---|
| `learning_channel_label` | `(176, 568, 460, 43)` | 学习通道总标题 |
| `auditory_type_label` | `(176, 612, 150, 39)` | 听觉型标题 |
| `auditory_type_value` | `(176, 652, 150, 44)` | 听觉型百分比 |
| `visual_type_label` | `(333, 612, 144, 39)` | 视觉型标题 |
| `visual_type_value` | `(333, 652, 144, 44)` | 视觉型百分比 |
| `kinesthetic_type_label` | `(484, 612, 152, 39)` | 体觉型标题 |
| `kinesthetic_type_value` | `(484, 652, 152, 44)` | 体觉型百分比 |

### 行为 / 脑平衡区

| Key | 坐标 | 内容 |
|---|---:|---|
| `behavior_pattern_label` | `(640, 568, 230, 61)` | 行为模式标题 |
| `behavior_pattern_value` | `(640, 630, 230, 66)` | 行为模式值 |
| `brain_distribution_label` | `(896, 568, 231, 61)` | 左右脑分布标题 |
| `brain_distribution_value` | `(896, 630, 231, 66)` | 左右脑分布值 |

### 功能区

| Key | 坐标 | 内容 |
|---|---:|---|
| `spirit_communication_label` | `(216, 1364, 128, 66)` | 沟通管理 / 计划判断 |
| `spirit_communication_value` | `(216, 1430, 128, 58)` | 对应数值 |
| `spirit_creative_label` | `(355, 1364, 180, 66)` | 创造领导 / 目标憧憬 |
| `spirit_creative_value` | `(355, 1430, 180, 58)` | 对应数值 |
| `thinking_logic_label` | `(246, 895, 140, 68)` | 逻辑推理 / 语言功能 |
| `thinking_logic_value` | `(240, 963, 145, 52)` | 对应数值 |
| `thinking_spatial_label` | `(246, 1000, 155, 70)` | 空间心像 / 构思拟想 |
| `thinking_spatial_value` | `(240, 1070, 155, 52)` | 对应数值 |
| `body_discrimination_label` | `(526, 724, 118, 66)` | 体觉辨识 / 操作理解 |
| `body_discrimination_value` | `(526, 790, 118, 50)` | 对应数值 |
| `body_feeling_label` | `(666, 724, 126, 66)` | 体觉感受 / 艺术欣赏 |
| `body_feeling_value` | `(666, 790, 126, 50)` | 对应数值 |
| `auditory_discrimination_label` | `(962, 918, 142, 66)` | 听觉辨识 / 语言理解 |
| `auditory_discrimination_value` | `(954, 984, 150, 54)` | 对应数值 |
| `auditory_feeling_label` | `(962, 1000, 142, 70)` | 听觉感受 / 音乐欣赏 |
| `auditory_feeling_value` | `(954, 1070, 150, 54)` | 对应数值 |
| `visual_discrimination_label` | `(848, 1364, 134, 66)` | 视觉辨识 / 观察理解 |
| `visual_discrimination_value` | `(848, 1430, 134, 58)` | 对应数值 |
| `visual_feeling_label` | `(968, 1364, 162, 66)` | 视觉感受 / 图像欣赏 |
| `visual_feeling_value` | `(968, 1430, 162, 58)` | 对应数值 |

### 可选个人信息

| Key | 坐标 | 内容 |
|---|---:|---|
| `profile_name` | `(548, 990, 250, 55)` | 姓名 |
| `profile_gender` | `(548, 1058, 250, 55)` | 性别 |
| `profile_phone` | `(548, 1126, 250, 55)` | 电话 |
| `profile_birthday` | `(548, 1195, 250, 55)` | 生日 |

### 底部说明

| Key | 坐标 | 内容 |
|---|---:|---|
| `legend_row_1` | `(176, 1506, 952, 45)` | 说明行 1 |
| `legend_row_2` | `(176, 1560, 952, 45)` | 说明行 2 |
| `legend_row_3` | `(176, 1614, 952, 45)` | 说明行 3 |
| `legend_row_4` | `(176, 1668, 952, 45)` | 说明行 4 |

## 推荐处理顺序

1. 先裁切总览区，提取 TRC / ATD / 性格类型 / 平均值。
2. 再裁切学习通道区，提取三感百分比。
3. 再裁切行为 / 脑平衡区。
4. 最后裁切五大功能区与可选个人信息。

## 结构输出

最终结构建议保持为：

- `summary`
- `学习通道`
- `精神功能`
- `思维功能`
- `体觉功能`
- `听觉功能`
- `视觉功能`
- `profile_optional`（可选）

## 使用说明

- 这份模板用于云端 Claude 读取和后续改码。
- 当前默认按固定版式工作，后续如版面变动，再单独重测坐标。
