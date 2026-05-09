# Runbook

What to do when something goes sideways. Each section starts with
**symptoms** so you can jump straight to the right one.

## Bot does not respond to commands

**Symptom:** `!roll` / `/roll` does nothing in Discord, no error.

1. Check service is active:
   ```
   ssh root@vps.example.com 'systemctl is-active discordbot'
   ```
2. Check the heartbeat file is fresh (mtime should be < 30s ago):
   ```
   ssh root@vps.example.com 'stat /home/botdiscord/SirrMizan/data/heartbeat'
   ```
3. Check the journal for warnings or stack traces:
   ```
   ssh root@vps.example.com 'journalctl -u discordbot -n 50 --no-pager'
   ```
4. Look for `discord.gateway` warnings (gateway latency / heartbeat blocked).
   If present and persistent, the asyncio loop is stuck — `systemctl restart discordbot`.
5. If the bot connects but ignores commands, check that the cogs loaded:
   look for `Loaded extension sirrmizan.cogs.dice` in the journal. Missing →
   the deploy didn't fully succeed; re-run `ci_deploy.sh` manually.

## Deploy fails

**Symptom:** Push to `prod` happens but the server stays on the old commit.

1. Check the GitHub Actions run for `Deploy to production`. Failure
   message usually points at the exact step.
2. Manual deploy from your laptop, equivalent to what CI does:
   ```
   ssh -i ~/.ssh/sirrmizan_ci botdiscord@vps.example.com
   ```
   This SSH triggers the forced-command at the server side
   (`ci_deploy.sh`) and bypasses GitHub Actions entirely.
3. If the script reports `Session is closed`, the bot is in a degraded
   shutdown state — `systemctl restart discordbot` clears it.
4. If pip-install fails with hash mismatch, regenerate
   `requirements.txt`:
   ```
   pip-compile --generate-hashes requirements.in
   ```
   Commit, merge to prod, deploy retries.

## Heartbeat watchdog is spamming alerts

**Symptom:** Discord channel gets repeated `⚠️ heartbeat stale` alerts.

1. The watchdog caps at 3 restarts per hour. If you see a 4th alert, it
   was the escalation message ("manual intervention needed") — the
   watchdog has stopped restarting.
2. SSH and check what's going on:
   ```
   journalctl -u discordbot -n 100 --no-pager
   stat /home/botdiscord/SirrMizan/data/heartbeat
   cat /var/lib/sirrmizan/restart-attempts
   ```
3. If a stuck loop is the culprit, attach `py-spy` (or just `strace`) to
   the python process to see what it's doing.
4. Once the underlying issue is fixed, clear the restart counter so the
   watchdog can resume:
   ```
   ssh root@... '> /var/lib/sirrmizan/restart-attempts'
   ```

## High disk usage

**Symptom:** `💾 VPS disk space (>80% used)` alert in Discord.

1. Find the offender:
   ```
   ssh root@... 'du -h --max-depth=2 / 2>/dev/null | sort -h | tail -20'
   ```
2. Common culprits:
   - `/home/botdiscord/SirrMizan/logs/` — log rotation is set up but
     check `*.log.*` accumulation.
   - `/var/log/journal/` — `journalctl --vacuum-size=200M` will trim it.
   - `/root/backups/` — retention is 14 days; if you see more, the cron
     isn't running.
   - Old kernel images in `/boot` — `apt autoremove` cleans them.

## CVE found by `pip-audit`

**Symptom:** `🔴 pip-audit: vulnerabilities found in SirrMizan deps`.

1. Read the alert: it lists the package, the CVE, and the fixed version.
2. Bump the constraint in `requirements.in` (e.g. `py-cord>=2.7.3`),
   regenerate hashes:
   ```
   pip-compile --generate-hashes requirements.in
   ```
3. Run the test suite locally (`pytest`).
4. Commit, PR to prod, merge — the regular pipeline deploys the patched
   bot.

## State file corruption

**Symptom:** Bot reports unexpected behaviour for a user (wrong color,
forgotten preferences) and the journal mentions sanitization warnings.

1. The bot's `_sanitize` step on load drops malformed entries
   automatically and persists the cleaned form on the next save. Most
   "corruption" heals itself.
2. If something serious happened (manual edit gone wrong, partial write),
   restore from the daily backup:
   ```
   ssh root@vps.example.com
   ls -la /root/backups/
   systemctl stop discordbot
   tar -xzf /root/backups/sirrmizan-data-YYYYMMDD.tar.gz \
       -C /home/botdiscord/SirrMizan/
   chown -R botdiscord:botdiscord /home/botdiscord/SirrMizan/data
   systemctl start discordbot
   ```

## Discord token compromise

**Symptom:** Bot does things you didn't program, or gets banned for
abuse.

1. Immediately revoke the token: Discord Developer Portal → your bot →
   Bot tab → **Reset Token**.
2. Update `.env` on the server:
   ```
   ssh root@vps.example.com
   nano /home/botdiscord/SirrMizan/.env   # replace SIRRMIZAN_TOKEN
   systemctl restart discordbot
   ```
3. Check the audit log
   (`/home/botdiscord/SirrMizan/logs/audit.log`) for unusual entries.
4. If the server itself is suspect, follow the next section.

## Suspected server compromise

**Symptom:** Unfamiliar processes, files, or network connections; bot
behaving strangely; SSH login from unknown IP in `auth.log`.

1. Snapshot for forensics: `tar -czf /tmp/forensics.tar.gz /var/log
   /home /etc/cron.* /etc/systemd /root/.bash_history`.
2. Block all inbound except your IP via ufw.
3. Rotate every secret: SSH keys, Discord token, webhook URL.
4. Compare `/etc/passwd`, `/etc/sudoers.d/*`, `crontab -l` (for every
   user) against the known-good state in this repo.
5. If anything looks off, treat it as game over — rebuild the VPS from
   scratch and restore data from offsite backups (not the VPS-local
   `/root/backups/`, which an attacker could have tampered with).

## Server is unreachable (no SSH)

**Symptom:** SSH hangs or refuses connection.

1. Use the VPS provider's web console (Vultr/Hetzner/etc.) to log in
   directly.
2. Check `journalctl -p err -b` for boot-time errors.
3. Check `ufw status` — if rules locked you out, `ufw disable`
   temporarily then fix them.
4. Check `fail2ban-client status sshd` — your IP might have been banned;
   `fail2ban-client unban <your-ip>`.
5. Last resort: re-image the VPS, restore data from offsite backup
   (you do have offsite backups, right?).

## Releasing a new version

1. Land changes via PRs into `dev`. CI must be green.
2. Open PR `dev → prod`. Merge once CI is green on the PR.
3. The `push: prod` trigger fires `deploy.yml` → SSH → bot updated.
4. The `sync-dev.yml` trigger fires → `dev` is reset to match `prod`.
5. Tag a release if it's a meaningful milestone:
   ```
   git fetch origin
   git tag -a v1.X.Y origin/prod -m "Release notes here"
   git push origin v1.X.Y
   ```
6. Update `CHANGELOG.md` (move `[Unreleased]` items into the new version
   section) and commit on `dev`.

## Disabling the bot temporarily

```
ssh root@vps.example.com 'systemctl stop discordbot'
```

The watchdog also will not bring it back if you also disable the cron:
```
ssh root@vps.example.com 'systemctl stop discordbot && crontab -l | grep -v sirrmizan-heartbeat-check | crontab -'
```

To re-enable:
```
ssh root@vps.example.com 'systemctl start discordbot && ( crontab -l ; echo "* * * * * /usr/local/bin/sirrmizan-heartbeat-check.sh" ) | crontab -'
```
