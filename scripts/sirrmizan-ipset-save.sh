#!/usr/bin/env bash
# Persist a single ipset to disk. Called from fail2ban actions and
# from the threat-feed updater after they mutate a set, so members
# survive reboot. Cheap (a few KB write) so calling it on every ban
# is fine.
#
# Usage: sirrmizan-ipset-save.sh <set-name>
set -euo pipefail

SET="${1:?set name required}"
SAVE_DIR=/var/lib/sirrmizan/ipset
mkdir -p "${SAVE_DIR}"
chmod 700 "${SAVE_DIR}"

ipset save "${SET}" > "${SAVE_DIR}/${SET}.save.tmp"
mv "${SAVE_DIR}/${SET}.save.tmp" "${SAVE_DIR}/${SET}.save"
chmod 600 "${SAVE_DIR}/${SET}.save"
