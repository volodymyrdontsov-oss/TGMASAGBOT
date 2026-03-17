"""Main monitoring loop that periodically checks for available massage slots."""

from __future__ import annotations

import asyncio
import json
import logging
import os

from telethon import TelegramClient

from src.bot_interaction import check_slots, SlotInfo
from src.config import CHECK_INTERVAL, SPECIALIST_NAME
from src.notifier import send_notification

log = logging.getLogger(__name__)

FLOW_CONFIG_FILE = "flow_config.json"

_already_notified: set[str] = set()


def _slot_key(slot: SlotInfo) -> str:
    return f"{slot.specialist}|{slot.date}|{slot.time}"


def load_button_sequence() -> list[dict]:
    """Load the button-press sequence from flow_config.json.

    The file should contain a JSON array of step objects, for example:

        [
            {"text": "/start"},
            {"button_text": "Book massage"},
            {"button_text": "Choose specialist"},
            {"button_text": "Anna"}
        ]

    See README for details on how to discover the correct sequence.
    """
    if not os.path.exists(FLOW_CONFIG_FILE):
        log.error(
            "Flow config file '%s' not found. "
            "Run `python -m src.discover` first to map the bot's menu, "
            "then create this file. See README for instructions.",
            FLOW_CONFIG_FILE,
        )
        raise SystemExit(1)

    with open(FLOW_CONFIG_FILE) as f:
        seq = json.load(f)

    if not isinstance(seq, list) or len(seq) == 0:
        log.error("flow_config.json must be a non-empty JSON array of step objects")
        raise SystemExit(1)

    return seq


async def run_monitor(client: TelegramClient) -> None:
    button_sequence = load_button_sequence()
    log.info(
        "Starting monitor – checking every %ds for specialist '%s'",
        CHECK_INTERVAL,
        SPECIALIST_NAME,
    )

    while True:
        try:
            slots = await check_slots(client, button_sequence)

            new_slots = [s for s in slots if _slot_key(s) not in _already_notified]

            if new_slots:
                log.info("Found %d new slot(s)!", len(new_slots))
                await send_notification(client, new_slots)
                for s in new_slots:
                    _already_notified.add(_slot_key(s))
            else:
                log.info("No new slots found. Will check again in %ds.", CHECK_INTERVAL)

        except Exception:
            log.exception("Error during slot check")

        await asyncio.sleep(CHECK_INTERVAL)
