#!/usr/bin/env python3
"""Weekly security analytics report posted to Discord.

Reads /var/lib/sirrmizan/attack-log.jsonl (populated by
sirrmizan-abuseipdb.sh) plus the journal for ``ssh`` and ``fail2ban``
covering the last 7 days, computes summary statistics, and posts a
Discord embed + a plain-text attachment with the full breakdown.

Designed to use only stdlib so we don't need a venv on the server.
"""

from __future__ import annotations

import collections
import datetime as dt
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

ATTACK_LOG = Path("/var/lib/sirrmizan/attack-log.jsonl")
WEBHOOK_FILE = Path("/etc/sirrmizan/webhook.url")
PERMABAN_SET = "sirrmizan-permaban"
BLOCKLIST_SET = "sirrmizan-blocklist"

WINDOW_DAYS = 7
TOP_N = 10


def journal(unit: str, since: str) -> str:
    try:
        return subprocess.check_output(
            ["journalctl", "-u", unit, "--since", since, "--no-pager"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        return ""


def ipset_count(name: str) -> int:
    try:
        out = subprocess.check_output(
            ["ipset", "list", name, "-output", "save"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        return 0
    return sum(1 for line in out.splitlines() if line.startswith("add "))


def read_attack_log(cutoff_iso: str) -> list[dict]:
    if not ATTACK_LOG.exists():
        return []
    events: list[dict] = []
    with ATTACK_LOG.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            if e.get("ts", "") >= cutoff_iso:
                events.append(e)
    return events


def bar(value: int, peak: int, width: int = 20) -> str:
    if peak <= 0:
        return ""
    filled = round((value / peak) * width)
    filled = max(0 if value == 0 else 1, filled)
    return "█" * filled + "░" * (width - filled)


def hour_heatmap(timestamps: list[str]) -> str:
    """Render a 24-hour heatmap as a monospace text block."""
    buckets = [0] * 24
    for ts in timestamps:
        try:
            buckets[int(ts[11:13])] += 1
        except (ValueError, IndexError):
            continue
    peak = max(buckets) if buckets else 0
    if peak == 0:
        return "(aucune donnée horaire)"
    lines = []
    for hour, count in enumerate(buckets):
        lines.append(f"{hour:02d}h │{bar(count, peak)}│ {count}")
    return "\n".join(lines)


def parse_ssh_usernames(journal_text: str) -> collections.Counter:
    """Pull attempted usernames from sshd ``Failed password for`` /
    ``Invalid user`` lines.
    """
    counter: collections.Counter = collections.Counter()
    rx = re.compile(r"(?:Failed password for(?: invalid user)?|Invalid user) ([A-Za-z0-9._-]+)")
    for line in journal_text.splitlines():
        match = rx.search(line)
        if match:
            counter[match.group(1)] += 1
    return counter


def parse_fail2ban_bans(journal_text: str) -> list[tuple[str, str, str]]:
    """Extract (timestamp, jail, ip) tuples from fail2ban Ban lines."""
    bans: list[tuple[str, str, str]] = []
    rx = re.compile(r"\[(\w+)\]\s+Ban\s+([0-9a-fA-F.:]+)")
    ts_rx = re.compile(r"^(\w{3} \d{2} \d{2}:\d{2}:\d{2})")
    for line in journal_text.splitlines():
        if " Ban " not in line:
            continue
        m = rx.search(line)
        if not m:
            continue
        ts_match = ts_rx.match(line)
        bans.append((ts_match.group(1) if ts_match else "", m.group(1), m.group(2)))
    return bans


def post_discord(content: str, attachment_text: str, attachment_name: str) -> None:
    if not WEBHOOK_FILE.exists():
        sys.stderr.write("(no webhook configured — printing to stdout instead)\n")
        print(content)
        print()
        print(attachment_text)
        return
    url = WEBHOOK_FILE.read_text().strip()
    boundary = "----sirrmizan-report-" + os.urandom(8).hex()
    body_parts = []

    def add_field(name: str, value: str) -> None:
        body_parts.append(f"--{boundary}\r\n")
        body_parts.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n')
        body_parts.append(value + "\r\n")

    def add_file(name: str, filename: str, content_bytes: bytes) -> None:
        body_parts.append(f"--{boundary}\r\n")
        body_parts.append(
            f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'
        )
        body_parts.append("Content-Type: text/plain; charset=utf-8\r\n\r\n")
        body_parts.append(content_bytes.decode("utf-8") + "\r\n")

    add_field("content", content)
    add_file("file", attachment_name, attachment_text.encode("utf-8"))
    body_parts.append(f"--{boundary}--\r\n")
    body = "".join(body_parts).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    try:
        urllib.request.urlopen(req, timeout=15).read()
    except Exception as exc:  # pragma: no cover
        sys.stderr.write(f"discord post failed: {exc}\n")


def main() -> int:
    now = dt.datetime.now(dt.timezone.utc)
    cutoff = now - dt.timedelta(days=WINDOW_DAYS)
    since_human = cutoff.strftime("%Y-%m-%d %H:%M:%S")
    cutoff_iso = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")

    enriched = read_attack_log(cutoff_iso)
    sshd_journal = journal("ssh", since_human)
    f2b_journal = journal("fail2ban", since_human)

    usernames = parse_ssh_usernames(sshd_journal)
    bans = parse_fail2ban_bans(f2b_journal)

    by_ip: collections.Counter = collections.Counter(ip for _, _, ip in bans)
    by_jail: collections.Counter = collections.Counter(jail for _, jail, _ in bans)

    ip_meta: dict[str, dict] = {}
    for event in enriched:
        ip = event.get("ipAddress")
        if not ip:
            continue
        prev = ip_meta.get(ip, {})
        # Keep the highest-confidence record we have.
        if event.get("abuseConfidence", 0) >= prev.get("abuseConfidence", -1):
            ip_meta[ip] = event

    by_country: collections.Counter = collections.Counter()
    for ip in by_ip:
        cc = ip_meta.get(ip, {}).get("countryCode") or "?"
        by_country[cc] += by_ip[ip]

    unique_ips = len(by_ip)
    total_attempts = sum(usernames.values())
    recidive_ips = sum(1 for ip, count in by_ip.items() if count >= 2)

    permaban_n = ipset_count(PERMABAN_SET)
    blocklist_n = ipset_count(BLOCKLIST_SET)

    timestamps = [e.get("ts", "") for e in enriched]
    heatmap = hour_heatmap(timestamps)

    # --- Build the long-form text attachment ---
    lines: list[str] = []
    lines.append(f"=== SirrMizan — security report {cutoff:%Y-%m-%d} → {now:%Y-%m-%d} ===")
    lines.append("")
    lines.append("Synthèse")
    lines.append(f"  IPs uniques bannies        : {unique_ips}")
    lines.append(f"  Bans total                 : {sum(by_ip.values())}")
    lines.append(f"  Tentatives d auth ratées   : {total_attempts}")
    lines.append(f"  Récidivistes (≥2 bans)     : {recidive_ips}")
    lines.append(f"  ipset permaban (taille)    : {permaban_n}")
    lines.append(f"  ipset blocklist (taille)   : {blocklist_n}")
    lines.append("")

    lines.append(f"Top {TOP_N} IPs (par nb de bans)")
    for ip, count in by_ip.most_common(TOP_N):
        meta = ip_meta.get(ip, {})
        cc = meta.get("countryCode", "?")
        isp = meta.get("isp", "?")
        score = meta.get("abuseConfidence")
        score_str = f"{score}/100" if score is not None else "—"
        lines.append(f"  {count:>4}× {ip:<15} {cc:<3} score={score_str:<7} {isp}")
    lines.append("")

    lines.append(f"Top {TOP_N} usernames tentés (sshd)")
    for user, count in usernames.most_common(TOP_N):
        lines.append(f"  {count:>5}× {user}")
    lines.append("")

    lines.append("Pays attaquants (top 5)")
    for cc, count in by_country.most_common(5):
        lines.append(f"  {count:>5} bans  {cc}")
    lines.append("")

    lines.append("Heatmap horaire (UTC, IPs enrichies)")
    lines.append(heatmap)
    lines.append("")

    lines.append("Par jail fail2ban")
    for jail, count in by_jail.most_common():
        lines.append(f"  {count:>5}  {jail}")
    lines.append("")

    attachment_text = "\n".join(lines)

    # --- Short Discord summary in the message body ---
    summary_lines = [
        f"🛡️ **Rapport sécurité hebdomadaire** ({cutoff:%Y-%m-%d} → {now:%Y-%m-%d})",
        f"• {unique_ips} IPs uniques bannies, {sum(by_ip.values())} bans total",
        f"• {recidive_ips} récidivistes (≥2 bans)",
        f"• ipset permaban: {permaban_n} | blocklist: {blocklist_n}",
    ]
    if by_country:
        top_country = by_country.most_common(1)[0]
        summary_lines.append(f"• Top pays: {top_country[0]} ({top_country[1]} bans)")
    if usernames:
        top_user = usernames.most_common(1)[0]
        summary_lines.append(f"• Username le plus ciblé: `{top_user[0]}` ({top_user[1]} tentatives)")
    summary_lines.append("Détail complet en pièce jointe.")

    attachment_name = f"sirrmizan-security-{now:%Y%m%d}.txt"
    post_discord("\n".join(summary_lines), attachment_text, attachment_name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
