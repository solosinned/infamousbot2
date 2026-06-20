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

- Install dependencies (recommended in a virtualenv):

```bash
python3 -m pip install -r requirements.txt
python3 -m playwright install
```

- Configure credentials and target site using environment variables (do not commit these):

```bash
export HOTEL_URL="https://infamous-tutoring.space/"
export SITE_EMAIL="your@email"
export SITE_PASSWORD="yourpassword"
```

- Run the userbot (optionally headless):

```bash
python3 web_userbot.py --headless
```

- If your network needs a proxy, provide one with `--proxy` or set `WEB_USERBOT_PROXY`:

```bash
python3 web_userbot.py --headless --proxy http://127.0.0.1:8080
```

- The userbot will sign in with the provided credentials and monitor the page chat for commands prefixed with `s.`. Responses are sent back into the website chat.

## Notes

- Store credentials in environment variables or a secrets manager; do not commit them into the repository.
- The website userbot uses Playwright to control a browser and may require extra interaction if the site uses CAPTCHA or multi-step authentication.
