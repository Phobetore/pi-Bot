# pi-Bot

A Discord bot for tabletop dice rolling, built on [Py-Cord](https://docs.pycord.dev/).
Multi-server, multi-language, with persistent per-user and per-server preferences.

## Features

- **Flexible dice rolls**: `2d6+3 Goblin`, `1d20+1d4-2`, modifier-only or dice-only.
- **Per-user color**: each user picks their preferred embed color (`!setcolor red`).
- **Per-server prefix**: any moderator can set a custom prefix (`!setprefix ?`).
- **Per-server default roll**: roll without arguments uses the server default
  (`!defaultRoll 1d20`).
- **Per-server language**: `en`, `fr`, `de`, `es` (`!setlang fr`).
- **Cryptographic-quality RNG**: rolls use `secrets.SystemRandom`.
- **Atomic JSON persistence**: state is never corrupted by interrupted writes.
- **Audit log**: prefix, language and default-roll changes are logged.

## Requirements

- Python ≥ 3.11
- A Discord bot application + token
  ([create one](https://discord.com/developers/applications))
- The **MESSAGE CONTENT INTENT** privileged gateway intent enabled on your
  application (Developer Portal → your app → *Bot* → *Privileged Gateway
  Intents*). Without it, py-cord raises `PrivilegedIntentsRequired` on
  startup.

## Installation

```bash
git clone <this-repo>
cd pi-bot
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"            # or: pip install -r requirements.txt
```

## Configuration

Configuration is read from environment variables. Copy the example file:

```bash
cp .env.example .env
$EDITOR .env                       # set PI_BOT_TOKEN
```

Available variables (all optional except `PI_BOT_TOKEN`):

| Variable | Default | Description |
|---|---|---|
| `PI_BOT_TOKEN` | — | **Required.** Discord bot token. |
| `PI_BOT_DEFAULT_PREFIX` | `!` | Fallback prefix when a server hasn't set its own. |
| `PI_BOT_DATA_DIR` | `data` | Directory for persisted JSON state. |
| `PI_BOT_LOG_DIR` | `logs` | Directory for log files. |
| `PI_BOT_SAVE_INTERVAL` | `60` | Seconds between background flushes (only fires if state changed). |
| `PI_BOT_LOG_LEVEL` | `INFO` | One of `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. |

### Migrating from the legacy `config.json`

The previous layout stored secrets in `config.json`. For backward compatibility,
that file is still read **only** when the matching environment variables are
unset. The recommended path is to migrate values to `.env` and delete
`config.json`.

## Running

```bash
python -m pi_bot
# or, equivalently
python main.py
# or, after `pip install -e .`
pi-bot
```

The bot creates `data/` and `logs/` on first start.

## Commands

| Command | Description | Permission |
|---|---|---|
| `!roll <expr> [target]` (alias `!r`) | Roll dice. | everyone |
| `!setcolor <name>` | Set your embed color. | everyone |
| `!getcolor` | Show your color. | everyone |
| `!defaultRoll <expr>` | Set server default roll. | `Manage Server` |
| `!setlang <en\|fr\|de\|es>` | Set server language. | `Manage Server` |
| `!setprefix <prefix>` | Set server prefix (1–5 visible non-alphanumeric chars). | `Manage Server` |
| `!help` (alias `!h`) | Show localized help. | everyone |

### Dice expressions

```
NdM             N rolls of an M-sided die           e.g.  3d6
NdM+K           with constant modifier               e.g.  1d20+5
NdM-PdQ         multiple terms (any sign)            e.g.  2d6-1d4+3
N               constant only                        e.g.  7
```

Limits: ≤ 50 rolls per term, ≤ 99999 faces, ≤ 100-character expression.

## Development

```bash
pip install -e ".[dev]"
pytest                              # run tests
ruff check pi_bot tests             # lint
mypy pi_bot                         # type-check
```

### Project layout

```
pi_bot/
├── __init__.py
├── __main__.py        # `python -m pi_bot` entrypoint
├── bot.py             # PiBot subclass + lifecycle + error handler
├── colors.py          # color registry and aliases
├── config.py          # env-driven configuration loader
├── dice_parser.py     # strict dice-expression parser
├── logging_setup.py   # rotating-file logging
├── persistence.py     # atomic JSON read/write
├── state.py           # async-locked, persistent in-memory state
├── translations.py    # i18n strings
└── cogs/
    ├── dice.py        # !roll, !setcolor, !getcolor
    ├── settings.py    # !setlang, !setprefix, !defaultRoll
    └── help.py        # !help
tests/
├── test_dice_parser.py
├── test_state.py
├── test_persistence.py
└── test_config.py
```

### Persistence model

State lives in three JSON files inside `PI_BOT_DATA_DIR`:

- `user_preferences.json` — `{"users": {"<user_id>": {"color": "<canonical>"}}}`
- `user_stats.json` — `{"<user_id>": {"dice_rolls_count": N}}`
- `server_preferences.json` — `{"<guild_id>": {"prefix": "...", "language": "...", "default_roll": "..."}}`

Writes are atomic (`write to .tmp → fsync → os.replace`). On corruption the
file is moved aside as `*.json.corrupted` and defaults are used.

For higher-traffic deployments, swap `pi_bot.state` for a SQLite-backed
implementation behind the same surface.

## Security notes

- The bot token must never be checked into Git. `.env` and `config.json` are
  in `.gitignore`.
- The dice RNG uses OS entropy (`secrets.SystemRandom`).
- Custom prefixes are restricted to a fixed whitelist of visible
  non-alphanumeric ASCII characters; alphanumeric prefixes are rejected to
  avoid collisions with normal chat.
- All server-scoped commands require `Manage Server`.
- Sensitive changes (prefix, language, default roll) are written to
  `logs/audit.log`.

## License

MIT.
