#!/usr/bin/env bash
set -e

python3 -m playwright install --with-deps chromium
python3 web_userbot.py --headless
