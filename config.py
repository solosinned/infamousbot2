"""Configuration and website account settings for the InfamousBot2 economy bot.

This module reads credentials and the target site URL from environment variables
to avoid committing secrets into the repository. If an environment variable is
not set, the existing hard-coded value is used as a fallback (not recommended
for production).
"""

from __future__ import annotations

import os

# Set these in your environment instead of committing into this file:
#   HOTEL_URL, SITE_EMAIL, SITE_PASSWORD

HOTEL_URL = os.environ.get("HOTEL_URL", "https://inf44121.eleganthotel.my/")
SITE_EMAIL = os.environ.get("SITE_EMAIL", "tokyosidz@outlook.com")
SITE_PASSWORD = os.environ.get("SITE_PASSWORD", "87784325")

# This bot currently runs locally and provides economy/command handling.
# For website automation, set the three environment variables above and then
# run `python3 web_userbot.py --headless` (headless optional).
