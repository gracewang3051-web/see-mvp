#!/usr/bin/env bash
set -euo pipefail

WHITEBOARD="${1:?whiteboard path required}"
shift

if [ "$#" -eq 0 ]; then
  echo "usage: $0 WHITEBOARD TARGET_PANE [TARGET_PANE...]" >&2
  exit 2
fi

mtime() {
  stat -f %m "$WHITEBOARD" 2>/dev/null || stat -c %Y "$WHITEBOARD"
}

last="$(mtime)"

while true; do
  sleep 3
  now="$(mtime)"
  if [ "$now" != "$last" ]; then
    last="$now"
    stamp="$(date '+%H:%M:%S')"
    for target in "$@"; do
      tmux send-keys -t "$target" -- "[whiteboard $stamp] AGENT_WHITEBOARD.md updated. Please read it before continuing." Enter
    done
  fi
done
