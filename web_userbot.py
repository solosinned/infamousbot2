from __future__ import annotations

import argparse
import os
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

LOGIN_SUCCESS_TEXT = [
    'logout',
    'sign out',
    'profile',
    'account',
    'settings',
    'my account',
    'dark mode',
]

LOGIN_FAILURE_TEXT = [
    'login',
    'sign in',
    'register',
    'create account',
    'forgot password',
]

INITIAL_OVERLAY_TEXT_CANDIDATES = [
    'click anywhere',
    'loading learning environment',
    'student dashboard',
    'continue to site',
]

CHAT_OPEN_TRIGGER_SELECTORS = [
    "button:has-text('Chat')",
    "a:has-text('Chat')",
    "button[aria-label*='chat']",
    "button[class*='chat']",
    "div[class*='chat']",
    "[data-testid*='chat']",
    "[aria-label*='Chat']",
    ".bottom-nav .chat",
    ".nav-chat",
    ".chat-icon",
]

BROWSER_ERROR_URL_PREFIXES = [
    'chrome-error://',
    'data:text/html,chromewebdata',
]

CAPTCHA_SELECTORS = [
    "iframe[src*='anubis']",
    "iframe[src*='captcha']",
    "iframe[src*='hcaptcha']",
    "iframe[src*='recaptcha']",
    "div[class*='anubis']",
    "div[id*='anubis']",
    "div[class*='h-captcha']",
    "div[class*='g-recaptcha']",
    "div[id*='h-captcha']",
    "div[id*='g-recaptcha']",
]

CAPTCHA_WAIT_SECONDS = 180

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

CHAT_MESSAGE_CANDIDATES = [
    '.message',
    '.chat-message',
    '.chat-line',
    '.message-row',
    '.message-body',
    '.message-text',
    '.bubble',
    '.chat-entry',
    '.room-chat-message',
    '.chat-message__content',
    '.message__content',
    '.chat-item',
    '.msg',
    '.chat-msg',
    '.message-content',
    '.chat-text',
    '.bubble-text',
    '.comment',
    '.comment-message',
    '[data-testid*="message"]',
    '[aria-label*="message"]',
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

    def launch(self, headless: bool = False, proxy: Optional[str] = None) -> None:
        proxy_server = self._get_proxy_server(proxy)
        browser_kwargs = {
            "headless": headless,
            "args": [
                "--disable-dev-shm-usage",
                "--disable-setuid-sandbox",
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--use-gl=desktop",
                "--disable-features=IsolateOrigins,site-per-process",
            ],
        }
        if proxy_server:
            print(f"Launching browser with proxy: {proxy_server}")
            browser_kwargs["proxy"] = {"server": proxy_server}
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(**browser_kwargs)
            context = browser.new_context(
                ignore_https_errors=True,
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0.0.0 Safari/537.36"
                ),
                locale="en-US",
                timezone_id="America/Los_Angeles",
                viewport={"width": 1280, "height": 800},
                java_script_enabled=True,
            )
            context.add_init_script(
                "() => {"
                "Object.defineProperty(navigator, 'webdriver', { get: () => false, configurable: true });"
                "Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });"
                "Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });"
                "Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });"
                "window.chrome = { runtime: {} };"
                "const originalQuery = window.navigator.permissions.query.bind(window.navigator.permissions);"
                "window.navigator.permissions.query = (parameters) => {"
                "  if (parameters.name === 'notifications') {"
                "    return Promise.resolve({ state: Notification.permission });"
                "  }"
                "  return originalQuery(parameters);"
                "};"
                "document.body.setAttribute('data-webdriver', 'false');"
                "}"
            )
            page = context.new_page()
            page.set_default_timeout(120000)
            self.page = page
            try:
                self.run()
            finally:
                context.close()
                browser.close()

    def _get_proxy_server(self, cli_proxy: Optional[str]) -> Optional[str]:
        proxy = (
            cli_proxy
            or os.environ.get("WEB_USERBOT_PROXY")
            or os.environ.get("HTTPS_PROXY")
            or os.environ.get("https_proxy")
            or os.environ.get("HTTP_PROXY")
            or os.environ.get("http_proxy")
        )
        if not proxy:
            return None
        proxy = proxy.strip()
        if proxy and not proxy.startswith(("http://", "https://", "socks5://")):
            proxy = "http://" + proxy
        return proxy

    def run(self) -> None:
        print(f"Starting website userbot for {self.local_user}...")
        self._open_site()
        self._dismiss_initial_overlay()
        self._wait_for_captcha_clear()
        print(f"Initial URL before login: {self.page.url}")
        self._login_if_needed()
        try:
            self.page.wait_for_load_state("networkidle", timeout=120000)
        except TimeoutError:
            print("Warning: page did not reach networkidle after login check; continuing anyway.")
        self._dismiss_initial_overlay()
        self._wait_for_captcha_clear()
        print(f"Page URL after login attempt: {self.page.url}")
        print(f"Page title after login attempt: {self.page.title()}")
        self.chat_input_selector = self._find_chat_input()
        self.chat_area_selector = self._find_chat_area()
        if not self.chat_input_selector:
            raise RuntimeError("Could not locate the chat input field on the page.")
        if not self.chat_area_selector:
            raise RuntimeError("Could not locate the chat message area on the page.")
        print(f"Found chat input: {self.chat_input_selector}")
        print(f"Found chat area: {self.chat_area_selector}")
        print("Sending activation ping to global chat...")
        self._send_chat_message("bleh")
        print("Sent initial chat message 'bleh'.")
        print("Logged in and found chat area. Listening for commands...")
        self._listen_loop()

    def _login_if_needed(self) -> None:
        if self._is_logged_in():
            print("Already logged in.")
            return
        print("Login required, looking for login dialog...")
        print(f"Current URL before login: {self.page.url}")
        self._open_login_dialog()
        self._wait_for_captcha_clear()
        
        # Wait for form elements to appear
        print("Waiting for login form elements to appear...")
        try:
            self.page.wait_for_selector("input, textarea, [contenteditable], form", timeout=10000)
        except TimeoutError:
            print("Warning: Timeout waiting for form elements")
        
        time.sleep(1)
        
        email_field = self._find_login_field(["email", "login", "user"], fields=("input",))
        password_field = self._find_login_field(["password", "pass"], fields=("input",))
        
        if not email_field or not password_field:
            print("Login fields were not found. Dumping candidate inputs...")
            self._dump_input_fields()
            # Try to get more page info
            print("Current page URL:", self.page.url)
            print("Current page title:", self.page.title())
            try:
                form_elements = self.page.query_selector_all("form")
                print(f"Found {len(form_elements)} form elements on page")
            except Exception:
                pass
            raise RuntimeError("Unable to find login form fields. Please verify the website login page structure.")
        
        print("Filling login credentials...")
        email_field.fill(SITE_EMAIL)
        password_field.fill(SITE_PASSWORD)
        button = self._find_login_button()
        if button:
            print("Clicking login button...")
            button.click()
        else:
            print("No login button found, pressing Enter on password field...")
            password_field.press("Enter")
        try:
            self.page.wait_for_load_state("networkidle", timeout=120000)
        except TimeoutError:
            print("Warning: page did not reach networkidle after submitting login; continuing anyway.")
        self._dismiss_initial_overlay()
        self._wait_for_captcha_clear()
        print(f"Current URL after login attempt: {self.page.url}")
        print(f"Page title after login attempt: {self.page.title()}")
        if not self._is_logged_in():
            print("Warning: login may not have completed. The site may require additional interaction.")
            print(f"Login check failed. Current URL: {self.page.url}")
            print(f"Current page title: {self.page.title()}")
            self._save_debug_snapshot('login-failure')

    def _is_logged_in(self) -> bool:
        try:
            self.page.wait_for_selector('input[type="password"]', state='detached', timeout=8000)
        except TimeoutError:
            pass
        chat_input_found = bool(self._find_chat_input())
        logged_in_ui = self._find_logged_in_ui()
        login_form_present = self._find_login_ui()
        logged_in = bool(logged_in_ui or (chat_input_found and not login_form_present))
        print(
            f"Login check: chat input {'found' if chat_input_found else 'not found'}, "
            f"login form {'present' if login_form_present else 'absent'}, "
            f"success indicator {'found' if logged_in_ui else 'not found'}, "
            f"inferred {'logged in' if logged_in else 'not logged in'}."
        )
        return logged_in

    def _find_logged_in_ui(self) -> bool:
        body_text = self._get_body_text()
        return any(token in body_text for token in LOGIN_SUCCESS_TEXT)

    def _find_login_ui(self) -> bool:
        body_text = self._get_body_text()
        return any(token in body_text for token in LOGIN_FAILURE_TEXT)

    def _get_body_text(self) -> str:
        try:
            return self.page.inner_text('body').lower()
        except Exception:
            return ''

    def _find_login_field(self, hints: List[str], fields: tuple) -> Optional[Page]:
        # First, try to find in any visible login form
        for field in fields:
            for hint in hints:
                selectors = [
                    f'{field}[type="{hint}"]',
                    f'{field}[name*="{hint}"]',
                    f'{field}[id*="{hint}"]',
                    f'{field}[placeholder*="{hint}"]',
                    f'{field}[aria-label*="{hint}"]',
                ]
                for selector in selectors:
                    try:
                        element = self.page.query_selector(selector)
                        if element and element.is_visible():
                            return element
                    except Exception:
                        pass
        
        # Try finding by attribute combinations
        for field in fields:
            try:
                element = self.page.query_selector(f"{field}[type='text']")
                if element and element.is_visible():
                    placeholder = (element.get_attribute("placeholder") or "").lower()
                    if any(hint in placeholder for hint in hints):
                        return element
            except Exception:
                pass
        
        # Try broader patterns
        for hint in hints:
            try:
                # Look for label associated with input
                label = self.page.query_selector(f"label:has-text('{hint}')")
                if label:
                    for_attr = label.get_attribute("for")
                    if for_attr:
                        element = self.page.query_selector(f'#{for_attr}')
                        if element and element.is_visible():
                            return element
            except Exception:
                pass
        
        # Try to find any form element that might work
        try:
            all_inputs = self.page.query_selector_all("input[type='text'], input[type='email'], input[type='password'], input:not([type])")
            for element in all_inputs:
                try:
                    if not element.is_visible():
                        continue
                    name = (element.get_attribute("name") or "").lower()
                    element_id = (element.get_attribute("id") or "").lower()
                    placeholder = (element.get_attribute("placeholder") or "").lower()
                    aria_label = (element.get_attribute("aria-label") or "").lower()
                    
                    combined = f"{name} {element_id} {placeholder} {aria_label}"
                    if any(hint in combined for hint in hints):
                        return element
                except Exception:
                    pass
        except Exception:
            pass
        
        return None

    def _find_login_button(self) -> Optional[Page]:
        for text in LOGIN_BUTTON_TEXT:
            try:
                button = self.page.query_selector(f"button:has-text(\"{text}\")")
                if button and button.is_visible():
                    return button
            except Exception:
                pass
            try:
                button = self.page.query_selector(f"input[type='submit'][value*='{text}']")
                if button and button.is_visible():
                    return button
            except Exception:
                pass
        
        # Try buttons with class patterns
        try:
            button = self.page.query_selector("button[class*='submit'], button[class*='login'], button[class*='signin']")
            if button and button.is_visible():
                return button
        except Exception:
            pass
        
        # Try any visible submit button
        try:
            buttons = self.page.query_selector_all("button[type='submit'], input[type='submit']")
            if buttons:
                for button in buttons:
                    try:
                        if button.is_visible():
                            return button
                    except Exception:
                        pass
        except Exception:
            pass
        
        # Fallback: get first visible button
        try:
            buttons = self.page.query_selector_all("button, input[type='submit']")
            if buttons:
                for button in buttons:
                    try:
                        if button.is_visible():
                            return button
                    except Exception:
                        pass
        except Exception:
            pass
        
        return None

    def _open_site(self) -> None:
        print(f"Opening site: {HOTEL_URL}")
        try:
            self.page.goto(HOTEL_URL, timeout=120000, wait_until='domcontentloaded')
        except TimeoutError:
            print("Warning: page.goto timed out waiting for DOM content. Continuing with current page state.")
        try:
            self.page.wait_for_load_state("networkidle", timeout=120000)
        except TimeoutError:
            print("Warning: page did not reach networkidle. Continuing with current page state.")
        print(f"Page opened, current URL: {self.page.url}")
        try:
            self._check_for_browser_navigation_error()
        except RuntimeError as exc:
            if HOTEL_URL.lower().startswith("https://"):
                fallback_url = "http://" + HOTEL_URL[len("https://"):]
                print(f"Detected browser navigation failure; retrying with fallback URL: {fallback_url}")
                try:
                    self.page.goto(fallback_url, timeout=120000, wait_until='domcontentloaded')
                    try:
                        self.page.wait_for_load_state("networkidle", timeout=120000)
                    except TimeoutError:
                        print("Warning: fallback page did not reach networkidle. Continuing with current page state.")
                    self._check_for_browser_navigation_error()
                    print(f"Page opened successfully with fallback URL: {self.page.url}")
                    return
                except Exception as fallback_exc:
                    print(f"HTTP fallback also failed: {fallback_exc}")
            raise

    def _check_for_browser_navigation_error(self) -> None:
        if any(self.page.url.startswith(prefix) for prefix in BROWSER_ERROR_URL_PREFIXES):
            body_text = self._get_body_text()
            raise RuntimeError(
                f"Browser navigation failed; current page URL is {self.page.url}. "
                "Verify the target site is accessible from this environment. "
                f"Page body preview: {body_text[:200]!r}"
            )

    def _open_login_dialog(self) -> None:
        if self._open_chat_panel_if_needed():
            print("Chat panel opened using bottom navigation trigger.")
            return

        for text in LOGIN_BUTTON_TEXT:
            start_button = self.page.query_selector(f"button:has-text(\"{text}\")")
            if start_button and start_button.is_visible():
                try:
                    print(f"Clicking login trigger button with text '{text}'")
                    start_button.click()
                    time.sleep(0.5)
                    return
                except Exception:
                    pass
            link = self.page.query_selector(f"a:has-text(\"{text}\")")
            if link and link.is_visible():
                try:
                    print(f"Clicking login trigger link with text '{text}'")
                    link.click()
                    time.sleep(0.5)
                    return
                except Exception:
                    pass

        # Try additional selectors for login buttons
        additional_selectors = [
            'button[class*="login"]',
            'button[class*="signin"]',
            'button[class*="auth"]',
            'a[class*="login"]',
            'a[class*="signin"]',
            'a[href*="login"]',
            'a[href*="signin"]',
            'input[type="submit"]',
        ]
        for selector in additional_selectors:
            try:
                button = self.page.query_selector(selector)
                if button and button.is_visible():
                    try:
                        print(f"Clicking login trigger with selector: {selector}")
                        button.click()
                        time.sleep(0.5)
                        return
                    except Exception:
                        pass
            except Exception:
                pass

        page_text = self._get_body_text()
        if any(token in page_text for token in INITIAL_OVERLAY_TEXT_CANDIDATES):
            try:
                print("Clicking page body to dismiss initial overlay and reveal login flow.")
                self.page.click('body', timeout=5000)
                time.sleep(0.5)
            except Exception:
                pass

        print("No login trigger button/link found; assuming login fields are already visible.")
        time.sleep(1)

    def _open_chat_panel_if_needed(self) -> bool:
        for selector in CHAT_OPEN_TRIGGER_SELECTORS:
            try:
                element = self.page.query_selector(selector)
            except Exception:
                continue
            if element and element.is_visible():
                try:
                    print(f"Hovering and clicking chat trigger selector: {selector}")
                    element.hover()
                    time.sleep(0.2)
                    element.click()
                    time.sleep(0.5)
                    return True
                except Exception:
                    try:
                        print(f"Fallback clicking chat trigger selector: {selector}")
                        element.click(force=True)
                        time.sleep(0.5)
                        return True
                    except Exception:
                        continue
        return False

    def _detect_captcha(self) -> bool:
        for selector in CAPTCHA_SELECTORS:
            try:
                element = self.page.query_selector(selector)
                if element and element.is_visible():
                    print(f"Detected captcha-like element using selector: {selector}")
                    return True
            except Exception:
                continue
        try:
            body_text = self.page.inner_text("body").lower()
            if "anubis" in body_text or "i'm not a robot" in body_text:
                print("Detected captcha-like page content in body text.")
                return True
        except Exception:
            pass
        return False

    def _wait_for_captcha_clear(self) -> None:
        if not self._detect_captcha():
            return
        if self._is_anubis_challenge():
            return self._wait_for_anubis_challenge_clear()
        print("CAPTCHA detected. Waiting for manual solve or page clearance...")
        deadline = time.time() + CAPTCHA_WAIT_SECONDS
        while time.time() < deadline:
            time.sleep(5)
            if not self._detect_captcha():
                print("CAPTCHA appears to be cleared.")
                return
            print("Still waiting for CAPTCHA to clear...")
        raise RuntimeError(
            "CAPTCHA was detected and did not clear within the wait period. "
            "Run the bot without --headless if you need to solve it manually, or adjust the site flow."
        )

    def _is_anubis_challenge(self) -> bool:
        try:
            body_text = self.page.inner_text('body').lower()
            if "making sure you're not a bot" in body_text:
                return True
        except Exception:
            pass
        try:
            if self.page.query_selector("script#anubis_version"):
                return True
        except Exception:
            pass
        return False

    def _wait_for_anubis_challenge_clear(self) -> None:
        print("Anubis challenge detected. Waiting for the challenge to complete...")
        deadline = time.time() + CAPTCHA_WAIT_SECONDS
        while time.time() < deadline:
            time.sleep(5)
            if not self._is_anubis_challenge():
                print("Anubis challenge appears to be cleared.")
                self.page.wait_for_load_state("networkidle", timeout=120000)
                return
            print("Still waiting for Anubis challenge to clear...")
        raise RuntimeError(
            "Anubis challenge did not clear within the wait period. "
            "Run the bot without --headless or add more browsing stealth options."
        )

    def _dump_input_fields(self) -> None:
        try:
            elements = self.page.query_selector_all('input, textarea, [contenteditable], form')
            print(f"Dumping {len(elements)} candidate input fields:")
            for element in elements:
                try:
                    tag = element.evaluate("el => el.tagName")
                    input_type = element.get_attribute("type") or ""
                    name = element.get_attribute("name") or ""
                    element_id = element.get_attribute("id") or ""
                    placeholder = element.get_attribute("placeholder") or ""
                    aria_label = element.get_attribute("aria-label") or ""
                    visible = element.is_visible()
                    print(f"  {tag} type={input_type!r} name={name!r} id={element_id!r} placeholder={placeholder!r} aria-label={aria_label!r} visible={visible}")
                except Exception as e:
                    print(f"  Error inspecting element: {e}")
        except Exception as exc:
            print(f"Failed to dump input fields: {exc}")

    def _dismiss_initial_overlay(self) -> None:
        clicked = False
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
                        clicked = True
                except Exception:
                    pass

        if not clicked:
            page_text = self._get_body_text()
            if any(token in page_text for token in INITIAL_OVERLAY_TEXT_CANDIDATES):
                try:
                    print("Detected click-to-continue overlay; clicking body to dismiss it.")
                    self.page.click('body', timeout=5000)
                    time.sleep(0.5)
                except Exception:
                    try:
                        self.page.mouse.click(10, 10)
                        time.sleep(0.5)
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
                print(f"Detected chat input selector: {selector}")
                return selector
        if self.page.query_selector('div[contenteditable="true"]'):
            print("Detected contenteditable chat input")
            return 'div[contenteditable="true"]'
        print("No chat input selector matched.")
        return None

    def _find_chat_area(self) -> Optional[str]:
        expanded_candidates = CHAT_AREA_CANDIDATES + [
            '.chat-area',
            '.chatbox',
            '.chat-content',
            '.message-list',
            '.chat-window',
            '.chatlog',
            'div[aria-live="polite"]',
            'div[role="log"]',
        ]
        for selector in expanded_candidates:
            element = self.page.query_selector(selector)
            if element:
                print(f"Detected chat area selector: {selector}")
                return selector
        page_text = self.page.content().lower()
        if "chat" in page_text or "message" in page_text:
            print("Falling back to body as chat area selector")
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
        lines = self._collect_chat_lines()
        new_commands: List[str] = []
        for line in lines:
            if line in self.last_seen_lines:
                continue
            self.last_seen_lines.append(line)
            if len(self.last_seen_lines) > 400:
                self.last_seen_lines = self.last_seen_lines[-400:]
            commands = self._extract_commands_from_line(line)
            for command in commands:
                new_commands.append(command)
        if new_commands:
            print(f"Detected new chat commands: {new_commands}")
        return new_commands

    def _collect_chat_lines(self) -> List[str]:
        lines: List[str] = []
        if self.chat_area_selector:
            try:
                raw_text = self.page.inner_text(self.chat_area_selector)
                lines.extend([line.strip() for line in raw_text.splitlines() if line.strip()])
                print(f"Collected {len(lines)} lines from chat area selector {self.chat_area_selector}.")
            except Exception as exc:
                print(f"Error reading chat area text: {exc}")
        if not lines:
            lines = self._scan_message_elements()

        if not lines or not any(COMMAND_PREFIX in line.lower() for line in lines):
            scanned_lines = self._scan_message_elements()
            if scanned_lines:
                lines.extend(scanned_lines)

        if not lines or not any(COMMAND_PREFIX in line.lower() for line in lines):
            fallback_lines = self._scan_all_text_elements_with_commands()
            if fallback_lines:
                lines.extend(fallback_lines)

        if not lines:
            try:
                raw_text = self.page.inner_text('body')
                body_lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
                print(f"Fallback collected {len(body_lines)} lines from body.")
                lines.extend(body_lines)
            except Exception as exc:
                print(f"Fallback body scan failed: {exc}")
        if lines:
            unique_lines: List[str] = []
            seen: set[str] = set()
            for line in lines:
                if line not in seen:
                    unique_lines.append(line)
                    seen.add(line)
            lines = unique_lines
        if not lines:
            self._save_debug_snapshot('no-chat-lines')
        return lines

    def _scan_message_elements(self) -> List[str]:
        lines: List[str] = []
        for selector in CHAT_MESSAGE_CANDIDATES:
            try:
                elements = self.page.query_selector_all(selector)
            except Exception:
                continue
            if elements:
                print(f"Found {len(elements)} elements with selector {selector}.")
            for element in elements:
                try:
                    text = element.inner_text().strip()
                except Exception:
                    continue
                if text:
                    lines.append(text)
        if lines:
            print(f"Scanned {len(lines)} candidate chat lines from message selectors.")
        return lines

    def _extract_commands_from_line(self, line: str) -> List[str]:
        content = line
        if ":" in line:
            content = line.split(":", 1)[-1].strip()
        commands: List[str] = []
        if content.lower().startswith(COMMAND_PREFIX):
            commands.append(content)
            return commands
        tokens = content.split()
        for index, token in enumerate(tokens):
            token = token.strip(".,!?;\"'\n\r")
            if token.lower().startswith(COMMAND_PREFIX):
                commands.append(" ".join(tokens[index:]).strip())
                break
        if not commands:
            match = re.search(re.escape(COMMAND_PREFIX) + r"[\w@]+", content, flags=re.IGNORECASE)
            if match:
                commands.append(content[match.start():].strip())
        return commands

    def _scan_all_text_elements_with_commands(self) -> List[str]:
        try:
            raw_texts = self.page.evaluate(
                "() => {"
                " const elements = Array.from(document.querySelectorAll('body *'));"
                " const results = [];"
                " for (const el of elements) {"
                "   const style = window.getComputedStyle(el);"
                "   if (!style || style.visibility === 'hidden' || style.display === 'none') continue;"
                "   const text = el.innerText || '';"
                "   if (text && text.toLowerCase().includes('s.')) {"
                "     results.push(text.trim());"
                "   }"
                " }"
                " return results;"
                "}"
            )
            lines: List[str] = []
            for text in raw_texts:
                lines.extend([line.strip() for line in text.splitlines() if line.strip()])
            print(f"Found {len(lines)} lines containing command prefix from page-wide scan.")
            return lines
        except Exception as exc:
            print(f"Command-aware page scan failed: {exc}")
            return []

    def _handle_command(self, command_text: str) -> Optional[str]:
        print(f"Handling command: {command_text}")
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
        print(f"Sending chat message using selector {self.chat_input_selector}: {message}")
        element_type = input_field.get_attribute("contenteditable")
        if element_type == "true":
            input_field.click()
            self.page.keyboard.type(message)
            self.page.keyboard.press("Enter")
            return
        try:
            input_field.fill(message)
            input_field.press("Enter")
            return
        except Exception as exc:
            print(f"Primary send method failed: {exc}")
        send_button = self.page.query_selector("button:has-text(\"Send\"), button:has-text(\"send\"), button[aria-label*='Send']")
        if send_button:
            send_button.click()
            return
        try:
            self.page.keyboard.press("Enter")
        except Exception as exc:
            print(f"Fallback send failed: {exc}")
            self._save_debug_snapshot('send-failure')

    def _save_debug_snapshot(self, label: str) -> None:
        try:
            timestamp = int(time.time())
            prefix = f"/tmp/web_userbot_{label}_{timestamp}"
            self.page.screenshot(path=f"{prefix}.png", full_page=True)
            with open(f"{prefix}.html", "w", encoding="utf-8") as handle:
                handle.write(self.page.content())
            print(f"Saved debug snapshot: {prefix}.png and {prefix}.html")
        except Exception as exc:
            print(f"Failed to save debug snapshot {label}: {exc}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the InfamousBot2 website userbot.")
    parser.add_argument("--headless", action="store_true", help="Run the browser in headless mode.")
    parser.add_argument(
        "--proxy",
        help="Optional proxy server to use for the browser, e.g. http://host:port.",
    )
    args = parser.parse_args()

    bot = WebsiteUserbot()
    try:
        bot.launch(headless=args.headless, proxy=args.proxy)
    except Exception as error:
        print(f"Website userbot could not run: {error}")
