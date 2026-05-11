#!/usr/bin/env bash
# Daily refresh of the `sirrmizan-blocklist` ipset from public threat
# feeds. Loads:
#   - Spamhaus DROP   (netblocks fully under spammer control)
#   - Spamhaus EDROP  (hijacked netblocks, extension of DROP)
#   - AbuseIPDB blacklist (top abusers, requires API key; skipped if absent)
#
# All entries land in the same hash:net ipset. iptables DROP'ed at the
# top of the INPUT chain by sirrmizan-ipset-restore.service. After the
# fact we save the set to disk so it survives reboot.
#
# Designed to keep the previous contents if any feed fails — never
# leave the box un-blocklisted because a CDN burped.
set -uo pipefail

WEBHOOK_FILE=/etc/sirrmizan/webhook.url
ABUSEIPDB_KEY_FILE=/etc/sirrmizan/abuseipdb.key
USER_TAG="<@386593552789929987>"

SET=sirrmizan-blocklist
TMPDIR=$(mktemp -d)
trap 'rm -rf "${TMPDIR}"' EXIT

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

# --- Spamhaus DROP + EDROP (public, no key) ----------------------------------
fetch_spamhaus() {
    local out="${TMPDIR}/spamhaus.txt"
    : > "${out}"
    for url in https://www.spamhaus.org/drop/drop.txt \
               https://www.spamhaus.org/drop/edrop.txt; do
        if ! curl -fsS --max-time 20 "${url}" >> "${out}.raw"; then
            return 1
        fi
    done
    # Strip comments (lines starting with ;) and SBL refs.
    awk '/^[0-9]/ { print $1 }' "${out}.raw" > "${out}"
    [ -s "${out}" ] && echo "${out}"
}

# --- AbuseIPDB blacklist (requires paid? — free tier gives 10k/day) ----------
fetch_abuseipdb() {
    if [ ! -r "${ABUSEIPDB_KEY_FILE}" ]; then
        return 1
    fi
    local out="${TMPDIR}/abuseipdb.txt"
    local key
    key=$(cat "${ABUSEIPDB_KEY_FILE}")
    curl -fsS --max-time 20 \
        -G "https://api.abuseipdb.com/api/v2/blacklist" \
        --data-urlencode "confidenceMinimum=90" \
        --data-urlencode "limit=10000" \
        -H "Key: ${key}" \
        -H "Accept: text/plain" \
        > "${out}" || return 1
    [ -s "${out}" ] && echo "${out}"
}

# --- Build new set in a temp set, then atomically swap ----------------------
SCRATCH="${SET}-scratch"
ipset destroy "${SCRATCH}" 2>/dev/null || true
ipset create  "${SCRATCH}" hash:net

added=0
sources=""

if spamhaus_file=$(fetch_spamhaus); then
    while IFS= read -r net; do
        [ -z "${net}" ] && continue
        ipset add "${SCRATCH}" "${net}" -exist && added=$((added+1)) || true
    done < "${spamhaus_file}"
    sources+="spamhaus "
fi

if abuseipdb_file=$(fetch_abuseipdb); then
    while IFS= read -r ip; do
        [ -z "${ip}" ] && continue
        # Coerce single IPs into /32 for hash:net.
        case "${ip}" in
            */*) entry="${ip}" ;;
            *)   entry="${ip}/32" ;;
        esac
        ipset add "${SCRATCH}" "${entry}" -exist && added=$((added+1)) || true
    done < "${abuseipdb_file}"
    sources+="abuseipdb "
fi

if [ "${added}" -eq 0 ]; then
    # All feeds failed. Keep current set untouched.
    ipset destroy "${SCRATCH}" 2>/dev/null || true
    post_alert "⚠️ ${USER_TAG} threat-feed update échouée — toutes les sources injoignables, blocklist conservée telle quelle"
    exit 1
fi

# Atomic swap so iptables never sees an empty set.
ipset swap "${SCRATCH}" "${SET}"
ipset destroy "${SCRATCH}"

/usr/local/bin/sirrmizan-ipset-save.sh "${SET}"

count=$(ipset list "${SET}" | grep -c '^[0-9]')
echo "threat-feed: ${count} entries, sources=${sources}"
