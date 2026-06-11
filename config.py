# config.py — អានតម្លៃពី Environment Variables
import os
from dotenv import load_dotenv

load_dotenv()  # អាន .env file (local dev)

BOT_TOKEN = os.environ["BOT_TOKEN"]   # Telegram Bot Token
GROQ_KEY  = os.environ["GROQ_API_KEY"]  # Groq API Key
ADMIN_ID  = int(os.environ.get("ADMIN_ID", "0"))

VOICES = {
    "sreymom": "km-KH-SreymomNeural",   # 👩 ស្រី
    "piseth":  "km-KH-PisethNeural",    # 👨 ប្រុស
}
