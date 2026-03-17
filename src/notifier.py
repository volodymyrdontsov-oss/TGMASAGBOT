"""Send notifications when slots are found.

Two strategies:
  1. (default) Send a message to your own Saved Messages via the same userbot
     session – zero extra setup.
  2. (optional) Use a separate Telegram Bot API token to push to a specific
     chat/channel.  Set NOTIFY_BOT_TOKEN and NOTIFY_CHAT_ID.
"""

from __future__ import annotations

import logging
from urllib.request import urlopen, Request
from urllib.parse import quote

from telethon import TelegramClient

from src.bot_interaction import SlotInfo
from src.config import NOTIFY_BOT_TOKEN, NOTIFY_CHAT_ID

log = logging.getLogger(__name__)


def _format_slots(slots: list[SlotInfo]) -> str:
    lines = [
        "🔔 *Available massage slots found!*\n",
    ]
    for s in slots:
        parts = [f"• *{s.specialist}*"]
        if s.date:
            parts.append(f"  📅 {s.date}")
        if s.time:
            parts.append(f"  🕐 {s.time}")
        lines.append("\n".join(parts))
    lines.append("\nOpen @GenesisMassagesBot to book now!")
    return "\n\n".join(lines)


async def notify_via_saved_messages(client: TelegramClient, slots: list[SlotInfo]) -> None:
    text = _format_slots(slots)
    await client.send_message("me", text)
    log.info("Notification sent to Saved Messages")


def notify_via_bot_api(slots: list[SlotInfo]) -> None:
    if not NOTIFY_BOT_TOKEN or not NOTIFY_CHAT_ID:
        log.warning("NOTIFY_BOT_TOKEN / NOTIFY_CHAT_ID not configured; skipping bot notification")
        return

    text = _format_slots(slots)
    encoded = quote(text)
    url = (
        f"https://api.telegram.org/bot{NOTIFY_BOT_TOKEN}"
        f"/sendMessage?chat_id={NOTIFY_CHAT_ID}"
        f"&parse_mode=Markdown&text={encoded}"
    )
    req = Request(url, method="GET")
    with urlopen(req, timeout=10) as resp:
        if resp.status == 200:
            log.info("Notification sent via Bot API to chat %s", NOTIFY_CHAT_ID)
        else:
            log.warning("Bot API returned status %s", resp.status)


async def send_notification(client: TelegramClient, slots: list[SlotInfo]) -> None:
    await notify_via_saved_messages(client, slots)

    if NOTIFY_BOT_TOKEN and NOTIFY_CHAT_ID:
        try:
            notify_via_bot_api(slots)
        except Exception:
            log.exception("Failed to send notification via Bot API")
