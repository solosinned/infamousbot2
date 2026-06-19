from __future__ import annotations

import hashlib
import json
import secrets
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

STATE_PATH = Path("state.json")

SHOP_ITEMS = [
    {
        "id": "basic_lure",
        "name": "Basic Lure",
        "cost": 200,
        "bonus": 0.05,
        "description": "Slightly increases chance to catch rarer fish.",
    },
    {
        "id": "shiny_lure",
        "name": "Shiny Lure",
        "cost": 500,
        "bonus": 0.10,
        "description": "A shiny lure that improves chances for rare and epic catches.",
    },
    {
        "id": "ancient_lure",
        "name": "Ancient Lure",
        "cost": 1200,
        "bonus": 0.15,
        "description": "A powerful lure that makes legendary fish easier to see.",
    },
]

FISH_LIST = [
    {"name": "Mudskipper", "rarity": "Common", "base_price": 45, "weight": 12},
    {"name": "Bluegill", "rarity": "Common", "base_price": 55, "weight": 11},
    {"name": "River Trout", "rarity": "Common", "base_price": 65, "weight": 10},
    {"name": "Guppy", "rarity": "Common", "base_price": 50, "weight": 10},
    {"name": "Flounder", "rarity": "Common", "base_price": 60, "weight": 9},
    {"name": "Koi", "rarity": "Common", "base_price": 70, "weight": 8},
    {"name": "Carp", "rarity": "Common", "base_price": 75, "weight": 8},
    {"name": "Tadpole", "rarity": "Common", "base_price": 40, "weight": 9},
    {"name": "Clownfish", "rarity": "Common", "base_price": 68, "weight": 8},
    {"name": "Pumpkin Bass", "rarity": "Common", "base_price": 72, "weight": 8},
    {"name": "Seahorse", "rarity": "Uncommon", "base_price": 110, "weight": 9},
    {"name": "Sunfish", "rarity": "Uncommon", "base_price": 120, "weight": 8},
    {"name": "Perch", "rarity": "Uncommon", "base_price": 130, "weight": 8},
    {"name": "Schooling Sardine", "rarity": "Uncommon", "base_price": 140, "weight": 7},
    {"name": "Silver Snapper", "rarity": "Uncommon", "base_price": 150, "weight": 7},
    {"name": "Cherryfish", "rarity": "Uncommon", "base_price": 155, "weight": 7},
    {"name": "Pufferfish", "rarity": "Uncommon", "base_price": 165, "weight": 7},
    {"name": "Rainbow Trout", "rarity": "Uncommon", "base_price": 170, "weight": 7},
    {"name": "Cactus Carp", "rarity": "Uncommon", "base_price": 180, "weight": 7},
    {"name": "Electric Eel", "rarity": "Rare", "base_price": 240, "weight": 6},
    {"name": "Harlequin Tetra", "rarity": "Rare", "base_price": 255, "weight": 5},
    {"name": "Sushi Waho", "rarity": "Rare", "base_price": 270, "weight": 5},
    {"name": "Dragon Carp", "rarity": "Rare", "base_price": 290, "weight": 5},
    {"name": "Neon Guppy", "rarity": "Rare", "base_price": 310, "weight": 5},
    {"name": "Ghost Pike", "rarity": "Rare", "base_price": 335, "weight": 5},
    {"name": "Volcano Snapper", "rarity": "Rare", "base_price": 360, "weight": 5},
    {"name": "Aurora Salmon", "rarity": "Rare", "base_price": 385, "weight": 5},
    {"name": "Sapphire Tuna", "rarity": "Epic", "base_price": 520, "weight": 3},
    {"name": "Golden Koi", "rarity": "Epic", "base_price": 560, "weight": 3},
    {"name": "Crystal Sturgeon", "rarity": "Epic", "base_price": 590, "weight": 2},
    {"name": "Obsidian Marlin", "rarity": "Epic", "base_price": 620, "weight": 2},
    {"name": "Moonlight Wyrm", "rarity": "Epic", "base_price": 650, "weight": 2},
    {"name": "Prism Swordfish", "rarity": "Epic", "base_price": 690, "weight": 2},
    {"name": "Emerald Shark", "rarity": "Epic", "base_price": 720, "weight": 2},
    {"name": "Solar Barracuda", "rarity": "Epic", "base_price": 750, "weight": 2},
    {"name": "Zephyr Leviathan", "rarity": "Legendary", "base_price": 1025, "weight": 1},
    {"name": "Shadow Seraph", "rarity": "Legendary", "base_price": 1100, "weight": 1},
    {"name": "Starlight Dragon", "rarity": "Legendary", "base_price": 1240, "weight": 1},
    {"name": "Void Kraken", "rarity": "Legendary", "base_price": 1380, "weight": 1},
]

RARITY_MODIFIERS = {
    "Common": 1.0,
    "Uncommon": 1.10,
    "Rare": 1.30,
    "Epic": 1.60,
    "Legendary": 2.10,
}

GAMBLE_COOLDOWN = 120
SLOTS_COOLDOWN = 180
FISH_WINDOW_SECONDS = 30 * 60
MAX_FISH_PER_WINDOW = 10

SLOT_SYMBOLS = [
    {"symbol": "🍒", "weight": 40, "payout": 2},
    {"symbol": "🍋", "weight": 30, "payout": 3},
    {"symbol": "💎", "weight": 18, "payout": 5},
    {"symbol": "👑", "weight": 8, "payout": 8},
    {"symbol": "7️⃣", "weight": 4, "payout": 15},
]

DEFAULT_USER = {
    "balance": 500,
    "lures": {},
    "fish_history": {},
    "fish_timestamps": [],
    "last_gamble": {"coinflip": 0.0, "slots": 0.0},
}


class EconomyBot:
    def __init__(self) -> None:
        self.state = self.load_state()
        self.active_user = self.state.get("active_user", "guest")
        self.ensure_user(self.active_user)

    def load_state(self) -> Dict:
        if not STATE_PATH.exists():
            return {"users": {}, "active_user": "guest"}
        with STATE_PATH.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def save_state(self) -> None:
        self.state["active_user"] = self.active_user
        with STATE_PATH.open("w", encoding="utf-8") as handle:
            json.dump(self.state, handle, indent=2)

    def ensure_user(self, username: str) -> None:
        if username not in self.state["users"]:
            self.state["users"][username] = json.loads(json.dumps(DEFAULT_USER))
            self.save_state()

    def user(self) -> Dict:
        return self.state["users"][self.active_user]

    def list_commands(self) -> str:
        return (
            "Commands:\n"
            "  login <username>         - Switch to a different local user profile.\n"
            "  s.balance                - View your coin balance.\n"
            "  s.shop                   - View available lures and bonuses.\n"
            "  s.buy <lure>             - Buy a lure to raise rare catch chances.\n"
            "  s.inventory              - View your lures and caught fish counts.\n"
            "  s.fish                   - Catch a fish (max 10 uses per 30 minutes).\n"
            "  s.gamble                 - Show gamble command options.\n"
            "  s.gamblecoinflip <amt>   - Bet coins on a 50/50 coinflip.\n"
            "  s.gambleslots <amt>      - Bet coins on slot machine reels.\n"
            "  s.slap @target           - Slap another user for fun.\n"
            "  s.ship @target           - Ship yourself with someone.\n"
            "  s.aura [@target]         - Reveal a fun aura rating.\n"
            "  s.help                   - Show this command list.\n"
            "  exit                     - Quit the bot."
        )

    def run(self) -> None:
        print("InfamousBot2 economy userbot started.")
        print("Use 'login <username>' to switch users, then 's.help'.")

        while True:
            try:
                raw = input(f"{self.active_user}> ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\nGoodbye.")
                break
            if not raw:
                continue
            if raw.lower() in {"exit", "quit"}:
                print("Goodbye.")
                break
            if raw.lower().startswith("login "):
                username = raw[6:].strip()
                if username:
                    self.active_user = username
                    self.ensure_user(username)
                    print(f"Switched to user '{username}'.")
                else:
                    print("Usage: login <username>")
                continue
            if raw.lower() == "s.help":
                print(self.list_commands())
                continue
            if raw.lower() == "s.balance":
                print(self.command_balance())
                continue
            if raw.lower() == "s.shop":
                print(self.command_shop())
                continue
            if raw.lower().startswith("s.buy "):
                item_name = raw[6:].strip()
                print(self.command_buy(item_name))
                continue
            if raw.lower() == "s.inventory":
                print(self.command_inventory())
                continue
            if raw.lower() == "s.fish":
                print(self.command_fish())
                continue
            if raw.lower() == "s.gamble":
                print(self.command_gamble())
                continue
            if raw.lower().startswith("s.gamblecoinflip "):
                amount = raw[16:].strip()
                print(self.command_gamble_coinflip(amount))
                continue
            if raw.lower().startswith("s.gambleslots "):
                amount = raw[14:].strip()
                print(self.command_gamble_slots(amount))
                continue
            if raw.lower().startswith("s.slap "):
                target = raw[7:].strip()
                print(self.command_slap(target))
                continue
            if raw.lower().startswith("s.ship "):
                target = raw[7:].strip()
                print(self.command_ship(target))
                continue
            if raw.lower().startswith("s.aura"):
                target = raw[6:].strip() if raw.lower() != "s.aura" else self.active_user
                if not target:
                    target = self.active_user
                print(self.command_aura(target))
                continue
            print("Unknown command. Use s.help to see available commands.")

    def command_balance(self) -> str:
        return f"{self.active_user} has {self.user()['balance']} coins."

    def command_shop(self) -> str:
        lines = ["Available lures:"]
        for item in SHOP_ITEMS:
            lines.append(f"  {item['id']} - {item['name']} ({item['cost']} coins): {item['description']}")
        lines.append("Use 's.buy <lure_id>' to purchase a lure.")
        lines.append("Lure bonus stacks and improves rare/epic/legendary catch chances.")
        return "\n".join(lines)

    def command_buy(self, item_name: str) -> str:
        item = next((x for x in SHOP_ITEMS if x["id"] == item_name), None)
        if item is None:
            return "That lure does not exist. Use s.shop to view available items."
        user = self.user()
        if user["balance"] < item["cost"]:
            return f"You need {item['cost']} coins to buy {item['name']}." \
                   f" You only have {user['balance']} coins."
        user["balance"] -= item["cost"]
        user["lures"][item_name] = user["lures"].get(item_name, 0) + 1
        self.save_state()
        return f"Purchased {item['name']} for {item['cost']} coins. You now have {user['lures'][item_name]} of that lure."

    def command_inventory(self) -> str:
        user = self.user()
        lines = [f"Inventory for {self.active_user}:", f"  Balance: {user['balance']} coins"]
        if user["lures"]:
            lines.append("  Lures:")
            for lure_id, qty in user["lures"].items():
                item = next((x for x in SHOP_ITEMS if x["id"] == lure_id), None)
                if item:
                    lines.append(f"    {item['name']} x{qty} (+{int(item['bonus']*100)}% rare chance bonus each)")
        else:
            lines.append("  Lures: none")
        if user["fish_history"]:
            lines.append("  Fish caught:")
            for fish_name, count in sorted(user["fish_history"].items(), key=lambda x: x[0]):
                lines.append(f"    {fish_name}: {count}")
        else:
            lines.append("  Fish caught: none")
        lines.append(f"  Fish uses this window: {self.current_fish_count()} / {MAX_FISH_PER_WINDOW}")
        return "\n".join(lines)

    def get_lure_bonus(self) -> float:
        user = self.user()
        total = 0.0
        for lure_id, qty in user["lures"].items():
            item = next((x for x in SHOP_ITEMS if x["id"] == lure_id), None)
            if item:
                total += item["bonus"] * qty
        return min(total, 0.25)

    def current_fish_count(self) -> int:
        now = time.time()
        timestamps = [t for t in self.user()["fish_timestamps"] if now - t <= FISH_WINDOW_SECONDS]
        self.user()["fish_timestamps"] = timestamps
        self.save_state()
        return len(timestamps)

    def choose_fish(self) -> Dict:
        lure_bonus = self.get_lure_bonus()
        weights = []
        for fish in FISH_LIST:
            bonus = lure_bonus * {
                "Common": 0.0,
                "Uncommon": 0.25,
                "Rare": 0.55,
                "Epic": 0.90,
                "Legendary": 1.25,
            }[fish["rarity"]]
            weight = int(fish["weight"] * (1 + bonus))
            weights.append(max(weight, 1))
        total = sum(weights)
        choice = secrets.randbelow(total)
        running = 0
        for fish, w in zip(FISH_LIST, weights):
            running += w
            if choice < running:
                return fish
        return FISH_LIST[-1]

    def command_fish(self) -> str:
        user = self.user()
        if self.current_fish_count() >= MAX_FISH_PER_WINDOW:
            oldest = min(user["fish_timestamps"])
            remaining = int(FISH_WINDOW_SECONDS - (time.time() - oldest))
            minutes = remaining // 60
            seconds = remaining % 60
            return (
                "You have reached the 10 fish limit for the last 30 minutes. "
                f"Try again in {minutes}m {seconds}s."
            )
        fish = self.choose_fish()
        reward = fish["base_price"] + secrets.randbelow(max(1, fish["base_price"] // 3))
        user["balance"] += reward
        user["fish_history"][fish["name"]] = user["fish_history"].get(fish["name"], 0) + 1
        user["fish_timestamps"].append(time.time())
        self.save_state()
        rarity = fish["rarity"]
        return (
            f"{self.active_user} caught a {rarity} fish: {fish['name']}! "
            f"Earned {reward} coins."
        )

    def command_gamble(self) -> str:
        return (
            "Gamble options:\n"
            "  s.gamblecoinflip <amount> - Flip a coin. Win doubles, lose your bet.\n"
            "  s.gambleslots <amount> - Slot machine with multiple payouts.\n"
            "Gambling has cooldowns and max bet limits to prevent abuse."
        )

    def parse_amount(self, amount_text: str, min_amount: int = 10, max_amount: Optional[int] = None) -> Optional[int]:
        if not amount_text.isdigit():
            return None
        amount = int(amount_text)
        if amount < min_amount:
            return None
        if max_amount is not None and amount > max_amount:
            return None
        return amount

    def command_gamble_coinflip(self, amount_text: str) -> str:
        user = self.user()
        max_bet = min(5000, max(100, int(user["balance"] * 0.2)))
        amount = self.parse_amount(amount_text, 10, max_bet)
        if amount is None:
            return f"Invalid bet amount. Bet between 10 and {max_bet} coins."
        if amount > user["balance"]:
            return "You do not have enough coins for that bet."
        now = time.time()
        if now - user["last_gamble"]["coinflip"] < GAMBLE_COOLDOWN:
            remain = int(GAMBLE_COOLDOWN - (now - user["last_gamble"]["coinflip"]))
            return f"Coinflip on cooldown. Try again in {remain}s."
        user["last_gamble"]["coinflip"] = now
        win = secrets.choice([True, False])
        if win:
            user["balance"] += amount
            outcome = f"Heads! You win {amount} coins."
        else:
            user["balance"] -= amount
            outcome = f"Tails! You lose {amount} coins."
        self.save_state()
        return f"{self.active_user} gambled {amount} coins on coinflip. {outcome}"

    def command_gamble_slots(self, amount_text: str) -> str:
        user = self.user()
        max_bet = min(5000, max(100, int(user["balance"] * 0.15)))
        amount = self.parse_amount(amount_text, 10, max_bet)
        if amount is None:
            return f"Invalid bet amount. Bet between 10 and {max_bet} coins."
        if amount > user["balance"]:
            return "You do not have enough coins for that bet."
        now = time.time()
        if now - user["last_gamble"]["slots"] < SLOTS_COOLDOWN:
            remain = int(SLOTS_COOLDOWN - (now - user["last_gamble"]["slots"]))
            return f"Slots are on cooldown. Try again in {remain}s."
        user["last_gamble"]["slots"] = now
        reels = [self.weighted_choice(SLOT_SYMBOLS) for _ in range(3)]
        symbols = [r["symbol"] for r in reels]
        self.save_state()
        payout = self.slot_payout(symbols, amount)
        if payout > 0:
            user["balance"] += payout
            result = f"{' '.join(symbols)} — You win {payout} coins!"
        else:
            user["balance"] -= amount
            result = f"{' '.join(symbols)} — No matching combination. You lose {amount} coins."
        self.save_state()
        return f"{self.active_user} spun the slots. {result}"

    def weighted_choice(self, choices: List[Dict]) -> Dict:
        total_weight = sum(item["weight"] for item in choices)
        pick = secrets.randbelow(total_weight)
        running = 0
        for item in choices:
            running += item["weight"]
            if pick < running:
                return item
        return choices[-1]

    def slot_payout(self, symbols: List[str], bet: int) -> int:
        if len(set(symbols)) == 1:
            symbol = symbols[0]
            item = next(x for x in SLOT_SYMBOLS if x["symbol"] == symbol)
            return bet * item["payout"]
        if symbols[0] == symbols[1] or symbols[1] == symbols[2] or symbols[0] == symbols[2]:
            return int(bet * 0.5)
        return 0

    def command_slap(self, target: str) -> str:
        if not target.startswith("@"):
            return "Use s.slap @username to slap another user."
        return f"{self.active_user} slaps {target}! Ouch!"

    def command_ship(self, target: str) -> str:
        if not target.startswith("@"):
            return "Use s.ship @username to ship with another user."
        score = self.deterministic_percent(self.active_user, target)
        hearts = "❤️" * (score // 20 + 1)
        return f"Shipping {self.active_user} and {target}: {score}% compatible. {hearts}"

    def command_aura(self, target: str) -> str:
        if target.startswith("@"):
            target_key = target[1:]
        else:
            target_key = target
        score = self.deterministic_percent("aura", target_key)
        descriptors = [
            "mystical", "fiery", "calm", "glimmering", "chaotic", "golden",
            "shadowy", "sunny", "icy", "electric",
        ]
        descriptor = descriptors[score % len(descriptors)]
        return f"{target} has a {descriptor} aura with {score}% intensity."

    def deterministic_percent(self, *parts: str) -> int:
        seed = hashlib.sha256("::".join(parts).encode()).digest()
        value = int.from_bytes(seed[:4], "big")
        return (value % 100) + 1


if __name__ == "__main__":
    EconomyBot().run()
