# SirrMizan

A Discord bot for tabletop dice rolling. Strict-but-lenient expression
parser, atomic JSON persistence, multilingual UI, both prefix and slash
commands. Built on [Py-Cord](https://docs.pycord.dev/).

## Capabilities

- Roll arbitrary dice expressions with an optional target name.
- Tolerate any reasonable spacing or stray operators around the expression
  (`1d20 +2d6 +4 Goblin`, `1d20+ Goblin`, `+5 1d20`).
- Per-server configuration: default roll, command prefix, language
  (`en`/`fr`/`de`/`es`).
- Per-user preferences: embed color, compact single-line roll output.
- Two interfaces in parallel — classic prefix commands (`!roll`, `!setlang`)
  and modern Discord slash commands (`/roll`, `/setlang`) with native
  parameter validation and autocomplete.
- Cryptographic-quality RNG via `secrets.SystemRandom`.
- Localized error messages, audit log for sensitive state changes.

## Stack

- **Python ≥ 3.11**
- **Py-Cord 2.6+** for the Discord gateway and slash commands
- **python-dotenv** for env-driven configuration
- **pytest + pytest-asyncio** for the test suite
- No database — three flat JSON files, written atomically

## Project layout

```
sirrmizan/
├── __main__.py        — entry point, lifecycle wiring
├── bot.py             — bot subclass, setup_hook, error handler, save loop
├── config.py          — env-driven config (with legacy config.json fallback)
├── colors.py          — canonical color registry + multi-language aliases
├── dice_parser.py     — strict parser + free-form input splitter
├── logging_setup.py   — rotating app/audit log handlers
├── persistence.py     — atomic JSON read/write
├── state.py           — in-memory state, async lock, schema sanitization
├── translations.py    — i18n strings for en/fr/de/es
└── cogs/
    ├── _base.py       — cog base with localization helpers
    ├── dice.py        — /roll, /setcolor, /getcolor, /setrollshort
    ├── settings.py    — /setlang, /setprefix, /defaultroll
    └── help.py        — /help

scripts/               — start/stop/restart/status (POSIX + PowerShell),
                         systemd unit
tests/                 — parser, state, persistence, config, translations,
                         colors
```

## Design notes

**Strict parser, lenient wrapper.** The expression parser refuses anything
that isn't pure dice syntax. A separate pre-pass tokenizes free-form input,
glues stray operators onto numeric neighbours, and feeds the parser the
longest valid prefix; whatever's left becomes the target name. Malformed
input never silently succeeds — but ergonomic input never fails.

**Atomic persistence.** Every state write goes through a temp file +
`fsync` + `os.replace`. A crash mid-write leaves the previous file intact
rather than truncated. On read, corrupt JSON is moved aside as
`*.json.corrupted` and defaults are used.

**Schema sanitization on load.** State files are user-editable, so loaded
JSON is shape-checked against expected types. Unexpected nested values are
dropped or repaired and the dirty flag is set so the repair persists on
the next save.

**Bot-wide `allowed_mentions=None`.** User-controlled text in error messages
or roll embeds cannot trigger pings — `@everyone` in a target name renders
as plain text.

**Audit log isolated from app log.** Prefix, language, and default-roll
changes (plus high-value rolls) go to a dedicated rotating `audit.log`
with `propagate=False`, separate from the general `app.log`.

**Async lock around every mutation.** All state-mutating methods take the
same `asyncio.Lock` and set a dirty flag. The periodic saver only writes
when the flag is set, avoiding spurious disk activity.

**Cryptographic RNG.** `secrets.SystemRandom`, not the standard `random`
module — players can't reverse-engineer a seed.

## Commands

| Command | Permission |
|---|---|
| `/roll <expr> [target]` — alias `!roll` / `!r` | everyone |
| `/setcolor <name>` | everyone |
| `/getcolor` | everyone |
| `/setrollshort <on\|off>` | everyone |
| `/defaultroll <expr>` | Manage Server |
| `/setlang <en\|fr\|de\|es>` | Manage Server |
| `/setprefix <prefix>` (1–5 visible non-alphanumeric chars) | Manage Server |
| `/help` — alias `!help` / `!h` | everyone |

## Roll syntax

```
NdM             N rolls of an M-sided die           e.g. 3d6
NdM+K           with a constant modifier            e.g. 1d20+5
NdM-PdQ+K       multiple terms, any sign            e.g. 2d6-1d4+3
N               constant only                       e.g. 7
```

The free-form layer collapses any leading sequence of valid tokens into a
single expression, regardless of whitespace or operator placement, and treats
the leftover tokens as a target name:

```
1d20 +20                    →  1d20+20
2d6 + 5 Goblin              →  2d6+5         target = Goblin
1d20 - 5 Boss               →  1d20-5        target = Boss
1d20 +2d6 +4 Goblin         →  1d20+2d6+4    target = Goblin
1d20+ Goblin                →  1d20          target = Goblin   (stray + dropped)
+ 1d20                      →  +1d20
Goblin                      →  uses server default roll, target = Goblin
```

Hard limits: ≤ 50 rolls per term, ≤ 99999 faces, ≤ 100-character input.

## Persistence model

Three JSON files in `data/`:

| File | Shape |
|---|---|
| `user_preferences.json` | `{"users": {<id>: {"color": str, "compact": bool}}}` |
| `user_stats.json` | `{<id>: {"dice_rolls_count": int}}` |
| `server_preferences.json` | `{<id>: {"prefix": str, "language": str, "default_roll": str}}` |

The `state.py` API surface is intentionally narrow; swapping the JSON
backend for SQLite (via `aiosqlite`) is a self-contained refactor.

## Tests

`tests/` exercises the pure logic — parser, state, persistence, config,
translations, colors — across roughly two hundred cases that run in well
under a second. Discord-coupled paths (cogs, gateway) are not unit-tested.

## CI / CD

Two GitHub Actions workflows live in `.github/workflows/`.

**`ci.yml`** runs on every push and PR to `dev` or `prod`:

| Job | Tooling |
|---|---|
| Lint & type-check | `ruff check`, `ruff format --check`, `mypy` |
| Tests | `pytest` with coverage on Python 3.11 / 3.12 / 3.13 |
| Security | `bandit` (SAST), `pip-audit` (dependency CVEs), `gitleaks` (secrets in git history) |

**`deploy.yml`** runs after a successful CI run on `prod`:

* Loads an SSH key and pinned host fingerprint from environment-scoped secrets.
* Opens an SSH session to the VPS as `botdiscord`.
* `authorized_keys` enforces a `command="…/scripts/ci_deploy.sh"` so the
  session can only run that one script — no shell, no port forwarding, no
  agent forwarding.
* The script fast-forwards `origin/prod`, refreshes deps, sanity-checks
  `import sirrmizan`, then `sudo systemctl restart discordbot`. A
  `/etc/sudoers.d/botdiscord-deploy` file scopes the sudo grant to the
  three `systemctl` verbs the script actually needs.

### Branch model

* `dev` is the default branch — work happens here, CI runs but nothing is
  deployed.
* `prod` is the release branch — merging into it triggers an automated
  deploy. Branch protection on `prod` requires a green CI run and a
  reviewed PR.

### Repository configuration (one-time setup)

1. **Default branch**: Settings → Branches → set `dev` as default.
2. **Branch protection on `prod`**: Settings → Branches → Add rule:
   - Require a pull request before merging
   - Require status checks: `Lint & type-check`, `Tests (Python 3.11)`, `Security scans`
   - Require linear history (squash merges)
   - Disallow force pushes
3. **Environment `production`**: Settings → Environments → New →
   `production`, optionally restrict deployments to the `prod` branch.
4. **Secrets** (Settings → Secrets and variables → Actions, or scoped to
   the `production` environment):
   - `DEPLOY_HOST` — VPS hostname
   - `DEPLOY_USER` — `botdiscord`
   - `DEPLOY_SSH_KEY` — private key whose public counterpart is in
     `~botdiscord/.ssh/authorized_keys` on the server (with the
     `command="…"` forced-command restriction)
   - `DEPLOY_KNOWN_HOSTS` — `ssh-keyscan` output for the VPS, pinned so a
     server swap is detectable

## License

MIT.
