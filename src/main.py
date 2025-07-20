import discord
import random
import json
import os
import re
from datetime import datetime
from dotenv import load_dotenv
import sys

from chats import chats

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Always use absolute paths based on the script location, even if run from anywhere
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RES_DIR = os.path.abspath(os.path.join(BASE_DIR, '..', 'res'))
USER_NOTES_PATH = os.path.join(RES_DIR, 'user_notes.json')
GRUNTS_PATH = os.path.join(RES_DIR, 'grunts.txt')
GREETINGS_PATH = os.path.join(RES_DIR, 'greetings.txt')

class GruntBot(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        os.makedirs(RES_DIR, exist_ok=True)
        # Ensure grunts.txt exists
        if not os.path.exists(GRUNTS_PATH):
            with open(GRUNTS_PATH, 'w') as f:
                f.write("Me grunt!\n")
        self.user_notes_path = USER_NOTES_PATH
        self.grunts_path = GRUNTS_PATH
        self.greetings_path = GREETINGS_PATH
        self.user_data = self.load_user_data()
        self.keyword_map = {
            "food": ["pie", "snack", "eat", "hungry", "food"],
            "gold": ["treasure", "money", "rich", "coins", "gold"],
            "sleep": ["nap", "tired", "rest", "bed", "sleep"]
        }

    @property
    def chats(self):
        if not hasattr(self, '_chats'):
            self._chats = chats(timeout=300)
        return self._chats

    def load_user_data(self):
        if os.path.exists(self.user_notes_path):
            with open(self.user_notes_path, 'r') as file:
                return json.load(file)
        return {}

    def save_user_data(self):
        os.makedirs(os.path.dirname(self.user_notes_path), exist_ok=True)
        with open(self.user_notes_path, 'w') as file:
            json.dump(self.user_data, file, indent=2)

    def categorize_note(self, note):
        for category, keywords in self.keyword_map.items():
            if any(k in note.lower() for k in keywords):
                return category
        return None

    def get_wow_title(self, username):
        word_count = self.user_data.get(username, {}).get("word_count", 0)
        titles = [
            (20000, "Warchief"),
            (10000, "Champion"),
            (4000, "Veteran"),
            (2000, "Grunt"),
            (1000, "Scout"),
            (200, "Peon"),
            (0, "Newcomer"),
        ]
        for threshold, title in titles:
            if word_count >= threshold:
                return f"{title} ({word_count} words spoken)"
        return "Newcomer (0 words spoken)"

    def learn_from_user(self, username, message_content):
        category = self.categorize_note(message_content)
        new_note = {
            "text": message_content,
            "category": category,
            "timestamp": datetime.now().isoformat()
        }
        self.user_data.setdefault(username, {}).setdefault("history", []).append(new_note)
        self.save_user_data()

    def get_user_traits(self, username):
        history = self.user_data.get(username, {}).get("history", [])
        scores = {k: 0 for k in self.keyword_map}
        for note in history:
            cat = note.get("category")
            if cat in scores:
                scores[cat] += 1
        total = sum(scores.values())
        if total == 0:
            return {}
        return {k: round(v / total, 2) for k, v in scores.items() if v > 0}

    def detect_personality_shift(self, username):
        history = self.user_data.get(username, {}).get("history", [])
        if len(history) < 10:
            return None
        recent = history[-10:]
        total_counts = {k: 0 for k in self.keyword_map}
        recent_counts = {k: 0 for k in self.keyword_map}
        for note in history:
            cat = note.get("category")
            if cat in total_counts:
                total_counts[cat] += 1
        for note in recent:
            cat = note.get("category")
            if cat in recent_counts:
                recent_counts[cat] += 1
        drifted = []
        hist_len, rec_len = len(history), len(recent)
        for k in self.keyword_map:
            if hist_len and rec_len:
                total_pct = total_counts[k] / hist_len
                rec_pct = recent_counts[k] / rec_len
                if abs(rec_pct - total_pct) >= 0.3:
                    drifted.append(k)
        return drifted if drifted else None

    def inflect_response(self, response, username):
        drift  = self.detect_personality_shift(username)
        prefix_parts = []
        if drift and random.random() < 0.3:
            prefix_parts.append(f"GruntBot senses a quiet shift... more {', '.join(drift)} lately.")
        prefix = " ".join(prefix_parts)
        return f"{prefix} {response}" if prefix else response

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print("Bot is ready!")

    async def on_member_join(self, member):
        if member.guild.system_channel:
            try:
                with open(self.greetings_path) as f:
                    greets = [line.strip() for line in f if line.strip()]
                await member.guild.system_channel.send(
                    f"{member.mention}, {random.choice(greets)}"
                )
            except Exception as e:
                print(f"Greeting error: {e}")

    async def on_message(self, message):
        if message.author == self.user:
            return

        msg_lower = message.content.lower()
        username  = str(message.author.name)

        # --- Count words for every message ---
        words = len(message.content.split())
        self.user_data.setdefault(username, {}).setdefault("history", [])
        self.user_data[username]["word_count"] = self.user_data[username].get("word_count", 0) + words
        self.save_user_data()
        # -------------------------------------

        # Title
        if msg_lower.strip() == "grunt title":
            title = self.get_wow_title(username)
            await message.channel.send(f"{message.author.mention}, your title: **{title}**")
            return

        # Help
        if msg_lower.strip() == "grunt help":
            help_text = (
                "**🪓 GruntBot Command Guide 🪓**\n\n"
                "`grunt` — Get a random grunt.\n"
                "`grunt <message>` — Talk to GruntBot.\n"
                "`train grunt: <phrase>` — Teach GruntBot a new grunt.\n"
                "`list grunts` — See all learned grunts.\n"
                "`grunt note: <fact>` — Share something personal with GruntBot.\n"
                "`grunt title` — See your WoW-style rank based on all your words spoken.\n"
                "`grunt help` — Show this help message.\n\n"
                "🪙 **Ranks:** GruntBot tracks every word you say and assigns you a World of Warcraft–style title. "
                "Type `grunt title` to see your current rank!"
            )
            await message.channel.send(help_text)
            return

        # Train
        if msg_lower.startswith("train grunt:"):
            new_grunt = message.content[len("train grunt:"):].strip()
            if new_grunt:
                try:
                    with open(self.grunts_path, 'a') as f:
                        f.write(new_grunt + "\n")
                    await message.channel.send(f"GruntBot learns: \"{new_grunt}\" 🧠")
                except Exception as e:
                    print(f"Training error: {e}")
                    await message.channel.send("Training failed. Me tired.")
            else:
                await message.channel.send("No grunt provided!")
            return

        # Note
        if msg_lower.startswith("grunt note:"):
            note = message.content[len("grunt note:"):].strip()
            if note:
                self.learn_from_user(username, message.content)
                await message.channel.send(
                    f"{message.author.mention}, fine. GruntBot remembers your nonsense."
                )
            else:
                await message.channel.send("You no teach me anything.")
            return

        # List
        if msg_lower.strip() == "list grunts":
            try:
                with open(self.grunts_path) as f:
                    all_grunts = [line.strip() for line in f if line.strip()]
                if all_grunts:
                    formatted = "\n".join(f"- {g}" for g in all_grunts)
                    await message.channel.send(f"Here be GruntBot's wisdom:\n{formatted}")
                else:
                    await message.channel.send("Me forget all grunts 😢")
            except Exception as e:
                print(f"List error: {e}")
                await message.channel.send("Me can't find grunts…")
            return

        # Chat
        if re.search(r'\bgrunt\b', message.content, re.IGNORECASE):
            try:
                after = message.content[
                    re.search(r'\bgrunt\b', message.content, re.IGNORECASE).end():
                ].strip()

                # Random grunt
                if not after:
                    with open(self.grunts_path) as f:
                        choices = [line.strip() for line in f if line.strip()]
                    await message.channel.send(random.choice(choices))
                    return

                # LLM chat
                chat     = self.chats.get_chat(username)
                response = await chat.prompt(after)

                self.learn_from_user(username, message.content)
                response = self.inflect_response(response, username)
                await message.channel.send(response)

            except Exception as e:
                print(f"Response error: {e}")
                await message.channel.send("Me confused. Come back later.")
            return

intents = discord.Intents.default()
intents.message_content = True

client = GruntBot(intents=intents)
print(f"DISCORD_TOKEN loaded: {DISCORD_TOKEN}")
client.run(DISCORD_TOKEN)