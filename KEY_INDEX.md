# SEE MVP API Key 位置地图 (2026-07-05)

> 最后更新: 2026-07-05 (BAOSI_KEY 已清理) · 笨笨持久化
> 用途: Grace 不需要重新给 KEY，直接看这个文件就知道哪些 KEY 在哪里、怎么用

---

## DeepSeek (server.py 主 LLM API)

| 项目 | 内容 |
|---|---|
| 变量名 | `DEEPSEEK_KEY` |
| 服务 | DeepSeek API `api.deepseek.com/v1/chat/completions` |
| 当前值 | `sk-3ba0b8…a6282fe`（35 字符，脱敏） |
| 持久化位置 | `~/.zshrc` **line 52** |
| 同步位置 | `~/.claude/settings.json` → `env.DEEPSEEK_KEY` |
| 备注 | 与 `env.ANTHROPIC_AUTH_TOKEN` 值相同（共用同一把 DeepSeek key） |

## 百度 OCR (server.py 文字识别)

| 项目 | 内容 |
|---|---|
| 变量名 | `BAIDU_OCR_API_KEY` / `BAIDU_OCR_SECRET_KEY` |
| 服务 | 百度智能云 → 文字识别 → 高精度含位置版 (`/rest/2.0/ocr/v1/accurate`) |
| 当前值 | `IiAwabup…YomoY` / `gieYURLM…1THE`（脱敏） |
| 持久化位置 | `~/.zshrc` **lines 53-54** |
| 同步位置 | `~/.claude/settings.json` → `env.BAIDU_OCR_API_KEY` / `env.BAIDU_OCR_SECRET_KEY` |
| 来源 | `~/.zsh_history`（Codex 从百度云控制台复制） |
| 历史踩坑 | Codex 尝试写入 `.env.baidu_ocr` 被 macOS 辅助功能权限拒绝 |

> **BAOSI 已取消** — 不再使用 `BAOSI_KEY`，部署时不需要申请该 key。server.py 源码中 `BAOSI_KEY` 读取行（line 12）仍存在但作为空值安全处理，后续可清理。

---

## 各文件位置一览

| 文件路径 | 包含内容 | 行号 |
|---|---|---|
| `~/.zshrc` | DEEPSEEK_KEY, BAIDU_OCR_API_KEY, BAIDU_OCR_SECRET_KEY | 49-54 |
| `~/.claude/settings.json` | `env` 块包含 DEEPSEEK_KEY, BAIDU_OCR_API_KEY, BAIDU_OCR_SECRET_KEY + ANTHROPIC_AUTH_TOKEN | — |
| `~/.claude/settings.json.bak.20260705-baosi-cleanup` | BAOSI_KEY 清理前的 settings.json 备份 | — |
| `~/.zshrc.bak.20260705` | 持久化前的 zshrc 备份 | — |

## 快速验证命令

```bash
source ~/.zshrc && echo "DEEPSEEK: ${DEEPSEEK_KEY:0:12}..." && echo "BAIDU: ${BAIDU_OCR_API_KEY:0:8}..."
```

## 服务调用模板

### Python (server.py / engine/*.py)
```python
import os

DEEPSEEK_KEY = os.environ.get('DEEPSEEK_KEY', '')
BAIDU_OCR_API_KEY = os.environ.get('BAIDU_OCR_API_KEY', '')
BAIDU_OCR_SECRET_KEY = os.environ.get('BAIDU_OCR_SECRET_KEY', '')

if not DEEPSEEK_KEY:
    raise ValueError("DEEPSEEK_KEY 未配置。请 source ~/.zshrc 或检查 settings.json")
```

### Bash / shell 脚本
```bash
source ~/.zshrc  # 确保 KEY 在环境中
if [ -z "$DEEPSEEK_KEY" ]; then
    echo "ERROR: DEEPSEEK_KEY 未设置"
    exit 1
fi
```

### 新模块接入 KEY
1. 在 `~/.zshrc` 末尾追加 `export NEW_SERVICE_KEY="..."`（不使用 .env）
2. 在 `~/.claude/settings.json` 的 `env` 块追加同名变量（同步）
3. 更新本文件 `KEY_INDEX.md` → 添加新行到「快速索引」表
4. 在 `server.py` 中用 `os.environ.get('NEW_SERVICE_KEY', '')` 读取

## 密钥轮换流程

当某个 API KEY 需要更换时：

```bash
# 1. 获取新 KEY（从对应云控制台复制）
# 2. 更新 ~/.zshrc
sed -i '' 's/export DEEPSEEK_KEY="sk-.*"/export DEEPSEEK_KEY="sk-NEW_KEY_HERE"/' ~/.zshrc

# 3. 更新 ~/.claude/settings.json（手动编辑 env 块）
# 4. 更新本文件 KEY_INDEX.md 中的脱敏值
# 5. 生效
source ~/.zshrc
# 6. 验证
echo ${DEEPSEEK_KEY:0:12}...
# 7. 如果是 DeepSeek KEY，重启 server.py
kill -HUP $(lsof -i :8088 | grep LISTEN | awk '{print $2}') 2>/dev/null; python3 server.py &
```

## 故障排查

### DeepSeek KEY 不工作

| 现象 | 排查步骤 | 参考文件 |
|---|---|---|
| `401 Authentication Fails` | 检查 DEEPSEEK_KEY 是否在环境变量 | `KEY_INDEX.md` 全表 |
| `503 DeepSeek API Key 未配置` | server.py 读到空值 | `~/.zshrc` lines 49-54 |
| Claude Code 里找不到 | settings.json env 块没同步 | `~/.claude/settings.json` env 块 |
| 重启 tmux 后丢失 | zshrc 没写对 | `~/.zshrc`, `~/.zshrc.bak.20260705` |
| 部署后连不上 | 生产环境实例没有对应 env | 部署配置（或 Grace 确认） |

### 百度 OCR KEY 不工作

| 现象 | 排查步骤 | 参考文件 |
|---|---|---|
| `503 Baidu OCR 未配置` | BAIDU_OCR_API_KEY / SECRET_KEY 缺失 | `~/.zshrc` lines 53-54 |
| token 获取失败 | AK/SK 输入错误或已轮换 | 百度智能云控制台 → 应用列表 |
| `accurate_basic` 无法识别位置 | 调用路径是 `accurate_basic` 而非 `accurate` | `server.py` 中 endpoint 路径 |

### 通用排查顺序

1. `echo $DEEPSEEK_KEY | head -c 15` → 非空则环境正常
2. `lsof -i :8088` → 服务器在跑
3. `curl -s http://localhost:8088/api/talent-v2 -X POST -H 'Content-Type: application/json' -d '{"ocrText":"test"}'` → 服务响应
4. 见 `PITFALLS.md` 查历史踩坑记录
5. 找 Grace

## 持久化约定

- 所有 API KEY 以 `export` 写入 `~/.zshrc`，source 后对所有 shell 可见
- 同步写入 `~/.claude/settings.json` 的 `env` 块，让 Claude Code 子进程继承
- 任何 KEY 变更先更新本文件，再同步到上述两处
- 绝对不写 KEY 到 RAG 项目文件或 git 历史

## 快速备份 / 恢复

```bash
# 备份当前 KEY 状态
cp ~/.zshrc ~/.zshrc.bak.$(date +%Y%m%d-%H%M)

# 从 KEY_INDEX.md 恢复
# 笨笨: 读取本文件 "当前值" 列，重新 export
```

## Claude 最新动态 (2026-07-05 10:5x)

### 当前进展
- **项目**: SEE MVP — 结构化人才报告 OCR 编辑器 (structured-ocr-editor)
- **最后活动**: 等待 Codex 跑完测试，状态提示词为 `codex 跑完了吗`
- **Git 最近 commits** (按时间倒序):
  - `1af0800` fix: X-aligned text+value merging in Baidu OCR (±60px)
  - `5557f98` fix: Baidu OCR 90s AbortController timeout + loading UX
  - `bb83e81` feat: position-based text+value merging in Baidu OCR
  - `9271470` feat: Baidu OCR merge Chinese label + number/code lines into one row
  - `f6ad93c` feat: Baidu OCR position-based sorting (Y top→bottom, X left→right)
  - `87c275b` fix: Baidu OCR endpoint accurate_basic → accurate (高精度含位置版)
  - `c0e40c6` feat: add Baidu OCR draft recognition for talent reports
  - `a0a5978` fix: make mobile OCR an editable draft before report generation
  - `3bef36c` fix: mobile readiness — LAN IP, user code notice, text-paste guidance, PDF label
  - `f0f50b6` fix: apply _trim_incomplete to all chat replies, raise chat tokens 400→800
  - `c9779c4` fix: Codex review — Promise.race OCR timeout, composite Tesseract OCR
- **当前分支**: `structured-ocr-editor`
- **白板**: `AGENT_WHITEBOARD.md` 有 CLAUDE ACTION REQUIRED 项，Codex 审查记录

### 新发现
- **KEY/凭证**: 无新 KEY。DEEPSEEK_KEY / BAIDU_OCR_API_KEY / BAIDU_OCR_SECRET_KEY 维持不变
- **server.py 仍引用 BAOSI_KEY** (line 12: `BAOSI_KEY = os.environ.get('BAOSI_KEY', '')`; line 233 用于 Authorization header) — 但当前值为空字符串，server.py 将其安全处理（空值状态下不会造成崩溃），**后续可清理源码但不紧急**
- **无新的 .env / config / settings 变更**
- **无新的远程仓库 / GitHub 引用**
- **server.py KEY 读取变量名不变**: `BAOSI_KEY` / `DEEPSEEK_KEY` / `BAIDU_OCR_API_KEY` / `BAIDU_OCR_SECRET_KEY`

### 下一步预告
- 等待 Codex 完成测试审查（7 项测试清单已写入白板）
- Claude 可能继续修复 Baidu OCR 位置合并逻辑或调整 timeout 处理
- 如用户继续指示，可能进入结构化人才报告最终生成功能
