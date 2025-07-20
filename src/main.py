import discord
import random
import json
import os
import re
from datetime import datetime
from dotenv import load_dotenv

from chats import chats
from chat import chatsvc

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

class GruntBot(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_notes_path = './res/user_notes.json'
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
        with open(self.user_notes_path, 'w') as file:
            json.dump(self.user_data, file, indent=2)

    def categorize_note(self, note):
        for category, keywords in self.keyword_map.items():
            if any(k in note.lower() for k in keywords):
                return category
        return None

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
        trait_scores = {key: 0 for key in self.keyword_map.keys()}

        for note in history:
            category = note.get("category")
            if category in trait_scores:
                trait_scores[category] += 1

        total = sum(trait_scores.values())
        if total == 0:
            return {}

        return {
            key: round(score / total, 2) for key, score in trait_scores.items() if score > 0
        }

    def detect_personality_shift(self, username):
        history = self.user_data.get(username, {}).get("history", [])
        if len(history) < 10:
            return None

        recent = history[-10:]
        recent_counts = {key: 0 for key in self.keyword_map.keys()}
        total_counts = {key: 0 for key in self.keyword_map.keys()}

        for note in history:
            cat = note.get("category")
            if cat in total_counts:
                total_counts[cat] += 1

        for note in recent:
            cat = note.get("category")
            if cat in recent_counts:
                recent_counts[cat] += 1

        drifted = []
        for cat in self.keyword_map.keys():
            total_pct = total_counts[cat] / len(history)
            recent_pct = recent_counts[cat] / len(recent)
            if abs(recent_pct - total_pct) >= 0.3:
                drifted.append(cat)

        return drifted if drifted else None

    def get_time_flavor(self):
        hour = datetime.now().hour
        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 22:
            return "evening"
        else:
            return "late_night"

    def inflect_response(self, response, username):
        traits = self.get_user_traits(username)
        flavor = self.get_time_flavor()
        drift = self.detect_personality_shift(username)

        prefixes = []

        if flavor == "morning":
            prefixes.append("Rise and grunt!")
        elif flavor == "afternoon":
            prefixes.append("GruntBot thinks your gold pile needs tending.")
        elif flavor == "evening":
            prefixes.append("Evening whispers carry true strength.")
        elif flavor == "late_night":
            prefixes.append("Moonlight grunts echo in your soul...")

        if traits.get("gold", 0) >= 0.5:
            prefixes.append("You sound like a mighty merchant today.")
        elif traits.get("food", 0) >= 0.5:
            prefixes.append("Speak quick — before you wander off in search of feast.")
        elif traits.get("sleep", 0) >= 0.5:
            prefixes.append("Another dreamy whisper from the shadows...")

        if drift:
            prefixes.append("GruntBot senses change... More " + ", ".join(drift) + " lately.")

        return " ".join(prefixes) + " " + response

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print("Bot is ready!")

    async def on_member_join(self, member):
        if member.guild.system_channel is not None:
            try:
                with open('./res/greetings.txt') as grunts_file:
                    contents = grunts_file.readlines()
                grunts = [line.strip() for line in contents if line.strip()]
                grunt = random.choice(grunts)
                await member.guild.system_channel.send(f"{member.mention}, {grunt}")
            except Exception as e:
                print(f"Greeting error: {e}")

    async def on_message(self, message):
        if message.author == self.user:
            return

        msg_lower = message.content.lower()
        username = str(message.author.name)

        if msg_lower.strip() == "grunt help":
            help_text = (
                "**🪓 GruntBot Command Guide 🪓**\n\n"
                "`grunt` — Get a random grunt.\n"
                "`grunt <message>` — Talk to GruntBot.\n"
                "`train grunt: <phrase>` — Teach GruntBot.\n"
                "`list grunts` — See learned grunts.\n"
                "`grunt note: <fact>` — Share something personal.\n"
                "`grunt help` — You just did.\n"
            )
            await message.channel.send(help_text)
            return

        if msg_lower.startswith("train grunt:"):
            new_grunt = message.content[msg_lower.find("train grunt:") + len("train grunt:"):].strip()
            if new_grunt:
                try:
                    with open('./res/grunts.txt', 'a') as grunts_file:
                        grunts_file.write(new_grunt + "\n")
                    await message.channel.send(f"GruntBot learns: \"{new_grunt}\" 🧠")
                except Exception as e:
                    print(f"Training error: {e}")
                    await message.channel.send("Training failed. Me tired.")
            else:
                await message.channel.send("No grunt provided!")
            return

        if msg_lower.startswith("grunt note:"):
            note = message.content[msg_lower.find("grunt note:") + len("grunt note:"):].strip()
            if note:
                self.learn_from_user(username, message.content)
                await message.channel.send(f"{message.author.mention}, fine. GruntBot remembers your nonsense.")
            else:
                await message.channel.send("You no teach me anything.")
            return

        if msg_lower.strip() == "list grunts":
            try:
                with open('./res/grunts.txt') as grunts_file:
                    grunts = [line.strip() for line in grunts_file.readlines() if line.strip()]
                if grunts:
                    formatted = "\n".join(f"- {g}" for g in grunts)
                    await message.channel.send(f"Here be GruntBot's wisdom:\n{formatted}")
                else:
                    await message.channel.send("Me forget all grunts 😢")
            except Exception as e:
                print(f"List error: {e}")
                await message.channel.send("Me can't find grunts...")
            return

        match = re.search(r'\bgrunt\b', message.content, re.IGNORECASE)
        if match:
            try:
                after_grunt = message.content[match.end():].strip()

                if after_grunt == "":
                    with open('./res/grunts.txt') as grunts_file:
                        grunts = [line.strip() for line in grunts_file.readlines() if line.strip()]
                    grunt = random.choice(grunts)
                    await message.channel.send(grunt)
                    return

                chat = self.chats.get_chat(username)
                response = await chat.prompt(after_grunt)

                self.learn_from_user(username, message.content)
                response = self.inflect_response(response, username)

                await message.channel.send(response)

            except Exception as e:
                print(f"Grunt response error: {e}")
                await message.channel.send("Me confused. Come back later.")

intents = discord.Intents.default()
intents.message_content = True

client = GruntBot(intents=intents)
print(f"DISCORD_TOKEN loaded: {DISCORD_TOKEN} | Type: {type(DISCORD_TOKEN)}")
client.run(DISCORD_TOKEN)