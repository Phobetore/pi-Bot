#!/usr/bin/env bash
# Boot-time restore of SirrMizan's two ipsets:
#   sirrmizan-permaban   (hash:ip)  — populated by fail2ban [recidive]
#   sirrmizan-blocklist  (hash:net) — populated by the daily threat-feed cron
# Both are wired into iptables INPUT with a -j DROP rule.
#
# Run as a one-shot systemd unit BEFORE fail2ban (which will add its
# own rules that reference the same set names).
set -euo pipefail

SAVE_DIR=/var/lib/sirrmizan/ipset
mkdir -p "${SAVE_DIR}"
chmod 700 "${SAVE_DIR}"

ensure_set() {
    local name="$1" type="$2"
    if ! ipset list -n "${name}" >/dev/null 2>&1; then
        ipset create "${name}" "${type}" timeout 0
    fi
}

ensure_set sirrmizan-permaban  hash:ip
ensure_set sirrmizan-blocklist hash:net

# Restore content if a save file exists.
for set_name in sirrmizan-permaban sirrmizan-blocklist; do
    save_file="${SAVE_DIR}/${set_name}.save"
    if [ -s "${save_file}" ]; then
        ipset restore -exist < "${save_file}" || true
    fi
done

# Wire the DROP rules in iptables (idempotent: only insert if absent).
ensure_drop_rule() {
    local set_name="$1"
    if ! iptables -C INPUT -m set --match-set "${set_name}" src -j DROP 2>/dev/null; then
        iptables -I INPUT 1 -m set --match-set "${set_name}" src -j DROP
    fi
}

ensure_drop_rule sirrmizan-permaban
ensure_drop_rule sirrmizan-blocklist
