"""Main monitoring loop that periodically checks for available massage slots."""

from __future__ import annotations

import asyncio
import json
import logging
import os

from telethon import TelegramClient
from telethon.errors import FloodWaitError

from src.bot_interaction import check_slots, SlotInfo
from src.config import CHECK_INTERVAL, ITERATION_TIMEOUT, SPECIALIST_NAME
from src.notifier import send_notification
from src.watchdog import alive as watchdog_alive

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
            slots = await asyncio.wait_for(
                check_slots(client, button_sequence),
                timeout=ITERATION_TIMEOUT,
            )

            new_slots = [s for s in slots if _slot_key(s) not in _already_notified]

            if new_slots:
                log.info("Found %d new slot(s)!", len(new_slots))
                await send_notification(client, new_slots)
                for s in new_slots:
                    _already_notified.add(_slot_key(s))
            else:
                log.info("No new slots found. Will check again in %ds.", CHECK_INTERVAL)

        except asyncio.TimeoutError:
            # Iteration exceeded ITERATION_TIMEOUT — almost always a hung
            # Telethon network call. Drop this iteration and try again next
            # tick; the in-flight task is cancelled by `wait_for`.
            log.warning(
                "Slot check exceeded %ds and was aborted. Will retry next tick.",
                ITERATION_TIMEOUT,
            )

        except FloodWaitError as e:
            # Telegram has rate-limited us. Sleep for *exactly* the requested
            # duration (plus a small buffer) instead of pounding the API
            # every CHECK_INTERVAL seconds while still in the wait window.
            wait = int(e.seconds) + 5
            log.warning(
                "Telegram FloodWait: must wait %ds before retrying", wait,
            )
            # Pet the watchdog in chunks so a multi-minute FloodWait doesn't
            # trip the systemd WatchdogSec timer — we are healthy, just
            # rate-limited.
            remaining = wait
            while remaining > 0:
                watchdog_alive()
                chunk = min(remaining, 60)
                await asyncio.sleep(chunk)
                remaining -= chunk
            continue  # skip the trailing sleep below — we already waited

        except Exception:
            log.exception("Error during slot check")

        watchdog_alive()
        await asyncio.sleep(CHECK_INTERVAL)
