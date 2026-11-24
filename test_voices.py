# test_voices.py
import os
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs

load_dotenv()

configured_id = os.getenv("ELEVENLABS_VOICE_ID", "").strip()

print("Voice ID loaded by Python:", repr(configured_id))

client = ElevenLabs(
    api_key=os.getenv("ELEVENLABS_API_KEY")
)

voices = client.voices.get_all()

print("\nVoices available to this API key:")
for voice in voices.voices:
    print(f"{voice.name} -> {voice.voice_id}")

if any(voice.voice_id == configured_id for voice in voices.voices):
    print("\nMATCH: The configured voice ID is available.")
else:
    print("\nNO MATCH: The configured voice ID is not in this account's voice list.")