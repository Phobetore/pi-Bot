#!/usr/bin/env bash
# Restart SirrMizan. Tolerates a not-currently-running bot (start anyway).
set -euo pipefail

cd "$(dirname "$0")/.."
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)

if [[ -f .run/sirrmizan.pid ]]; then
    "$SCRIPT_DIR/stop.sh" || true
fi
"$SCRIPT_DIR/start.sh"
