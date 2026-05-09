# SirrMizan

A Discord bot for tabletop dice rolling. Python, runs on
[Py-Cord](https://docs.pycord.dev/).

## Features

- Arbitrary dice expressions: `1d20`, `2d6+3`, `1d20+2d6+4 Goblin`.
- Free-form input — spaces, stray operators and lone signs around the
  expression are tolerated. `1d20 +20`, `2d6 + 5 Goblin`, `1d20+ Goblin`
  all parse the way you'd expect.
- Server-side: command prefix, language (en/fr/de/es), default roll.
- User-side: embed color, compact single-line output.
- Both prefix commands (`!roll`) and slash commands (`/roll`).

## Roll syntax

```
1d20                 single d20
2d6+3 Goblin         expression + optional target name
1d20 +2d6 +4         multiple terms
+5                   modifier-only
```

Limits: 50 rolls per term, 99999 faces, 100-character expression.

## Commands

| Command | Permission |
|---|---|
| `/roll <expr> [target]` — alias `!roll` / `!r` | everyone |
| `/setcolor <name>` | everyone |
| `/getcolor` | everyone |
| `/setrollshort <on\|off>` | everyone |
| `/defaultroll <expr>` | Manage Server |
| `/setlang <en\|fr\|de\|es>` | Manage Server |
| `/setprefix <prefix>` | Manage Server |
| `/help` | everyone |

## Project layout

```
sirrmizan/
├── __main__.py        entrypoint
├── bot.py             bot class, lifecycle, error handler
├── config.py          env-driven config
├── dice_parser.py     expression parser + free-form splitter
├── state.py           in-memory state, JSON-backed
├── persistence.py     atomic JSON writes
├── translations.py    i18n (en/fr/de/es)
├── colors.py
├── logging_setup.py
└── cogs/
    ├── _base.py       cog base + slash cooldown helper
    ├── dice.py        /roll, /setcolor, /getcolor, /setrollshort
    ├── settings.py    /setlang, /setprefix, /defaultroll
    └── help.py        /help

tests/                 pytest suite (parser, state, persistence, …)
scripts/               start/stop/status, systemd unit, ci_deploy.sh
.github/workflows/     CI + automatic deploy on prod
```

## Branches

- `dev` — default, integration branch.
- `prod` — release branch. Merging into it triggers an automatic
  deploy via SSH after CI is green.

## State

Three flat JSON files in `data/`, written atomically (tempfile + fsync +
rename):

| File | Shape |
|---|---|
| `user_preferences.json` | `{"users": {<id>: {"color": str, "compact": bool}}}` |
| `user_stats.json` | `{<id>: {"dice_rolls_count": int}}` |
| `server_preferences.json` | `{<id>: {"prefix": str, "language": str, "default_roll": str}}` |

## Tests

```
pytest
```

## More

- [`CHANGELOG.md`](CHANGELOG.md) — version history.
- [`docs/runbook.md`](docs/runbook.md) — what to do when something breaks.

## License

MIT.
