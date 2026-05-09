# Rebuild from scratch

Procedure for standing the bot back up on a fresh VPS. Use this after a
total VPS loss (data centre fire, cloud account compromise, accidental
`rm -rf /`) or when migrating to a new host.

Estimated time: **45 minutes**, end to end, with the artefacts below
ready.

## Prerequisites

Have these on hand before starting:

- A fresh Debian 12 VPS with root SSH access (password or initial key
  from the provider).
- The bot's Discord token (Developer Portal → SirrDice → Bot tab → Reset
  Token if you don't have it any more).
- Most recent state-files backup (`sirrmizan-data-YYYYMMDD.tar.gz`).
  Without offsite backups this means the latest local
  `/root/backups/*.tar.gz` from the dying VPS — copy it before the
  machine goes; from a new machine you can only start fresh.
- The CI-deploy SSH key (`~/.ssh/sirrmizan_ci`). If you regenerated it,
  the new public half goes in step 9 and the private half goes in
  GitHub Secrets `DEPLOY_SSH_KEY`.
- Discord webhook URL for alerting.

Throughout this doc, replace `vps.example.com` with the new host name
and `1.2.3.4` with its public IP.

## 1. Provision the VPS

Pick Debian 12 (Bookworm), at least 1 GB RAM and 20 GB disk. The bot
itself uses ~50 MB RAM but apt history, logs, and backups take space.

Note the root login the provider gives you. SSH in once to confirm
access:
```
ssh root@1.2.3.4
```

## 2. Base system

```
apt update && apt full-upgrade -y
apt install -y python3 python3-venv python3-pip git curl ufw fail2ban \
                logwatch unattended-upgrades
```

Time sync — already on most cloud images, but verify:
```
timedatectl status | grep "synchronized: yes"
```

## 3. Firewall + fail2ban

```
ufw default deny incoming
ufw default allow outgoing
ufw limit 22/tcp comment SSH
ufw --force enable

cat > /etc/fail2ban/jail.d/sshd.local <<'EOF'
[sshd]
enabled = true
port = ssh
backend = systemd
maxretry = 3
findtime = 10m
bantime = 1h
EOF
systemctl enable --now fail2ban
```

Auto-reboot for kernel patches:
```
cat > /etc/apt/apt.conf.d/52unattended-reboots <<'EOF'
Unattended-Upgrade::Automatic-Reboot "true";
Unattended-Upgrade::Automatic-Reboot-Time "04:00";
EOF
```

## 4. SSH hardening

Add your interactive key to `/root/.ssh/authorized_keys`. Then in
`/etc/ssh/sshd_config.d/99-hardening.conf`:

```
KexAlgorithms curve25519-sha256,curve25519-sha256@libssh.org
Ciphers chacha20-poly1305@openssh.com,aes256-gcm@openssh.com,aes128-gcm@openssh.com
MACs hmac-sha2-512-etm@openssh.com,hmac-sha2-256-etm@openssh.com
HostKeyAlgorithms ssh-ed25519,rsa-sha2-512,rsa-sha2-256
PasswordAuthentication no
PermitRootLogin prohibit-password
MaxAuthTries 3
LoginGraceTime 30s
ClientAliveInterval 300
ClientAliveCountMax 2
```

```
sshd -t && systemctl reload ssh
```

Disable LLMNR/mDNS (cloud providers usually don't need them):
```
mkdir -p /etc/systemd/resolved.conf.d
cat > /etc/systemd/resolved.conf.d/no-llmnr.conf <<'EOF'
[Resolve]
LLMNR=no
MulticastDNS=no
EOF
systemctl restart systemd-resolved
```

## 5. Service account

```
useradd -m -s /bin/bash botdiscord
```

Sudoers entry — the deploy SSH key needs to call three `systemctl`
verbs, nothing else:
```
cat > /etc/sudoers.d/botdiscord-deploy <<'EOF'
Defaults:botdiscord !use_pty
botdiscord ALL=(root) NOPASSWD: /usr/bin/systemctl restart discordbot, /usr/bin/systemctl is-active discordbot, /usr/bin/systemctl status discordbot
EOF
chmod 440 /etc/sudoers.d/botdiscord-deploy
visudo -cf /etc/sudoers.d/botdiscord-deploy
```

## 6. Bot code

As `botdiscord`:
```
sudo -u botdiscord -H bash -c '
    cd ~
    git clone https://github.com/Phobetore/pi-Bot.git SirrMizan
    cd SirrMizan
    python3 -m venv .venv
    .venv/bin/pip install --upgrade pip
    .venv/bin/pip install --require-hashes -r requirements.txt
    mkdir -p data logs
    chmod 700 data logs
'
```

Drop the `.env` in (mode 600, owned by botdiscord):
```
cat > /home/botdiscord/SirrMizan/.env <<EOF
SIRRMIZAN_TOKEN=PUT_THE_TOKEN_HERE
SIRRMIZAN_DEFAULT_PREFIX=!
EOF
chown botdiscord:botdiscord /home/botdiscord/SirrMizan/.env
chmod 600 /home/botdiscord/SirrMizan/.env
```

Restore the state files if you have a backup; otherwise skip — the bot
will start with empty state:
```
tar -xzf /path/to/sirrmizan-data-YYYYMMDD.tar.gz \
    -C /home/botdiscord/SirrMizan/
chown -R botdiscord:botdiscord /home/botdiscord/SirrMizan/data
```

## 7. systemd service

```
mkdir -p /etc/systemd/system/discordbot.service.d
cat > /etc/systemd/system/discordbot.service <<'EOF'
[Unit]
Description=SirrMizan Discord dice rolling bot
After=network-online.target
Wants=network-online.target
StartLimitIntervalSec=60
StartLimitBurst=5

[Service]
Type=simple
User=botdiscord
Group=botdiscord
WorkingDirectory=/home/botdiscord/SirrMizan
EnvironmentFile=/home/botdiscord/SirrMizan/.env
ExecStart=/home/botdiscord/SirrMizan/.venv/bin/python -m sirrmizan
Restart=on-failure
RestartSec=5s
TimeoutStopSec=30

NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictNamespaces=true
LockPersonality=true
RestrictRealtime=true
ReadWritePaths=/home/botdiscord/SirrMizan/data /home/botdiscord/SirrMizan/logs

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/discordbot.service.d/memory.conf <<'EOF'
[Service]
MemoryMax=512M
EOF

systemctl daemon-reload
systemctl enable --now discordbot
sleep 5
systemctl is-active discordbot
journalctl -u discordbot -n 20 --no-pager
```

You should see `Loaded extension sirrmizan.cogs.dice/help/settings` and
`Connected as SirrDice#0679`.

## 8. Monitoring scripts

Webhook URL:
```
mkdir -p /etc/sirrmizan
echo 'https://discord.com/api/webhooks/...' > /etc/sirrmizan/webhook.url
chmod 600 /etc/sirrmizan/webhook.url
```

Tools venv for `pip-audit`:
```
python3 -m venv /opt/sirrmizan-tools
/opt/sirrmizan-tools/bin/pip install --upgrade pip pip-audit
```

Copy the four scripts from the repo's `scripts/` directory (or your own
copy) to `/usr/local/bin/`. They are:

- `sirrmizan-heartbeat-check.sh` — every minute, restarts on stuck bot
- `sirrmizan-backup.sh` — daily, tarballs `data/` to `/root/backups`
- `sirrmizan-logwatch.sh` — weekly, posts logwatch report to Discord
- `sirrmizan-pip-audit.sh` — weekly, alerts on new CVEs in deps
- `sirrmizan-disk-check.sh` — daily, alerts at >80% disk

```
chmod 700 /usr/local/bin/sirrmizan-*.sh
```

Cron (root):
```
crontab -e
```
```
* * * * *   /usr/local/bin/sirrmizan-heartbeat-check.sh
30 3 * * *  /usr/local/bin/sirrmizan-backup.sh
0 7 * * *   /usr/local/bin/sirrmizan-disk-check.sh
0 8 * * 1   /usr/local/bin/sirrmizan-logwatch.sh
0 9 * * 1   /usr/local/bin/sirrmizan-pip-audit.sh
```

## 9. CI deploy key (forced-command)

The GitHub Actions deploy uses an SSH key that can only execute the
deploy script.

```
sudo -u botdiscord -H mkdir -p /home/botdiscord/.ssh
sudo -u botdiscord -H chmod 700 /home/botdiscord/.ssh

cat > /home/botdiscord/.ssh/authorized_keys <<EOF
command="/home/botdiscord/SirrMizan/scripts/ci_deploy.sh",no-port-forwarding,no-X11-forwarding,no-agent-forwarding,no-user-rc PUBLIC_KEY_HERE
EOF
chown botdiscord:botdiscord /home/botdiscord/.ssh/authorized_keys
chmod 600 /home/botdiscord/.ssh/authorized_keys
chmod +x /home/botdiscord/SirrMizan/scripts/ci_deploy.sh
```

If you regenerated the keypair, also update the matching GitHub secrets
on https://github.com/Phobetore/pi-Bot/settings/secrets/actions:
- `DEPLOY_HOST` — new VPS hostname
- `DEPLOY_SSH_KEY` — private half of the new key
- `DEPLOY_KNOWN_HOSTS` — `ssh-keyscan -t ed25519,rsa,ecdsa NEW_HOST`

## 10. Validation checklist

Run through these, top to bottom:

1. `systemctl is-active discordbot` → `active`
2. `journalctl -u discordbot -n 30 --no-pager` shows `Connected as ...`
3. `stat /home/botdiscord/SirrMizan/data/heartbeat` — modified within
   the last 30 s
4. From your laptop, run a manual deploy with the CI key — the script
   should exit `[deploy] already at <SHA> — nothing to do`:
   ```
   ssh -i ~/.ssh/sirrmizan_ci botdiscord@vps.example.com
   ```
5. `crontab -l` shows the five `sirrmizan-*.sh` lines.
6. Trigger a webhook test:
   ```
   curl -fsS --max-time 10 -X POST "$(cat /etc/sirrmizan/webhook.url)" \
       -H "Content-Type: application/json" \
       -d '{"content":"🧪 rebuild validation ping"}'
   ```
   Confirm the message appears in your Discord channel.
7. Send `!r 1d20` in a server where the bot is — it should respond.
8. `ufw status` → only port 22 listed, `default: deny (incoming)`.
9. `fail2ban-client status sshd` returns OK.

If any of the above fails, the corresponding section above is the place
to start debugging — they map one-to-one.

## Common mismatches when migrating

- **Hostname change**: GitHub secret `DEPLOY_HOST` must be updated, and
  `DEPLOY_KNOWN_HOSTS` must be regenerated against the new host. Without
  the latter, CI deploys fail with "Host key verification failed".
- **Different distro**: paths to `systemctl`, `node`, etc. may move.
  The sudoers entry uses absolute paths. Run `which systemctl` on the
  new host and update if needed.
- **Different Python**: the bot requires Python ≥ 3.11. On older
  Debian/Ubuntu, install via deadsnakes or use `pyenv`.
- **Backups gap**: if you don't have offsite backups, the migration
  starts the bot with empty state. Users will see their colour, prefs,
  and stats reset. Mention this in your server before switching DNS.
