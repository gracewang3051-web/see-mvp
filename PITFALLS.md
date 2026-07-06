# PITFALLS · SEE MVP

## 2026-07-05 [P001] macOS 辅助功能权限拒 Codex 写 .env
- **坑**：Codex 试写 `.env.baidu_ocr` 被系统拒
- **修复**：改写到 ~/.zshrc export，避免文件权限问题
- **教训**：本机 .env 文件类操作要走 shell rc 或 settings.json，不直接 .env

## 2026-07-05 [P002] DEEPSEEK_KEY 变量名混乱
- **坑**：server.py 读 `DEEPSEEK_KEY`，settings.json 只设了 `ANTHROPIC_AUTH_TOKEN`，靠 tmux session 手动 export 同值才跑通
- **修复**：双写 DEEPSEEK_KEY 到 zshrc + settings.json env
- **教训**：变量名要全链路一致，命名约定写进 AGENTS.md

## 2026-07-05 [P003] 嵌套 server.py 副本导致路径混乱
- **坑**：`see-mvp/` 目录内有 `see-mvp/server.py` 副本，与根 `server.py` 存在代码差异，导致排查时不知道该修哪个
- **修复**：通过白板标注根目录文件为权威副本
- **教训**：任何嵌套副本必须标注 sync 状态，或由项目规范禁止

## YYYY-MM-DD [Pxxx] 模板
- **坑**：...
- **修复**：...
- **教训**：...
