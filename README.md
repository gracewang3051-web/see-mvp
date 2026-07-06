# SEE MVP — 生命印迹 元认知训练系统

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | Python 3 标准库（`http.server` + `ThreadingMixIn`），零框架，零依赖 |
| 数据库 | SQLite（`see_data.db`），启动自动创建 |
| AI 服务 | DeepSeek v4-pro（LLM）+ 百度云 OCR |
| 前端 | 原生 HTML/CSS/JS，Tesseract.js 本地 OCR 兜底 |
| 代码量 | **7002 行**（服务端 1675 + 前端 3249 + 引擎 2078） |

## 快速启动

```bash
python3 server.py
# → http://localhost:8088
# → http://localhost:8088/admin.html  后台管理
# → http://localhost:8088/insight.html  报告总览
```

---

## 系统架构

```
┌──────────────────────────────────────────────┐
│              server.py :8088                  │
│  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │ OCR/AI   │  │ 报告生成 │  │ 数据库 API  │  │
│  │ 代理层   │  │ 引擎编排 │  │ SQLite      │  │
│  │ Baidu    │  │ Cognitive│  │ users       │  │
│  │ DeepSeek │  │ Engine   │  │ reports     │  │
│  └──────────┘  └──────────┘  └────────────┘  │
└──────┬───────────────────────────────────────┘
       │ HTTP
┌──────┼───────────────────────────────────────┐
│      ▼           前端 4 页面                  │
│  index.html    talent.html                    │
│  思维画像      先天思维特质                    │
│  25 题测评     结构化 OCR + 知识库             │
│                                               │
│  insight.html  admin.html                     │
│  报告总览      后台管理                        │
│  交叉比对      用户码/二维码/激活码             │
└───────────────────────────────────────────────┘
```

## 页面功能

### 1. index.html — 思维画像报告（839 行）

上传 SEE 卡 25 题答题卡照片，生成思维画像报告。

```
拍照上传 → 百度云 OCR（Tesseract 回退）
  → DeepSeek 解析 25 题答案 + 4 手写字段
  → 用户核对 + 大脑通道(radio) + 接收器(checkbox)
  → 27 字段完整性校验
  → SEE 卡规则引擎（纯代码）: _match_combo 计票 × 30+ 组合规则
  → DeepSeek v4-pro → 800-1200 字报告
  → SQLite 保存 + PDF/Word/MD 下载
```

| 功能 | 说明 |
|------|------|
| OCR 识别 | 百度云 → Tesseract.js 本地回退 → 手动输入兜底 |
| 手动输入 | 25 题下拉，27 字段严格校验 |
| 规则引擎 | 5 层计票匹配 × 5 功能区 × 30+ 组合规则 |
| 关系合盘 | 上传对方报告 → 亲子/伴侣/家庭交叉分析 |
| 报告下载 | PDF + Word + MD，文件名含姓名+用户码 |

### 2. talent.html — 先天思维特质报告（1423 行）

上传天赋测评报告照片，生成先天特质解读。

```
拍照上传 → 百度云 OCR（28 区域坐标定位 + 中文标签映射）
  → 结构化编辑面板（TRC/ATD/通道/功能区 可视化编辑）
  → 三层认知引擎: 提取 → 规则 → LLM
  → 知识库注入（kb_talent/ 培训 + 应用手册）
  → SQLite 保存 → 对话咨询 → 整合报告
```

| 功能 | 说明 |
|------|------|
| OCR 识别 | 28 坐标模板 + 区域值提取 + OCR 错字容错 |
| 结构化编辑 | TRC/ATD/通道/十大功能区 数值+纹型可编辑 |
| 顾问风格 | 5 种（温和/亲子/教育/教练/直接）× 4 种对象（self/parent/other/global） |
| 年龄适配 | 儿童/青少年/青年/成人 自动调整语言和报告名 |
| 异步生成 | 后台线程 + 前端轮询 |
| 对话咨询 | 聊天式优化 + 自动整合 |
| 关系合盘 | 双人报告交叉分析 |
| 报告下载 | PDF + Word + MD |

### 3. insight.html — 自我觉察陪伴（366 行）

按用户码查看所有历史报告，交叉比对。

| 功能 | 说明 |
|------|------|
| 报告总览 | 画像 + 特质历史版本列表 |
| 成长比对 | 选两份报告 × DeepSeek 交叉分析 |
| 报告下载 | .md 多 section 合并下载 |
| 配额显示 | 跨页面统计（画像 + 特质合计） |

### 4. admin.html — 后台管理（621 行）

| 功能 | 说明 |
|------|------|
| 用户码管理 | 增/删/改，每人独立报告上限（服务端 SQLite） |
| 一键初始化 | PX001-PX010 测试码批量创建 |
| 配额监控 | 实时计数，≥80% ⚠️，满额标红 |
| 二维码生成 | 入口二维码（名称 + 人数 + 份数 + 有效期） |
| 激活码管理 | 一次性激活码（额外报告数 + 权益描述） |
| 使用记录 | CSV 导出 |

## API 端点（20 个）

| 分类 | 端点 | 用途 |
|------|------|------|
| **报告** | `POST /api/report` | 思维画像报告（SEE 卡规则引擎） |
| | `POST /api/talent-v2` | 先天特质报告（认知引擎同步版） |
| | `POST /api/talent-job` | 先天特质报告（异步版） |
| | `GET /api/talent-job?id=` | 轮询异步任务 |
| **OCR** | `POST /api/baidu-ocr` | 百度云 OCR + 区域值提取 |
| | `POST /api/parse-answers` | OCR → 25 题答案（DeepSeek） |
| | `POST /api/extract-metrics` | OCR → 结构化指标（纯代码） |
| **对话** | `POST /api/talent-chat` | 对话咨询 + 整合 |
| **专项** | `POST /api/composite` | 关系合盘 |
| | `POST /api/growth` | 成长比对 |
| | `POST /api/belief` | 信念系统分析 |
| **导出** | `POST /api/export-pdf` | 服务端 PDF |
| | `POST /api/export-doc` | Word 导出（兼容微信） |
| **数据库** | `POST /api/db/reports` | 保存报告 |
| | `GET /api/db/reports?code=` | 查询报告 |
| | `GET /api/db/users` | 用户列表 + 报告计数 |
| | `POST /api/db/users` | 增/改/删用户 |

## 引擎层（engine/）

```
engine/
├── orchestrator.py  119行  三层 pipeline 编排
├── extractor.py     144行  正则提取 TRC/ATD/通道/功能区
├── rules.py         551行  天赋特质规则引擎（18 种组合 + 纹型解读）
├── prompts.py       408行  5 风格 × 4 对象 × 年龄适配 prompt
├── see_card.py      456行  思维画像引擎（30+ 组合规则 + 计票算法）
├── retrieval.py     118行  知识库检索
├── interpreter.py    70行  纹型 → 自然语言解释
└── validator.py     200行  输出质量校验
```

## 数据库

```sql
users (
  code       TEXT PRIMARY KEY,
  name       TEXT DEFAULT '',
  max_reports INTEGER DEFAULT 20,
  created_at TEXT DEFAULT (datetime('now')),
  last_active TEXT DEFAULT ''
)

reports (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  user_code  TEXT NOT NULL,
  type       TEXT NOT NULL,    -- 'portrait' | 'talent'
  sections   TEXT NOT NULL,     -- JSON
  created_at TEXT DEFAULT (datetime('now'))
)
```

## 双引擎对比

| | 思维画像 | 先天特质 |
|---|---|---|
| **页面** | index.html | talent.html |
| **输入** | 25 题 A/B/C/D 答案 | 天赋测评 OCR（TRC/ATD/功能区） |
| **OCR 解析** | DeepSeek 解析 25 题答案 | 28 坐标模板 + 正则提取 |
| **规则引擎** | `_match_combo` 计票 + 30+ 组合规则 | 18 种 TRC/ATD/模式组合 + 纹型解读 |
| **知识库** | `kb_portrait/SEE卡应用手册.md` | `kb_talent/` 培训 + 应用手册 |
| **报告类型** | portrait / communication / action / career | portrait / learning / emotion / potential |
| **风格适配** | 内置 prompt | 5 风格 × 4 对象 × 年龄 |
| **对话咨询** | 无 | 有（chat + summarize） |

## 配额体系

```
Admin 添加用户 → SQLite users 表（含 maxReports）
  ↓
前端加载 → GET /api/db/users → _userCache 缓存
  ↓
isValidCode(code)  → 检查 code 是否在缓存中
getMaxReports(code) → 读用户的 maxReports
getReportCount(code) → 画像 + 特质报告合计
  ↓
生成报告前 → count ≥ max → alert → 拦截
saveReports() → POST /api/db/reports → SQLite → 刷新缓存
```

## 目录结构

```
see-mvp/
├── server.py          服务端（API + SQLite + OCR 代理）
├── index.html          思维画像报告页
├── talent.html         先天思维特质报告页
├── insight.html        自我觉察陪伴页
├── admin.html          后台管理页
├── see_data.db         SQLite 数据库
├── engine/             认知引擎
├── kb_talent/          天赋知识库（只读）
├── kb_portrait/        画像知识库（只读）
└── tesseract/          Tesseract.js 本地 OCR
```
