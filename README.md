# pi-Bot

A Discord bot for rolling dice in tabletop RPG games.

> **Note:** This is mainly a personal project to showcase my development skills. Feel free to use it or contribute if you'd like.

## What is pi-Bot?

pi-Bot is a Discord bot that helps you roll dice for your tabletop games. It supports multiple languages and lets you customize how it looks and works.

## Features

- **Roll dice easily**: Type `!roll 2d6+3` to roll 2 six-sided dice and add 3
- **Personalize your colors**: Choose your favorite color for the bot's messages
- **Multiple languages**: Works in English, French, German, and Spanish
- **Custom prefix**: Change the command prefix for your server
- **Default rolls**: Set a default dice roll for quick use
- **Statistics**: Keep track of how many times you've rolled

## How to Use

### Rolling Dice

The basic command is `!roll` (or just `!r` for short):

```
!roll 2d6+3          Roll 2 six-sided dice and add 3
!roll 1d20+5 Goblin  Roll against a target named "Goblin"
!r 2d8-2             Quick roll shortcut
!r                   Use the default roll (if set)
```

Supported formats:
- `2d6` - Roll 2 six-sided dice
- `1d20+5` - Roll 1 twenty-sided die and add 5
- `3d8-2` - Roll 3 eight-sided dice and subtract 2
- `2d6+1d4+3` - Mix different dice and modifiers

### Personalizing Colors

Choose your favorite color for the bot's messages:

```
!setcolor blue       Choose blue (options: blue, red, green, yellow)
!getcolor            See your current color
```

### Server Settings (For Moderators)

These commands require "Manage Server" permission:

```
!setlang en          Change language (en, fr, de, es)
!defaultRoll 1d20    Set a default roll for quick use
!setprefix ?         Change the command prefix
```

## Contributing

This project is personal, but contributions are welcome. Feel free to:
- Suggest improvements
- Report bugs
- Add new features

To contribute:
1. Fork the project
2. Create a branch
3. Make your changes
4. Submit a Pull Request

## Contact

For questions or suggestions: **core.layer**
