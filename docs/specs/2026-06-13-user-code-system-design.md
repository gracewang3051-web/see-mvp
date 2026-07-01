# SEE H5 用户码系统设计

## 1. 目标

将用户码管理从 localStorage 迁移到 server.py 后端，支持批量生成、额度管理、报告记录。

## 2. 数据模型

server.py 维护 `data.json`：

```json
{
  "codes": {
    "PX001": {"quota": 3, "used": 0, "name": "", "createdAt": "2026-06-13T..."},
    "PX002": {"quota": 20, "used": 5, "name": "VIP用户", "createdAt": "2026-06-13T..."}
  },
  "records": [
    {"code": "PX001", "type": "portrait", "date": "2026-06-13 14:30", "content": "..."},
    {"code": "PX001", "type": "talent", "date": "2026-06-13 15:00", "content": "..."}
  ]
}
```

- `codes`: key 为用户码，value 含额度、已用次数、名称、创建时间
- `records`: 数组，每条记录含用户码、报告类型、日期、完整 Markdown 内容

## 3. API 端点

| 方法 | 路径 | 功能 | 请求体 | 返回 |
|------|------|------|--------|------|
| POST | `/api/codes/gen` | 批量生成码 | `{prefix:"PX", count:10, quota:3}` | `{codes:["PX001"..."PX010"]}` |
| GET | `/api/codes/list` | 列出所有码 | — | `{codes: {...}}` |
| POST | `/api/codes/quota` | 修改额度 | `{code:"PX001", quota:20}` | `{ok:true}` |
| POST | `/api/check-code` | 验证码有效性 | `{code:"PX001"}` | `{valid:true, quota:3, used:0}` |
| POST | `/api/report` | 生成报告(含userCode) | `{type, portrait, userCode}` | `{content, usage, cost}` |
| GET | `/api/reports?code=XXX` | 报告列表(元数据) | — | `{reports:[{type,date,index}]}` |
| GET | `/api/reports?code=XXX&id=N` | 单份报告内容 | — | `{type, date, content}` |

## 4. 页面改动

### 4.1 admin.html
- 批量生成：前缀 + 数量 + 默认额度 → 调 `/api/codes/gen`
- 码列表：从 `/api/codes/list` 加载替换 localStorage
- 单独调额度：新增操作，调 `/api/codes/quota`
- 二维码生成：`api.qrserver.com` 不变
- 使用记录：从 localStorage 改为 `/api/records`（或复用 records 数据）

### 4.2 index.html（用户端）
- 用户码输入框（已有）→ 上传 + OCR 不强制
- 点击「生成报告」→ 检查用户码：
  - 无码：弹窗输入
  - 有码：调 `/api/check-code` 验证 → 额度用完弹「联系顾问购买」
  - 验证通过：调 `/api/report`（带 userCode）→ 成功后扣额度
- 不显示剩余份数

### 4.3 insight.html（用户查看）
- 输入用户码 → 调 `/api/reports?code=XXX` → 显示报告列表（类型 + 日期）
- 点击某份报告 → 调 `/api/reports?code=XXX&id=N` → 打开完整内容
- 已有界面结构基本可用，改数据源即可

## 5. 安全
- API Key 从环境变量读取
- `data.json` 通过 API 访问，不直接暴露
- 无用户认证（Phase 1 简化）

## 6. 向后兼容
- 保留原 localStorage 读取逻辑作为 fallback
- 优先从 server API 读取
