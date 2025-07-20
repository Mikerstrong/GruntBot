import json

from chat import chatsvc
from utils import first

class chats:
	def __init__(self, timeout):
		self._chats = {}
		self._timeout = timeout

	def get_chat(self, name):
		chat = self._chats.get(name, None)
      
		if not chat:
			profile = self.load_profile(name)
			display_name = profile['displayName'] if profile and 'displayName' in profile else name
			hint = self.load_all_profile_hints()
			chat = chatsvc(name, display_name, f"You are an Orc Warrior from World of Warcraft. {display_name} is addressing you, {hint}, answer in one to four sentences" if hint else "You are an Orc Warrior from World of Warcraft, answer in one to four sentences")
			self._chats[name] = chat
		elif not chat.is_active:
			del chat
			chat = None
			self.chats[name] = None
      
		if not chat:
			profile = self.load_profile(name)
			display_name = profile['displayName'] if profile and 'displayName' in profile else name
			hint = self.load_all_profile_hints()
			chat = chatsvc(name, display_name, f"You are an Orc Warrior from World of Warcraft. {display_name} is addressing you, {hint}, answer in one to four sentences" if hint else "You are an Orc Warrior from World of Warcraft, answer in one to four sentences")
			self._chats[name] = chat

		return chat

	def load_profile(self, name):
		try:
			with open('./res/profiles.json') as f:
				profiles = json.load(f)
			profile = first(x for x in profiles if x['name'].lower() == name.lower())
			return profile
		except FileNotFoundError:
			print("Profile file not found.")
			return None
		except json.JSONDecodeError:
			print("Error decoding JSON from profile file.")
			return None
		except StopIteration:
			print(f"No profile found for {name}.")
			return None

	def load_all_profile_hints(self):
		try:
			with open('./res/profiles.json') as f:
				profiles = json.load(f)
			hints = ""
			for profile in profiles:
				if hints:
					hints += ", "
				hints += profile['hint']
			return hints
		except:
			return None

	def load_profile_hint(self, name):
		try:
			with open('./res/profiles.json') as f:
				profiles = json.load(f)
			profile = first(x for x in profiles if x['name'].lower() == name.lower())
			return profile['hint']
		except FileNotFoundError:
			print("Profile file not found.")
			return None
		except json.JSONDecodeError:
			print("Error decoding JSON from profile file.")
			return None
		except StopIteration:
			print(f"No profile found for {name}.")
			return None