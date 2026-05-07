#!/usr/bin/env bash
# Print pi-Bot status. Exit codes: 0 running, 1 stopped, 2 stale pidfile.
set -euo pipefail

cd "$(dirname "$0")/.."
PIDFILE=${PIDFILE:-".run/pi-bot.pid"}

if [[ ! -f "$PIDFILE" ]]; then
    echo "pi-Bot is not running"
    exit 1
fi

PID=$(cat "$PIDFILE")
if kill -0 "$PID" 2>/dev/null; then
    echo "pi-Bot is running (pid $PID)"
    exit 0
fi

echo "pi-Bot is not running (stale pidfile: $PIDFILE)"
exit 2
