#!/usr/bin/env bash
# AbuseIPDB integration. Two sub-commands:
#
#   lookup <ip>           print enriched JSON for one IP (used by ops / reports)
#   enrich <ip> <jail>    called by fail2ban actionban: appends an event line
#                         to /var/lib/sirrmizan/attack-log.jsonl and posts a
#                         high-priority Discord alert if confidence ≥ 90, if
#                         the IP belongs to a country we haven't seen before,
#                         or if the IP is in the operator's known-good list.
#
# Designed to no-op cleanly when /etc/sirrmizan/abuseipdb.key is absent so
# the rest of the security stack still works without a paid lookup.
set -euo pipefail

API_KEY_FILE=/etc/sirrmizan/abuseipdb.key
WEBHOOK_FILE=/etc/sirrmizan/webhook.url
STATE_DIR=/var/lib/sirrmizan
ATTACK_LOG="${STATE_DIR}/attack-log.jsonl"
SEEN_COUNTRIES="${STATE_DIR}/seen-countries.txt"
KNOWN_GOOD_IPS="${STATE_DIR}/known-good-ips.txt"
USER_TAG="<@386593552789929987>"

HIGH_SCORE_THRESHOLD=90

mkdir -p "${STATE_DIR}"
chmod 700 "${STATE_DIR}"
touch "${ATTACK_LOG}" "${SEEN_COUNTRIES}" "${KNOWN_GOOD_IPS}"
chmod 600 "${ATTACK_LOG}"

api_lookup() {
    local ip="$1"
    if [ ! -r "${API_KEY_FILE}" ]; then
        printf '{"ipAddress":"%s","skipped":"no_api_key"}\n' "${ip}"
        return 0
    fi
    local key
    key=$(cat "${API_KEY_FILE}")
    curl -fsS --max-time 8 \
        -G "https://api.abuseipdb.com/api/v2/check" \
        --data-urlencode "ipAddress=${ip}" \
        --data-urlencode "maxAgeInDays=90" \
        -H "Key: ${key}" \
        -H "Accept: application/json" \
    | python3 -c '
import json, sys
try:
    payload = json.load(sys.stdin).get("data", {})
except Exception as exc:  # pragma: no cover
    print(json.dumps({"error": str(exc)}))
    sys.exit(0)
out = {
    "ipAddress":         payload.get("ipAddress"),
    "abuseConfidence":   payload.get("abuseConfidenceScore", 0),
    "countryCode":       payload.get("countryCode") or "?",
    "isp":               payload.get("isp") or "?",
    "domain":            payload.get("domain") or "",
    "usageType":         payload.get("usageType") or "",
    "totalReports":      payload.get("totalReports", 0),
    "lastReportedAt":    payload.get("lastReportedAt") or "",
    "isPublic":          payload.get("isPublic", True),
    "isTor":             payload.get("isTor", False),
}
print(json.dumps(out))
'
}

post_alert() {
    local content="$1"
    if [ ! -r "${WEBHOOK_FILE}" ]; then
        return 0
    fi
    local url
    url=$(cat "${WEBHOOK_FILE}")
    local payload
    payload=$(python3 -c 'import json,sys; print(json.dumps({"content": sys.argv[1]}))' "${content}")
    curl -fsS --max-time 8 -X POST "${url}" \
        -H "Content-Type: application/json" \
        --data "${payload}" >/dev/null || true
}

case "${1:-}" in
    lookup)
        api_lookup "${2:?ip required}"
        ;;
    enrich)
        ip="${2:?ip required}"
        jail="${3:?jail required}"
        meta=$(api_lookup "${ip}")
        ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
        # Append one JSONL line: timestamp, jail, and the API metadata merged.
        printf '%s\n' "${meta}" | TS="${ts}" JAIL="${jail}" ATTACK_LOG="${ATTACK_LOG}" python3 -c '
import json, sys, os
meta = json.loads(sys.stdin.read() or "{}")
event = {"ts": os.environ["TS"], "jail": os.environ["JAIL"]}
event.update(meta)
with open(os.environ["ATTACK_LOG"], "a", encoding="utf-8") as f:
    f.write(json.dumps(event, sort_keys=True) + "\n")
print(event.get("abuseConfidence", 0))
print(event.get("countryCode", "?"))
print(event.get("isp", "?"))
print(event.get("totalReports", 0))
' > /tmp/sirrmizan-abuseipdb.$$
        confidence=$(sed -n '1p' /tmp/sirrmizan-abuseipdb.$$)
        country=$(sed -n '2p' /tmp/sirrmizan-abuseipdb.$$)
        isp=$(sed -n '3p' /tmp/sirrmizan-abuseipdb.$$)
        reports=$(sed -n '4p' /tmp/sirrmizan-abuseipdb.$$)
        rm -f /tmp/sirrmizan-abuseipdb.$$

        # Country first-seen tracking.
        new_country=0
        if [ -n "${country}" ] && [ "${country}" != "?" ]; then
            if ! grep -qx "${country}" "${SEEN_COUNTRIES}" 2>/dev/null; then
                echo "${country}" >> "${SEEN_COUNTRIES}"
                new_country=1
            fi
        fi

        # Self-ban detection: did fail2ban just ban an IP we use ourselves?
        self_banned=0
        if grep -qx "${ip}" "${KNOWN_GOOD_IPS}" 2>/dev/null; then
            self_banned=1
        fi

        # Alerts. Only fire on conditions worth a Discord ping.
        confidence_int=${confidence:-0}
        if [ "${self_banned}" -eq 1 ]; then
            post_alert "🛑 ${USER_TAG} fail2ban a banni ${ip} qui apparaît dans known-good-ips (faux positif probable, jail=${jail}) — vérifier /var/lib/sirrmizan/known-good-ips.txt"
        elif [ "${confidence_int}" -ge "${HIGH_SCORE_THRESHOLD}" ]; then
            post_alert "🚨 IP très malveillante bannie : \`${ip}\` (${country}, ${isp}) — score AbuseIPDB ${confidence_int}/100, ${reports} signalements, jail=${jail}"
        elif [ "${new_country}" -eq 1 ]; then
            post_alert "🌍 Nouveau pays attaquant détecté : \`${country}\` via \`${ip}\` (${isp}) — score ${confidence_int}/100, jail=${jail}"
        fi
        ;;
    *)
        echo "usage: $0 {lookup|enrich} <ip> [jail]" >&2
        exit 2
        ;;
esac
