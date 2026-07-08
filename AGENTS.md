# AGENTS.md · SEE MVP 协作铁律

> 启动必读。Codex / Claude / 任何 AI agent session 启动时第一件事 cat 这个文件。

## 🚨 启动 checklist（不可跳过）

```bash
# 1. 读规则（你自己）
cat AGENTS.md

# 2. 读 KEY 位置（API key 怎么读、值在哪）
cat KEY_INDEX.md

# 3. 读现状（谁在做什么、下一步）
cat PROGRESS.md | tail -100

# 4. 读历史踩坑（已经踩过的坑不要再踩）
cat PITFALLS.md | tail -30

# 5. 读决策日志（不要重复纠结已决策的事）
cat DECISIONS.md | tail -20

# 6. 读白板（Claude 的最新任务流）
cat WHITEBOARD.md 2>/dev/null || cat AGENT_WHITEBOARD.md
```

不读就开工 = 违反铁律。

## 🤝 协作分工

| Agent | 角色 | 写什么 |
|---|---|---|
| Claude | 拆任务、定优先级 | WHITEBOARD.md 顶行 + AGENTS.md 引用 |
| Codex | 写代码、跑测试 | WHITEBOARD.md 底行 + commit |
| Grace | 决策、收尾 | 任意 .md 标注 "## Grace decision" |

## ⚠️ 铁律（违反任一条 = bug）

1. **白板每次插顶行**（不 overwrite）：
   ```bash
   TS=$(date +%Y-%m-%dT%H:%M)
   TASK="..."
   printf "\n## $TS [Claude→Codex]\n$TASK\n" > /tmp/wb.new
   cat WHITEBOARD.md >> /tmp/wb.new
   mv /tmp/wb.new WHITEBOARD.md
   ```
2. **完工回写加底行**：`echo "..." >> WHITEBOARD.md`
3. **API key 永远从环境变量读**：`os.environ.get(...)`，绝不硬编码
4. **RAG 路径只读不写**：`~/.claude/projects/see-mvp-rag/` 下任何修改先问 Grace
5. **不用 BAOSI_KEY**（已彻底取消）
6. **跨 session 必须写 PROGRESS.md**：session 结束前 append 至少一行

## 🔑 API KEY 索引（精简版，详细见 KEY_INDEX.md）

| 服务 | 变量 | 来源 |
|---|---|---|
| DeepSeek | DEEPSEEK_KEY | ~/.zshrc + ~/.claude/settings.json |
| 百度 OCR | BAIDU_OCR_API_KEY / BAIDU_OCR_SECRET_KEY | ~/.zshrc |
| ❌ BAOSI | 已取消 | — |

## 🚧 禁区

- `~/.claude/projects/see-mvp-rag/`：只读不写
- 任何生产部署：先确认有 Grace 拍板证据

## 🔧 工程规则

- Python: `python3` 命令，禁止 venv 假环境
- Bash 脚本: 默认 bash，不用 zsh-only 语法
- Git: main 分支 protected，feature 分支 → PR
- 测试: 每个新模块必须有 `if __name__ == "__main__"` 的 smoke test

## 📐 白板格式铁律（2026-07-05 新增）

所有新增段**必须**用以下格式开头：

```markdown
## YYYY-MM-DDTHH:MM [Agent→Agent] 标题

正文...

## YYYY-MM-DDTHH:MM [Codex→Claude] 完成 - <commit hash>
- 做了什么：...
- 测试：...
```

**反例**（违规格式）：
- ❌ `## 2026-07-04 Codex Re-review — QA Fixes Accepted`（无时分）
- ❌ `## 2026-07-05 Claude: All Keys Configured`（无冒号规范）

**强制命令**（写白板时）：
```bash
TS=$(date +%Y-%m-%dT%H:%M)
TASK="..."
printf "\n## $TS [Claude→Codex] $TASK\n\n" > /tmp/wb.new
cat AGENT_WHITEBOARD.md >> /tmp/wb.new
mv /tmp/wb.new AGENT_WHITEBOARD.md
```

## 🔧 Claude 专属操作规范（2026-07-08 新增）

### 1. CODE_REVIEW_FIXES.md 阅读规则

文件中 1-1574 行是已闭环的历史记录，**从 1575 行开始读**即可。每次用户说「读一下 Code Review Fixes」时，只读 1575 行以后的部分。

### 2. 修复 → 文档 → 同步三步走

每次修完代码后，必须完成以下步骤：

```
1. 修复代码文件（server.py / index.html / talent.html 等）
2. 更新 CODE_REVIEW_FIXES.md（勾选 [x]、更新验证表、更新汇总）
3. 同步到 Desktop 的 3 个位置：
   - ~/Desktop/see-mvp/
   - ~/Desktop/GitHub代码/see-mvp/
   - ~/Desktop/CODE_REVIEW_FIXES.md
```

### 3. GitHub 上传铁律

**所有 `git push` 必须在 Grace 明确确认后才能执行。** 任务完成后先列出待推送的 commits 和变更摘要，等待 Grace 回复确认再 push。参见 `memory/github-upload-requires-approval.md`。

### 4. 权威源

- 源代码权威位置：`~/.claude/projects/see-mvp/`
- CODE_REVIEW_FIXES.md 以 `~/Desktop/GitHub代码/see-mvp/` 中的为最新版本（Grace 可能直接编辑）
- GitHub 仓库：`git@github.com:gracewang3051-web/see-mvp.git`
