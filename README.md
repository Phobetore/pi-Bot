# pi-Bot

pi-Bot is a Discord bot that manages dice rolls with many customization options. Built on [Py-Cord](https://docs.pycord.dev/), it supports multiple languages and offers several commands to make life easier for both players and game masters.

## Main Features

- **Flexible dice rolling**: expressions like `2d6+3` with modifiers and an optional target name.
- **Card drawing**: draw cards from a standard 52-card deck with commands like `!draw`, `!shuffle`, and `!newdeck`.
- **Custom colors**: each user can choose the bot's message color (`!setcolor red`).
- **Configurable prefix**: adjust the command prefix per server (`!setprefix ?`).
- **Default roll**: define a default roll used when no expression is provided (`!defaultRoll 1d20`).
- **Multilanguage support**: English, French, German and Spanish via `!setlang`.
- **Automatic saving**: preferences and statistics stored in JSON files and cached in memory.

## Installation

1. Clone this repository.
2. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `config.json` file with the following content:
   ```json
   {
       "token": "YOUR_DISCORD_TOKEN",
       "prefix": "!"
   }
   ```
4. Start the bot:
   ```bash
   python main.py
   ```

## Quick Guide

### For players and GMs

- **Roll a single die**: `!roll 1d20`
- **Add modifiers**: `!roll 1d20+5` or `!r 1d6+1d4-2`
- **Shortcut**: `!r` is the same as `!roll`
- **Default roll**: if a roll is set via `!defaultRoll`, calling `!r` with no arguments uses it
- **Draw cards**: `!draw` or `!draw 5` to draw cards from the deck
- **Shuffle deck**: `!shuffle` to shuffle and return all cards to the deck
- **New deck**: `!newdeck` to create a fresh deck
- **Deck info**: `!deckinfo` to see how many cards remain
- **Change message color**: `!setcolor red`
- **View the current color**: `!getcolor`

### For moderators

- **Change the language**: `!setlang fr`
- **Set a default roll**: `!defaultRoll 1d20+5`
- **Modify the prefix**: `!setprefix ?`

Only those with the "Manage Server" permission can change the language, default roll, or prefix.

## Additional Notes

- The files `user_stats.json`, `user_preferences.json` and `server_preferences.json` are generated automatically and ignored by git.
- Audit logs are saved in `audit.log`.

## Contributing

Contributions are welcome! Feel free to open an issue or pull request to suggest improvements.
