#!/usr/bin/env bash
# Cron-driven anomaly detector. Runs every 5 minutes and posts a
# single Discord alert if it sees a behavior pattern out of the
# ordinary. Single-shot alerts (high-score IP, new country, self-ban)
# are already emitted by sirrmizan-abuseipdb.sh inline with the
# fail2ban actionban — this script catches things that only show up
# when looking at a window:
#
#   - ban-rate spike (>10 bans in 5 minutes)
#   - sshd brute-force burst targeting a single username
#   - one of our known-good IPs has been hammering auth.log
#
# Each pattern emits at most one Discord message per detection, with
# a short cooldown file so we don't paginate ourselves to death when a
# botnet sustains the spike for hours.
set -uo pipefail

WEBHOOK_FILE=/etc/sirrmizan/webhook.url
STATE_DIR=/var/lib/sirrmizan
COOLDOWN_DIR="${STATE_DIR}/anomaly-cooldown"
USER_TAG="<@386593552789929987>"

BAN_SPIKE_THRESHOLD=10            # bans in the last 5 min
USERNAME_BURST_THRESHOLD=20       # failed auth attempts for the same user in 5 min
COOLDOWN_SEC=$((60*30))           # 30 min between identical alerts

mkdir -p "${COOLDOWN_DIR}"
chmod 700 "${COOLDOWN_DIR}"

post_alert() {
    if [ ! -r "${WEBHOOK_FILE}" ]; then
        return 0
    fi
    local url payload
    url=$(cat "${WEBHOOK_FILE}")
    payload=$(python3 -c 'import json,sys; print(json.dumps({"content": sys.argv[1]}))' "$1")
    curl -fsS --max-time 8 -X POST "${url}" \
        -H "Content-Type: application/json" \
        --data "${payload}" >/dev/null || true
}

# True if the named alert is past its cooldown.
cooled_down() {
    local key="$1"
    local file="${COOLDOWN_DIR}/${key}"
    if [ -f "${file}" ]; then
        local last_ts now_ts
        last_ts=$(stat -c %Y "${file}")
        now_ts=$(date +%s)
        if [ $((now_ts - last_ts)) -lt "${COOLDOWN_SEC}" ]; then
            return 1
        fi
    fi
    touch "${file}"
    return 0
}

# --- ban-rate spike ---------------------------------------------------------
ban_count=$(journalctl -u fail2ban.service --since "5 minutes ago" --no-pager 2>/dev/null \
    | grep -cE "NOTICE.*Ban " || true)

if [ "${ban_count}" -gt "${BAN_SPIKE_THRESHOLD}" ]; then
    if cooled_down "ban-spike"; then
        post_alert "📈 ${USER_TAG} pic d'activité fail2ban : ${ban_count} bans en 5 min (seuil ${BAN_SPIKE_THRESHOLD}). Probablement un scan distribué en cours."
    fi
fi

# --- single-username brute-force burst --------------------------------------
top_user_line=$(journalctl -u ssh --since "5 minutes ago" --no-pager 2>/dev/null \
    | grep -oE "(Failed password for|Invalid user) [a-zA-Z0-9._-]+" \
    | awk '{print $NF}' \
    | sort | uniq -c | sort -rn | head -1 || true)

if [ -n "${top_user_line:-}" ]; then
    count=$(echo "${top_user_line}" | awk '{print $1}')
    user=$(echo  "${top_user_line}" | awk '{print $2}')
    if [ "${count:-0}" -gt "${USERNAME_BURST_THRESHOLD}" ]; then
        if cooled_down "user-burst-${user}"; then
            post_alert "🎯 ${USER_TAG} brute-force sur l utilisateur \`${user}\` : ${count} tentatives ratées en 5 min. Vérifier que cet utilisateur n existe pas sur le système (/etc/passwd)."
        fi
    fi
fi

# --- one of our IPs hammering auth.log (account compromise / network NAT) ---
if [ -s "${STATE_DIR}/known-good-ips.txt" ]; then
    while IFS= read -r ip; do
        [ -z "${ip}" ] && continue
        fails=$(journalctl -u ssh --since "5 minutes ago" --no-pager 2>/dev/null \
            | grep -c "Failed password.*from ${ip}" || true)
        if [ "${fails}" -gt 5 ]; then
            if cooled_down "self-fails-${ip}"; then
                post_alert "⚠️ ${USER_TAG} l IP connue \`${ip}\` a ${fails} échecs d auth en 5 min — clé invalide, NAT partagé compromis, ou compte ciblé."
            fi
        fi
    done < "${STATE_DIR}/known-good-ips.txt"
fi

# --- maintain known-good IPs list from successful logins --------------------
# Adds any IP seen in `Accepted publickey` events to the whitelist so
# future false-positive bans get caught by sirrmizan-abuseipdb.sh.
journalctl -u ssh --since "1 hour ago" --no-pager 2>/dev/null \
    | grep -oE "Accepted publickey for [a-z]+ from [0-9a-fA-F.:]+" \
    | awk '{print $NF}' \
    | sort -u \
    | while IFS= read -r ip; do
        if [ -n "${ip}" ] && ! grep -qx "${ip}" "${STATE_DIR}/known-good-ips.txt" 2>/dev/null; then
            echo "${ip}" >> "${STATE_DIR}/known-good-ips.txt"
        fi
    done

exit 0
