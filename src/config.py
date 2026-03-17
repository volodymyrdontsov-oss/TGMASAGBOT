import os
import sys

from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        print(f"ERROR: Required environment variable {name} is not set.")
        print(f"       Copy .env.example to .env and fill in the values.")
        sys.exit(1)
    return value


TELEGRAM_API_ID: int = int(_require("TELEGRAM_API_ID"))
TELEGRAM_API_HASH: str = _require("TELEGRAM_API_HASH")
SPECIALIST_NAME: str = _require("SPECIALIST_NAME")

CHECK_INTERVAL: int = int(os.getenv("CHECK_INTERVAL", "60"))
MASSAGE_BOT_USERNAME: str = os.getenv("MASSAGE_BOT_USERNAME", "GenesisMassagesBot")
SESSION_NAME: str = os.getenv("SESSION_NAME", "massage_monitor_session")

NOTIFY_BOT_TOKEN: str = os.getenv("NOTIFY_BOT_TOKEN", "").strip()
NOTIFY_CHAT_ID: str = os.getenv("NOTIFY_CHAT_ID", "").strip()
