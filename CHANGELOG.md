# Changelog

All notable changes to this project. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added — security stack uplift

- **Persistent permaban** via `ipset` (`sirrmizan-permaban`, hash:ip)
  loaded at boot by a new `sirrmizan-ipset-restore.service`. Survives
  fail2ban restart and reboot — previously every ban evaporated on
  service bounce.
- **Recidive jail** for fail2ban: any IP that triggers ≥3 bans in 7
  days is moved to the permaban ipset for 4 weeks.
- **AbuseIPDB enrichment**: each ban is queried against AbuseIPDB,
  results (country, ISP, confidence, total reports) appended to
  `/var/lib/sirrmizan/attack-log.jsonl`. Immediate Discord alert when
  confidence ≥90, when a new attacker country is seen, or when one of
  our known-good IPs gets banned (false-positive guard).
- **Threat-feed pre-block** (`sirrmizan-blocklist`, hash:net) refreshed
  daily from Spamhaus DROP/EDROP and AbuseIPDB blacklist. iptables
  drops the traffic at the top of INPUT before sshd even sees it.
- **Anomaly detector** running every 5 min: catches ban-rate spikes,
  single-username brute-force bursts, and our-own-IPs hammering auth
  (compromised account, NAT issue). Per-pattern 30-min cooldown so we
  don't flood the channel during a sustained scan.
- **Weekly security report** (`sirrmizan-security-report.py`,
  Mon 09:00) replacing the bare logwatch dump: top IPs with score +
  ISP + country, top usernames tried, country breakdown, UTC hour
  heatmap, recidive count, ipset sizes. Posted to Discord as a short
  embed + a full text attachment.
- One-shot installer `sirrmizan-security-init.sh` for fresh VPS or
  upgrade-in-place. All new helper scripts live in the repo
  (`scripts/`) so they're version-controlled.

## [1.1.1] — 2026-05-09

### Fixed

- Removed the `_GatewayHealthcheck` handler that triggered `os._exit(1)`
  on any "heartbeat blocked > 60s" line from `discord.gateway`. In
  practice this fired on routine network/gateway hiccups that py-cord
  recovers from on its own — causing 549 systemd-driven restarts in
  3 days on prod. The cron watchdog (now 1min cadence + 90s stale
  threshold) covers the real-stuck case at the OS level, so the
  app-level hook was both redundant and far too trigger-happy.

### Changed

- Tightened watchdog cadence: bot heartbeat 60s→30s (write-then-sleep so
  a fresh boot is detected immediately), cron check 5min→1min, stale
  threshold 5min→90s.

## [1.1.0] — 2026-05-09

First tagged release. Bot is feature-complete for tabletop dice rolling
and runs in production with a full CI/CD pipeline.

### Bot

- Roll command (`!roll` / `/roll`) with strict-but-lenient parser:
  arbitrary spacing around operators, optional target name, dice/modifier
  ordering tolerated.
- Per-server: command prefix, language (en/fr/de/es), default expression.
- Per-user: embed color, compact single-line output toggle.
- Both prefix and slash commands.
- Cryptographic-quality RNG (`secrets.SystemRandom`).
- Atomic JSON persistence with schema sanitization on load.
- Localized error messages and global `allowed_mentions=None`.
- Audit log for sensitive state changes.
- Per-user, per-command cooldowns; max-concurrency on `roll`.

### Infrastructure

- Locked-down deploy: forced-command SSH key from CI, restricted sudoers,
  hashed pip dependencies, branch-protected prod.
- GitHub Actions: lint + tests + security scans on every push, automatic
  deploy on push to prod.
- Auto-sync of `dev` to `prod` after every merge to avoid squash-merge
  divergence.
- systemd hardening: `MemoryMax=512M`, `NoNewPrivileges`, restricted
  filesystem access.
- Cron suite on the VPS:
  - 5-min heartbeat watchdog with restart cap (3/h) and Discord alerts
  - daily backup (14-day retention) of state files
  - daily disk-space alert (>80%)
  - weekly logwatch report posted to Discord
  - weekly `pip-audit` for dependency CVEs
- ufw firewall (port 22 only, rate-limited) + fail2ban.
- Auto-reboot at 04:00 when kernel patches are pending.

[Unreleased]: https://github.com/Phobetore/pi-Bot/compare/v1.1.1...HEAD
[1.1.1]: https://github.com/Phobetore/pi-Bot/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/Phobetore/pi-Bot/releases/tag/v1.1.0
