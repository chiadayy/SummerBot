import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError(
        "Missing TELEGRAM_BOT_TOKEN. Set it in your .env file (do NOT commit .env)."
    )