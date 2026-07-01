# SEE H5 Phase 2 租户版（顾问系统）设计

## 1. 数据模型

### 1.1 三层结构

```
超级管理员
  └── 顾问（专属二维码 + 品牌页 + 管理面板）
        └── 用户码 → 终端客户 → 报告（默认3份/人）
```

### 1.2 data.json 扩展

```json
{
  "advisors": {
    "linruoxi": {
      "id": "linruoxi",
      "name": "林若溪",
      "role": "SEE 生命印迹成长顾问",
      "city": "上海",
      "bio": "擅长亲子沟通与学习路径梳理",
      "phone": "138-0000-1024",
      "hero": "hero_lin.jpg",
      "avatar": "lin_avatar.jpg",
      "color": "#6b96ac",
      "contact": "微信 SEElife2026",
      "qrUrl": "https://report.puxin2022.com/?advisor=linruoxi",
      "features": ["portrait", "talent", "insight"],
      "layout": ["hero", "features", "upload", "composite", "see-card"],
      "userCodes": ["PX001","PX002","PX003"],
      "totalQuota": 30
    }
  },
  "codes": {
    "PX001": {"quota": 3, "used": 0, "advisor": "linruoxi", "createdAt": "..."}
  },
  "records": [
    {"code": "PX001", "type": "portrait", "date": "...", "content": "...", "advisor": "linruoxi"}
  ]
}
```

## 2. 页面定制方案

### 2.1 配置驱动渲染

一套 `index.html`，根据 `?advisor=linruoxi` 加载配置 → 动态渲染。

```json
{
  "id": "linruoxi",
  "name": "林若溪",
  "hero": "hero_lin.jpg",
  "features": ["portrait", "talent", "insight"],
  "layout": ["hero", "features", "upload", "composite", "see-card"],
  "color": "#6b96ac",
  "contact": "微信 SEElife2026"
}
```

### 2.2 定制能力

| 维度 | 实现方式 | 新顾问成本 |
|------|----------|-----------|
| 内容（名称/头像/介绍） | JSON 字段 | 🟢 1分钟 |
| 品牌色 | CSS 变量覆盖 | 🟢 1个字段 |
| 功能模块开关 | features 数组 | 🟢 勾选 |
| 页面布局顺序 | layout 数组 | 🟢 调顺序 |
| 头图 | 上传图片 | 🟡 需要图片 |

**新增一个顾问：创建 `advisors/xxx.json` + 一张头图 → 完成。**

## 3. API 端点

| 方法 | 路径 | 功能 | 权限 |
|------|------|------|------|
| GET | `/api/advisor-config?id=xxx` | 获取顾问配置（公开） | — |
| GET | `/api/advisor/dashboard?advisor=xxx` | 顾问自己的数据面板 | 顾问 |
| POST | `/api/codes/gen` | 批量生成码（绑定顾问） | 管理员/顾问 |
| GET | `/api/codes/list?advisor=xxx` | 列出顾问名下的码 | 管理员/顾问 |
| GET | `/api/records?advisor=xxx` | 顾问名下记录 | 管理员/顾问 |

## 4. 轻量化原则

**定制由开发者完成，不在 admin 里做可视化编辑器。**

| 操作 | 谁做 | 方式 |
|------|------|------|
| 添加顾问 | 超管 | admin 里填姓名+角色 |
| 页面定制 | 开发者 | 创建/修改 `advisors/xxx.json` |
| 用户码管理 | 超管/顾问 | admin 里操作 |

这样 admin.html 保持简洁：
- 顾问列表（只显示、不编辑样式）
- 批量生成用户码（已有）
- 单独调额度（已有）
- 使用记录（已有）

不含：配色选择器、图片上传、模块拖拽、布局编辑器。

## 5. admin.html 顾问模式

URL 参数控制：

| 参数 | 可见范围 |
|------|----------|
| 无参数 | 超管（全部） |
| `?advisor=linruoxi` | 顾问（仅自己数据） |

## 6. 从 Phase 1 迁移

| Phase 1 | Phase 2 | 量级 |
|---------|---------|------|
| data.json 只有 codes/records | 加 advisors 层 | 🟢 |
| index.html 无顾问概念 | 读 `?advisor=` + JSON 配置渲染 | 🟡 |
| admin.html 单体 | 加顾问模式（权限过滤） | 🟡 |
| 无顾问配置 | advisors/*.json 目录 | 🟢 |
| server.py 无过滤 | 加 advisor 参数 | 🟢 |

## 7. 二维码流程

```
超管 admin → 加顾问 → 生成二维码
→ https://report.puxin2022.com/?advisor=linruoxi
→ 顾问分享给客户 → 客户看到品牌页 → 输用户码 → 生成报告
```

## 8. 不做

- ❌ admin 里可视化编辑页面样式
- ❌ 顾问独立登录/密码
- ❌ 自定义域名
- ❌ 顾问自己管理二维码
