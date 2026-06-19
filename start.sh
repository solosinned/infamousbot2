#!/usr/bin/env bash
set -e

python3 -m playwright install chromium
python3 web_userbot.py --headless
