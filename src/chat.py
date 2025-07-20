import os
import time

from google import genai
from google.genai import types

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

class chatsvc():
	def __init__(self, name, display_name, context):
		self._name = name
		self._display_name = display_name
		self._context = context
		self._last_activity = time.time()
		self._client = genai.Client(api_key=GOOGLE_API_KEY)

	@property
	def name(self):
		return self._name

	@property
	def display_name(self):
		return self._display_name

	@property
	def context(self):
		return self._context

	@property
	def is_active(self):
		# Check if the chat has been active in the last 5 minutes
		return (time.time() - self._last_activity) < 300

	async def prompt(self, message):
		try:
			# Update last activity time
			self._last_activity = time.time()
   
			response = self._client.models.generate_content(
				model="gemini-2.5-flash",
				config=types.GenerateContentConfig(
					system_instruction=self._context,),
				contents=message
			)

			return response.text

		except Exception as e:
			print(f"Error: {e}")
