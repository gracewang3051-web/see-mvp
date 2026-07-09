#!/bin/bash
# 服务器执行此脚本：bash fix_conflict_and_deploy.sh

cd ~/see-mvp

# 1. 停服务
kill 13624
sleep 1

# 2. 备份生产适配的 3 个文件
cp engine/rules.py /tmp/rules.py.bak
cp server.py /tmp/server.py.bak
cp talent.html /tmp/talent.html.bak

# 3. 拉取 GitHub 最新代码
git fetch origin main
git reset --hard origin/main

# 4. 覆盖回生产适配
cp /tmp/rules.py.bak engine/rules.py
cp /tmp/server.py.bak server.py
cp /tmp/talent.html.bak talent.html

# 5. 提交 + 重启
git add engine/rules.py server.py talent.html
git commit -m "fix: 生产适配 — deepseek-v4-pro模型 + Wsc矩阵补全 + 调试面板V3 + 脱敏"
nohup python3 server.py > /dev/null 2>&1 &

echo "done. server restarted."
