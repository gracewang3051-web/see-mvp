# DECISIONS · SEE MVP

## 2026-07-05 [D001] DeepSeek KEY 不持久化根因
- **背景**：tmux Claude 重启后 DEEPSEEK_KEY 找不到
- **选项**：
  - A. 写到 ~/.zshrc
  - B. 写到 ~/.claude/settings.json env 块
  - C. 写到 .env（被 macOS 辅助功能权限拒）
- **结论**：A + B 双写（zshrc 给 shell，settings.json 给 Claude Code 子进程）
- **执行**：笨笨 2026-07-05 10:48 完成

## 2026-07-05 [D002] BAOSI_KEY 取消
- **背景**：baosi 代理不可用
- **结论**：彻底清理，不再申请
- **执行**：笨笨 2026-07-05 10:58 清理 zshrc / settings.json / KEY_INDEX

## 2026-07-05 [D003] SEE MVP 项目级 Agent 协作体系方案选择
- **背景**：需要更规范的 Agent 间协作流程（Claude ↔ Codex ↔ Grace），提升跨 session 连续性
- **选项**：
  - A. 全自动方案：launchd + tmux watcher + 白板 monitor
  - B. 双层 + AGENTS.md 铁律：只做 .md 铁律文件，launchd 自动化留下一步
  - C. 不做变更：保持现状
- **结论**：B — 双层 + AGENTS.md 铁律
- **执行**：笨笨 2026-07-05 11:33 创建 AGENTS.md / KEY_INDEX.md / PROGRESS.md / DECISIONS.md / PITFALLS.md

## YYYY-MM-DD [Dxxx] 模板
- **背景**：...
- **选项**：
  - A. ...
  - B. ...
- **结论**：...
- **执行**：...
