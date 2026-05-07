#!/usr/bin/env bash
# Start pi-Bot in the background and write its PID to a file.
#
# Environment overrides:
#   PYTHON   : python interpreter (default: prefers .venv/bin/python, then python)
#   PIDFILE  : where to write the pid (default: .run/pi-bot.pid)
#   LOGFILE  : where to redirect stdout/stderr (default: logs/console.log)
set -euo pipefail

cd "$(dirname "$0")/.."
PROJECT_ROOT=$(pwd)

PIDFILE=${PIDFILE:-"$PROJECT_ROOT/.run/pi-bot.pid"}
LOGFILE=${LOGFILE:-"$PROJECT_ROOT/logs/console.log"}

mkdir -p "$(dirname "$PIDFILE")" "$(dirname "$LOGFILE")"

# Refuse to start if a previous instance is still alive.
if [[ -f "$PIDFILE" ]]; then
    existing_pid=$(cat "$PIDFILE" 2>/dev/null || true)
    if [[ -n "${existing_pid:-}" ]] && kill -0 "$existing_pid" 2>/dev/null; then
        echo "pi-Bot is already running (pid $existing_pid)" >&2
        exit 1
    fi
    rm -f "$PIDFILE"
fi

# Pick the interpreter: explicit override > local venv > system python.
if [[ -z "${PYTHON:-}" ]]; then
    if [[ -x ".venv/bin/python" ]]; then
        PYTHON=".venv/bin/python"
    else
        PYTHON="python"
    fi
fi

# Detach so the bot survives terminal close. setsid puts it in its own
# session/process group, which makes signal handling on stop predictable.
if command -v setsid >/dev/null 2>&1; then
    setsid "$PYTHON" -m pi_bot </dev/null >>"$LOGFILE" 2>&1 &
else
    nohup "$PYTHON" -m pi_bot </dev/null >>"$LOGFILE" 2>&1 &
fi

echo $! >"$PIDFILE"
sleep 0.3

# Sanity-check that the process is still alive a heartbeat later.
if ! kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
    echo "pi-Bot failed to start — see $LOGFILE" >&2
    rm -f "$PIDFILE"
    exit 1
fi

echo "pi-Bot started (pid $(cat "$PIDFILE"), log: $LOGFILE)"
