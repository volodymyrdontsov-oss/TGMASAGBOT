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

# Hard cap on how long a single slot-check iteration may run before we abort
# it. This is the safety net for hung Telethon network calls (see
# https://github.com/LonamiWebs/Telethon/issues/... — `client.get_messages`
# can occasionally block forever on a stalled connection, which would
# otherwise wedge the monitor loop until the process is restarted).
# Default: 180s (longer than the natural ~90s flow but much shorter than
# "forever"). Override with ITERATION_TIMEOUT env var if your flow is slower.
ITERATION_TIMEOUT: int = int(os.getenv("ITERATION_TIMEOUT", "180"))
MASSAGE_BOT_USERNAME: str = os.getenv("MASSAGE_BOT_USERNAME", "GenesisMassagesBot")
SESSION_NAME: str = os.getenv("SESSION_NAME", "massage_monitor_session")

NO_SLOTS_TEXT: str = os.getenv("NO_SLOTS_TEXT", "Немає вільних слотів").strip()

NOTIFY_BOT_TOKEN: str = os.getenv("NOTIFY_BOT_TOKEN", "").strip()
NOTIFY_CHAT_ID: str = os.getenv("NOTIFY_CHAT_ID", "").strip()
