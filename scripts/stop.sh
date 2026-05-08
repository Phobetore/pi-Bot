#!/usr/bin/env bash
# Stop SirrMizan. Sends SIGTERM and waits up to TIMEOUT seconds for a clean
# shutdown (during which the bot flushes state to disk). Falls back to
# SIGKILL only if that fails.
#
# Environment overrides:
#   PIDFILE : pidfile location (default: .run/sirrmizan.pid)
#   TIMEOUT : seconds to wait for graceful exit (default: 15)
set -euo pipefail

cd "$(dirname "$0")/.."
PROJECT_ROOT=$(pwd)

PIDFILE=${PIDFILE:-"$PROJECT_ROOT/.run/sirrmizan.pid"}
TIMEOUT=${TIMEOUT:-15}

if [[ ! -f "$PIDFILE" ]]; then
    echo "no pidfile at $PIDFILE — is SirrMizan running?" >&2
    exit 1
fi

PID=$(cat "$PIDFILE")
if ! kill -0 "$PID" 2>/dev/null; then
    echo "process $PID is not running; removing stale pidfile"
    rm -f "$PIDFILE"
    exit 0
fi

echo "stopping SirrMizan (pid $PID, waiting up to ${TIMEOUT}s)..."
kill -TERM "$PID"

# Poll up to TIMEOUT seconds for the process to vanish.
for ((i = 0; i < TIMEOUT; i++)); do
    if ! kill -0 "$PID" 2>/dev/null; then
        rm -f "$PIDFILE"
        echo "SirrMizan stopped cleanly"
        exit 0
    fi
    sleep 1
done

echo "process did not stop within ${TIMEOUT}s; sending SIGKILL" >&2
kill -KILL "$PID" 2>/dev/null || true
rm -f "$PIDFILE"
exit 0
