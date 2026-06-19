# InfamousBot2

A local Python economy userbot scaffold for https://inf44121.eleganthotel.my/.

## Features

- Local economy with balance, shop, and fishing.
- `s.fish` catches fish from a 40+ fish pool with rarities and prices.
- `s.shop` sells lures that boost rare fish chances.
- `s.gamblecoinflip` and `s.gambleslots` with cooldowns and bet limits.
- Fun social commands: `s.slap`, `s.ship`, `s.aura`.

## Usage

1. Install Python 3.12+.
2. Run `python3 bot.py` for the local terminal economy bot.
3. Use `login <name>` to create or switch local users.
4. Enter `s.help` for available commands.

## Website userbot

- Run `python3 web_userbot.py` to launch the website userbot.
- It will attempt to sign in automatically using the account in `config.py` and monitor the chat area for commands beginning with `s.`.
- It sends responses back into the website chat.

## Notes

- The provided account info is stored in `config.py` for future automation.
- This current version does not automate the website directly; it is a local command-based economy bot.
