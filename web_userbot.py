from __future__ import annotations

import re
import time
from typing import List, Optional

from bot import EconomyBot
from config import HOTEL_URL, SITE_EMAIL, SITE_PASSWORD
from playwright.sync_api import Page, TimeoutError, sync_playwright

COMMAND_PREFIX = "s."

CHAT_INPUT_CANDIDATES = [
    'textarea[placeholder*="chat"]',
    'textarea[placeholder*="message"]',
    'textarea[name*="chat"]',
    'textarea[name*="message"]',
    'input[placeholder*="chat"]',
    'input[placeholder*="message"]',
    'input[name*="chat"]',
    'input[name*="message"]',
    'div[contenteditable="true"]',
    'div[class*="chat"]',
    'div[class*="message"]',
]

CHAT_AREA_CANDIDATES = [
    '.chat-log',
    '.chat-messages',
    '.messages',
    '.room-chat',
    '#chat',
    '#chatlog',
    '#messages',
    '.message-list',
]

LOGIN_BUTTON_TEXT = [
    'Log In',
    'Login',
    'Sign In',
    'Enter',
    'Submit',
    'Continue',
]

OVERLAY_DISMISS_SELECTORS = [
    "button:has-text('Continue')",
    "button:has-text('Continue to site')",
    "button:has-text('Enter')",
    "button:has-text('Click to continue')",
    "button:has-text('Agree')",
    "button:has-text('Accept')",
    "button:has-text('Close')",
    ".overlay",
    ".modal",
    ".popup",
    ".cookie-banner",
    ".splash-screen",
]


class WebsiteUserbot:
    def __init__(self) -> None:
        self.bot = EconomyBot()
        self.local_user = self._derive_local_user()
        self.bot.active_user = self.local_user
        self.bot.ensure_user(self.local_user)
        self.last_seen_lines: List[str] = []
        self.chat_input_selector: Optional[str] = None
        self.chat_area_selector: Optional[str] = None
        self.username = self.local_user

    def _derive_local_user(self) -> str:
        if "@" in SITE_EMAIL:
            return SITE_EMAIL.split("@", 1)[0]
        return SITE_EMAIL

    def launch(self, headless: bool = True) -> None:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=headless)
            context = browser.new_context()
            page = context.new_page()
            self.page = page
            try:
                self.run()
            finally:
                context.close()
                browser.close()

    def run(self) -> None:
        print(f"Starting website userbot for {self.local_user}...")
        self.page.goto(HOTEL_URL, timeout=60000)
        self.page.wait_for_load_state("networkidle", timeout=30000)
        self._dismiss_initial_overlay()
        self._login_if_needed()
        self.page.wait_for_load_state("networkidle", timeout=30000)
        self._dismiss_initial_overlay()
        self.chat_input_selector = self._find_chat_input()
        self.chat_area_selector = self._find_chat_area()
        if not self.chat_input_selector:
            raise RuntimeError("Could not locate the chat input field on the page.")
        if not self.chat_area_selector:
            raise RuntimeError("Could not locate the chat message area on the page.")
        print("Logged in and found chat area. Listening for commands...")
        self._listen_loop()

    def _login_if_needed(self) -> None:
        if self._is_logged_in():
            print("Already logged in.")
            return
        self._open_login_dialog()
        email_field = self._find_login_field(["email", "login", "user"], fields=("input",))
        password_field = self._find_login_field(["password", "pass"], fields=("input",))
        if not email_field or not password_field:
            raise RuntimeError("Unable to find login form fields. Please verify the website login page structure.")
        email_field.fill(SITE_EMAIL)
        password_field.fill(SITE_PASSWORD)
        button = self._find_login_button()
        if button:
            button.click()
        else:
            password_field.press("Enter")
        self.page.wait_for_load_state("networkidle", timeout=30000)
        self._dismiss_initial_overlay()
        if not self._is_logged_in():
            print("Warning: login may not have completed. The site may require additional interaction.")

    def _is_logged_in(self) -> bool:
        try:
            self.page.wait_for_selector('input[type="password"]', state='detached', timeout=8000)
        except TimeoutError:
            pass
        return bool(self._find_chat_input())

    def _find_login_field(self, hints: List[str], fields: tuple) -> Optional[Page]:
        for field in fields:
            for hint in hints:
                selectors = [
                    f'{field}[type="{hint}"]',
                    f'{field}[name*="{hint}"]',
                    f'{field}[id*="{hint}"]',
                    f'{field}[placeholder*="{hint}"]',
                ]
                for selector in selectors:
                    element = self.page.query_selector(selector)
                    if element:
                        return element
        for field in fields:
            element = self.page.query_selector(f"{field}[type='text']")
            if element:
                placeholder = (element.get_attribute("placeholder") or "").lower()
                if any(hint in placeholder for hint in hints):
                    return element
        return None

    def _find_login_button(self) -> Optional[Page]:
        for text in LOGIN_BUTTON_TEXT:
            button = self.page.query_selector(f"button:has-text(\"{text}\")")
            if button:
                return button
            button = self.page.query_selector(f"input[type='submit'][value*='{text}']")
            if button:
                return button
        buttons = self.page.query_selector_all("button, input[type='submit']")
        if buttons:
            return buttons[0]
        return None

    def _open_login_dialog(self) -> None:
        for text in LOGIN_BUTTON_TEXT:
            start_button = self.page.query_selector(f"button:has-text(\"{text}\")")
            if start_button and start_button.is_visible():
                try:
                    start_button.click()
                    time.sleep(0.5)
                    return
                except Exception:
                    pass
            link = self.page.query_selector(f"a:has-text(\"{text}\")")
            if link and link.is_visible():
                try:
                    link.click()
                    time.sleep(0.5)
                    return
                except Exception:
                    pass

    def _dismiss_initial_overlay(self) -> None:
        for selector in OVERLAY_DISMISS_SELECTORS:
            try:
                elements = self.page.query_selector_all(selector)
            except Exception:
                continue
            for element in elements:
                try:
                    if element.is_visible():
                        element.click()
                        time.sleep(0.25)
                except Exception:
                    pass
        try:
            self.page.evaluate(
                "() => { const overlays = document.querySelectorAll('[class*=overlay],[class*=modal],[class*=popup],[class*=cookie],[class*=splash]'); overlays.forEach(el => el.style.display = 'none'); }"
            )
        except Exception:
            pass

    def _find_chat_input(self) -> Optional[str]:
        for selector in CHAT_INPUT_CANDIDATES:
            element = self.page.query_selector(selector)
            if element:
                return selector
        return None

    def _find_chat_area(self) -> Optional[str]:
        expanded_candidates = CHAT_AREA_CANDIDATES + [
            '.chat-area',
            '.chatbox',
            '.chat-content',
            '.message-list',
            '.messages-list',
            'div[aria-live="polite"]',
            'div[role="log"]',
        ]
        for selector in expanded_candidates:
            element = self.page.query_selector(selector)
            if element:
                return selector
        page_text = self.page.content().lower()
        if "chat" in page_text or "message" in page_text:
            return "body"
        return None

    def _listen_loop(self) -> None:
        while True:
            try:
                new_commands = self._collect_new_commands()
                for raw_command in new_commands:
                    answer = self._handle_command(raw_command)
                    if answer:
                        self._send_chat_message(answer)
                time.sleep(2.0)
            except KeyboardInterrupt:
                print("Stopping userbot.")
                break
            except Exception as exc:
                print(f"Listener error: {exc}")
                time.sleep(5)

    def _collect_new_commands(self) -> List[str]:
        if not self.chat_area_selector:
            return []
        raw_text = self.page.inner_text(self.chat_area_selector)
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        new_commands: List[str] = []
        for line in lines:
            if line in self.last_seen_lines:
                continue
            self.last_seen_lines.append(line)
            if len(self.last_seen_lines) > 400:
                self.last_seen_lines = self.last_seen_lines[-400:]
            content = line.split(":", 1)[-1].strip()
            if content.lower().startswith(COMMAND_PREFIX):
                new_commands.append(content)
        return new_commands

    def _handle_command(self, command_text: str) -> Optional[str]:
        parts = command_text.split()
        command = parts[0].lower()
        args = parts[1:]
        if command == "s.help":
            return (
                "Commands: s.balance, s.shop, s.buy <lure>, s.inventory, s.fish, "
                "s.gamble, s.gamblecoinflip <amt>, s.gambleslots <amt>, s.slap @user, "
                "s.ship @user, s.aura [@user]"
            )
        if command == "s.balance":
            return self.bot.command_balance()
        if command == "s.shop":
            return self.bot.command_shop()
        if command == "s.buy" and args:
            return self.bot.command_buy(args[0])
        if command == "s.inventory":
            return self.bot.command_inventory()
        if command == "s.fish":
            return self.bot.command_fish()
        if command == "s.gamble":
            return self.bot.command_gamble()
        if command == "s.gamblecoinflip" and args:
            return self.bot.command_gamble_coinflip(args[0])
        if command == "s.gambleslots" and args:
            return self.bot.command_gamble_slots(args[0])
        if command == "s.slap" and args:
            return self.bot.command_slap(args[0])
        if command == "s.ship" and args:
            return self.bot.command_ship(args[0])
        if command == "s.aura":
            target = args[0] if args else self.username
            return self.bot.command_aura(target)
        return None

    def _send_chat_message(self, message: str) -> None:
        if not self.chat_input_selector:
            raise RuntimeError("Chat input selector is not defined.")
        input_field = self.page.query_selector(self.chat_input_selector)
        if not input_field:
            raise RuntimeError("Unable to locate the chat input element.")
        element_type = input_field.get_attribute("contenteditable")
        if element_type == "true":
            input_field.click()
            self.page.keyboard.type(message)
            self.page.keyboard.press("Enter")
            return
        input_field.fill(message)
        try:
            input_field.press("Enter")
        except Exception:
            send_button = self.page.query_selector("button:has-text(\"Send\"), button:has-text(\"send\"), button[aria-label*='Send']")
            if send_button:
                send_button.click()
            else:
                self.page.keyboard.press("Enter")


if __name__ == "__main__":
    bot = WebsiteUserbot()
    try:
        bot.launch(headless=True)
    except Exception as error:
        print(f"Website userbot could not run: {error}")
