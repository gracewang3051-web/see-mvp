#!/bin/bash
# archive-whiteboard.sh
# 36h 自动归档脚本（路线 A 新格式版）
# 触发：launchd 每 6h
# 日志由 launchd plist 的 StandardOutPath / StandardErrorPath 接管

set -euo pipefail

WB="$HOME/.claude/projects/see-mvp/AGENT_WHITEBOARD.md"
PROG="$HOME/.claude/projects/see-mvp/PROGRESS.md"

if [ ! -f "$WB" ]; then
  echo "[archive] $(date '+%F %T') $WB not found, skipping"
  exit 0
fi

python3 -c "
import re, os, time, datetime

wb_path = '$WB'
prog_path = '$PROG'

with open(wb_path) as f:
    wb_text = f.read()

if not wb_text.strip():
    print('[archive] whiteboard empty, nothing to do')
    exit(0)

cutoff_epoch = time.time() - 36 * 3600
now_ts = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M')
cutoff_str = datetime.datetime.fromtimestamp(cutoff_epoch).strftime('%Y-%m-%dT%H:%M')

# Split on ## YYYY-MM-DD or ## YYYY-MM-DDTHH:MM
segments = re.split(r'(?=^## (?:\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2})? ))', wb_text, flags=re.MULTILINE)

archive_segs = []
keep_segs = []

for s in segments:
    s_stripped = s.strip()
    if not s_stripped:
        continue

    m = re.match(r'## (\d{4}-\d{2}-\d{2})', s_stripped)
    if not m:
        keep_segs.append(s)
        continue

    date_str = m.group(1)
    m2 = re.match(r'## (\d{4}-\d{2}-\d{2}T\d{2}:\d{2})', s_stripped)
    if m2:
        ts = datetime.datetime.strptime(m2.group(1), '%Y-%m-%dT%H:%M').timestamp()
    else:
        ts = datetime.datetime.strptime(date_str, '%Y-%m-%d').timestamp()

    first_line = s_stripped.split(chr(10))[0]
    is_completed = '[Codex→Claude]' in first_line and ' 完成' in first_line

    if ts < cutoff_epoch and not is_completed:
        archive_segs.append(s_stripped)
    else:
        keep_segs.append(s)

if archive_segs:
    archive_block = '\n\n---\n\n'.join(archive_segs)
    archive_entry = f'''
## {now_ts} [笨笨·自动归档] 36h 未完成任务

> 来源：AGENT_WHITEBOARD.md 自动检测
> 段数：{len(archive_segs)} 段
> 阈值：36h（{cutoff_str} 前）
> 条件：无 [Codex→Claude] 完成标记

{archive_block}
'''
    with open(prog_path, 'a') as f:
        f.write(archive_entry)

    with open(wb_path, 'w') as f:
        f.write(''.join(keep_segs))

    print(f'[archive] archived {len(archive_segs)} segments, kept {len(keep_segs)} segments')
else:
    print(f'[archive] no segments to archive, kept {len(keep_segs)} segments')
"