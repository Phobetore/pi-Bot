#!/usr/bin/env bash
# Idempotent one-shot installer for the security stack added on top of
# the base SirrMizan VPS. Re-runnable: every step checks current state
# and exits 0 if already configured. Run as root.
#
# What this does:
#   1. Installs apt deps (ipset)
#   2. Drops the helper scripts into /usr/local/bin
#   3. Installs fail2ban action.d + jail.d snippets
#   4. Installs the ipset-restore systemd unit + enables it
#   5. Creates /var/lib/sirrmizan/ + /etc/sirrmizan/ with safe perms
#   6. Reloads fail2ban
#   7. Schedules new cron entries (additive to whatever's already there)
set -euo pipefail

REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd)
SCRIPTS="${REPO_ROOT}/scripts"
ETC_TEMPLATES="${REPO_ROOT}/etc"

echo "== [1/7] apt deps =="
if ! dpkg -s ipset >/dev/null 2>&1; then
    apt-get update
    apt-get install -y ipset
fi

echo "== [2/7] install helper scripts =="
for s in sirrmizan-ipset-restore.sh \
         sirrmizan-ipset-save.sh \
         sirrmizan-abuseipdb.sh \
         sirrmizan-threatfeed-update.sh \
         sirrmizan-security-anomaly.sh \
         sirrmizan-security-report.py; do
    install -m 700 -o root -g root "${SCRIPTS}/${s}" "/usr/local/bin/${s}"
done

echo "== [3/7] fail2ban config =="
install -m 644 -o root -g root \
    "${ETC_TEMPLATES}/fail2ban/action.d/abuseipdb-enrich.conf" \
    /etc/fail2ban/action.d/abuseipdb-enrich.conf
install -m 644 -o root -g root \
    "${ETC_TEMPLATES}/fail2ban/action.d/permaban-ipset.conf" \
    /etc/fail2ban/action.d/permaban-ipset.conf
install -m 644 -o root -g root \
    "${ETC_TEMPLATES}/fail2ban/jail.d/recidive.local" \
    /etc/fail2ban/jail.d/recidive.local
install -m 644 -o root -g root \
    "${ETC_TEMPLATES}/fail2ban/jail.d/sshd-enrich.local" \
    /etc/fail2ban/jail.d/sshd-enrich.local

echo "== [4/7] systemd ipset-restore unit =="
install -m 644 -o root -g root \
    "${ETC_TEMPLATES}/systemd/system/sirrmizan-ipset-restore.service" \
    /etc/systemd/system/sirrmizan-ipset-restore.service
systemctl daemon-reload
systemctl enable --now sirrmizan-ipset-restore.service

echo "== [5/7] state directories =="
mkdir -p /var/lib/sirrmizan/ipset \
         /var/lib/sirrmizan/anomaly-cooldown \
         /etc/sirrmizan
chmod 700 /var/lib/sirrmizan /var/lib/sirrmizan/ipset \
          /var/lib/sirrmizan/anomaly-cooldown /etc/sirrmizan
touch /var/lib/sirrmizan/attack-log.jsonl
chmod 600 /var/lib/sirrmizan/attack-log.jsonl
touch /var/lib/sirrmizan/known-good-ips.txt
chmod 600 /var/lib/sirrmizan/known-good-ips.txt
touch /var/lib/sirrmizan/seen-countries.txt
chmod 600 /var/lib/sirrmizan/seen-countries.txt

echo "== [6/7] fail2ban reload =="
systemctl restart fail2ban
sleep 2
fail2ban-client status

echo "== [7/7] cron =="
# Append missing entries. Each line is idempotent via grep -q.
add_cron() {
    local schedule="$1" cmd="$2"
    if ! crontab -l 2>/dev/null | grep -qF "${cmd}"; then
        (crontab -l 2>/dev/null; echo "${schedule} ${cmd}") | crontab -
    fi
}

add_cron "*/5 * * * *" "/usr/local/bin/sirrmizan-security-anomaly.sh"
add_cron "15 4 * * *"  "/usr/local/bin/sirrmizan-threatfeed-update.sh"
add_cron "0 9 * * 1"   "/usr/local/bin/sirrmizan-security-report.py"

echo
echo "Setup complete."
echo
echo "Pour activer l'enrichissement AbuseIPDB, créer /etc/sirrmizan/abuseipdb.key"
echo "(mode 600) contenant votre clé API. Sans la clé, le système fonctionne"
echo "quand même : pas de score sur les bans, threat-feed sans la blacklist"
echo "AbuseIPDB (Spamhaus DROP/EDROP suffit comme baseline)."
