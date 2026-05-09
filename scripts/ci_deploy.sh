#!/usr/bin/env bash
# CI deploy script — invoked via SSH forced-command from GitHub Actions.
#
# This script lives in the repo so CI changes are reviewable, but the
# *executed* copy is the one already on the server (the forced-command in
# ~botdiscord/.ssh/authorized_keys points at the on-disk path). To roll
# out a change to the deploy script itself, push it AND copy it manually
# the first time (the script will pull subsequent versions itself).
#
# Pulls origin/prod, updates deps, sanity-checks the import, restarts the
# service, and verifies that systemd considers it active.
set -euo pipefail

cd /home/botdiscord/SirrMizan

echo "[deploy] fetching prod..."
git fetch --quiet origin prod

TARGET=$(git rev-parse origin/prod)
CURRENT=$(git rev-parse HEAD)

if [[ "$CURRENT" == "$TARGET" ]]; then
    echo "[deploy] already at $TARGET — nothing to do"
    exit 0
fi

echo "[deploy] updating: $CURRENT -> $TARGET"
git reset --hard origin/prod

echo "[deploy] installing deps..."
.venv/bin/pip install --require-hashes -r requirements.txt --quiet

echo "[deploy] sanity-check import..."
.venv/bin/python -c 'import sirrmizan; print("  module OK, version=" + sirrmizan.__version__)'

echo "[deploy] restarting service..."
sudo /usr/bin/systemctl restart discordbot

sleep 5

if sudo /usr/bin/systemctl is-active discordbot >/dev/null 2>&1; then
    echo "[deploy] success — running $TARGET"
else
    echo "[deploy] FAILURE — service is not active" >&2
    sudo /usr/bin/systemctl status discordbot >&2 || true
    exit 1
fi
