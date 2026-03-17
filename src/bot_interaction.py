"""Interact with the massage booking bot to discover available slots.

The flow with @GenesisMassagesBot is unknown ahead of time, so this module
provides two operating modes:

1. **Discovery mode** (`discover_flow`): walks through the bot's menu tree,
   logging every message and inline-keyboard layout so you can map out
   the conversation flow once and configure the monitor.

2. **Monitor mode** (`check_slots`): follows a configured button-press
   sequence to reach the specialist's schedule page, parses the response
   for available time-slots, and returns them.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field

from telethon import TelegramClient
from telethon.tl.custom import Message
from telethon.tl.types import (
    InputMediaContact,
    KeyboardButtonCallback,
    KeyboardButtonRequestPhone,
    KeyboardButtonRow,
    ReplyInlineMarkup,
    ReplyKeyboardMarkup,
)

from src.config import MASSAGE_BOT_USERNAME, SPECIALIST_NAME

log = logging.getLogger(__name__)

RESPONSE_TIMEOUT = 15  # seconds to wait for a bot reply


@dataclass
class SlotInfo:
    specialist: str
    date: str
    time: str
    raw_text: str
    button_data: bytes | None = None


@dataclass
class BotMessage:
    """Structured representation of a single bot response."""

    text: str
    buttons: list[list[dict]] = field(default_factory=list)

    @classmethod
    def from_message(cls, msg: Message) -> "BotMessage":
        text = msg.text or msg.message or ""
        buttons: list[list[dict]] = []
        markup = msg.reply_markup
        if markup and isinstance(markup, ReplyInlineMarkup):
            for row in markup.rows:
                btn_row = []
                for btn in row.buttons:
                    btn_row.append(
                        {
                            "text": btn.text,
                            "data": btn.data if isinstance(btn, KeyboardButtonCallback) else None,
                            "request_phone": isinstance(btn, KeyboardButtonRequestPhone),
                        }
                    )
                buttons.append(btn_row)
        elif markup and isinstance(markup, ReplyKeyboardMarkup):
            for row in markup.rows:
                btn_row = []
                for btn in row.buttons:
                    btn_row.append(
                        {
                            "text": btn.text,
                            "data": None,
                            "request_phone": isinstance(btn, KeyboardButtonRequestPhone),
                        }
                    )
                buttons.append(btn_row)
        return cls(text=text, buttons=buttons)


async def _send_phone_contact(client: TelegramClient, bot_entity) -> Message | None:
    """Share the logged-in user's phone number as a contact with the bot."""
    me = await client.get_me()
    phone = me.phone
    if not phone:
        log.error("Cannot share phone: the logged-in account has no phone number")
        return None

    if not phone.startswith("+"):
        phone = "+" + phone

    log.info("Sharing phone number %s with bot", phone[:4] + "****")

    await client.send_file(
        bot_entity,
        InputMediaContact(
            phone_number=phone,
            first_name=me.first_name or "",
            last_name=me.last_name or "",
            vcard="",
        ),
    )

    await asyncio.sleep(2)

    deadline = time.monotonic() + RESPONSE_TIMEOUT
    last_msg = None
    while time.monotonic() < deadline:
        msgs = await client.get_messages(bot_entity, limit=1)
        if msgs:
            last_msg = msgs[0]
            if not last_msg.out:
                break
        await asyncio.sleep(1)

    return last_msg


async def _send_and_wait(
    client: TelegramClient,
    bot_entity,
    text: str | None = None,
    click_msg: Message | None = None,
    button_data: bytes | None = None,
    button_index: int | None = None,
) -> Message | None:
    """Send a message or click a button and wait for the bot's next response."""
    if text is not None:
        await client.send_message(bot_entity, text)
    elif click_msg is not None and button_data is not None:
        await click_msg.click(data=button_data)
    elif click_msg is not None and button_index is not None:
        await click_msg.click(button_index)
    else:
        return None

    await asyncio.sleep(1.5)

    deadline = time.monotonic() + RESPONSE_TIMEOUT
    last_msg = None
    while time.monotonic() < deadline:
        msgs = await client.get_messages(bot_entity, limit=1)
        if msgs:
            last_msg = msgs[0]
            if not last_msg.out:
                break
        await asyncio.sleep(1)

    return last_msg


async def discover_flow(client: TelegramClient, depth: int = 3) -> list[BotMessage]:
    """Walk the bot's menu tree up to *depth* levels, returning every response.

    This is meant to be run once interactively so you can see the full menu
    structure and decide which button sequence leads to the specialist list.
    """
    bot = await client.get_entity(MASSAGE_BOT_USERNAME)
    collected: list[BotMessage] = []

    log.info("=== Starting bot flow discovery (depth=%d) ===", depth)

    response = await _send_and_wait(client, bot, text="/start")
    if response is None:
        log.warning("No response to /start")
        return collected

    bm = BotMessage.from_message(response)
    collected.append(bm)
    _log_bot_message(bm, level=0)

    if depth > 0:
        await _explore_buttons(client, bot, response, bm, collected, current_depth=1, max_depth=depth)

    return collected


async def _explore_buttons(
    client: TelegramClient,
    bot_entity,
    parent_msg: Message,
    parent_bm: BotMessage,
    collected: list[BotMessage],
    current_depth: int,
    max_depth: int,
) -> None:
    """Recursively press each button in a message and record responses."""
    if current_depth > max_depth:
        return

    for row_idx, row in enumerate(parent_bm.buttons):
        for col_idx, btn in enumerate(row):
            label = btn["text"]
            data = btn["data"]
            is_phone = btn.get("request_phone", False)
            indent = "  " * current_depth
            log.info("%s-> Pressing button [%s] (data=%s%s)", indent, label, data, " [SHARE PHONE]" if is_phone else "")

            if is_phone:
                resp = await _send_phone_contact(client, bot_entity)
            elif data is not None:
                resp = await _send_and_wait(client, bot_entity, click_msg=parent_msg, button_data=data)
            else:
                resp = await _send_and_wait(client, bot_entity, text=label)

            if resp is None:
                log.info("%s   (no response)", indent)
                continue

            bm = BotMessage.from_message(resp)
            collected.append(bm)
            _log_bot_message(bm, level=current_depth)

            if bm.buttons and current_depth < max_depth:
                await _explore_buttons(
                    client, bot_entity, resp, bm, collected, current_depth + 1, max_depth
                )

            await asyncio.sleep(1)


def _log_bot_message(bm: BotMessage, level: int = 0) -> None:
    indent = "  " * level
    log.info("%sBOT TEXT: %s", indent, bm.text[:200] if bm.text else "(empty)")
    for ri, row in enumerate(bm.buttons):
        labels = []
        for b in row:
            tag = " [SHARE PHONE]" if b.get("request_phone") else ""
            labels.append(b["text"] + tag)
        btns = " | ".join(labels)
        log.info("%s  row %d: [ %s ]", indent, ri, btns)


async def check_slots(
    client: TelegramClient,
    button_sequence: list[dict],
) -> list[SlotInfo]:
    """Follow *button_sequence* to reach the slots page and return any
    available slots matching SPECIALIST_NAME.

    Each entry in *button_sequence* is a dict with either:
      - ``{"text": "/start"}``  – send this text message
      - ``{"button_text": "Book massage"}`` – click button whose label matches
      - ``{"button_data": b"..."}`` – click button with this callback data
    """
    bot = await client.get_entity(MASSAGE_BOT_USERNAME)
    specialist_lower = SPECIALIST_NAME.lower()

    last_msg: Message | None = None

    for step in button_sequence:
        if step.get("share_phone"):
            last_msg = await _send_phone_contact(client, bot)
        elif "text" in step:
            last_msg = await _send_and_wait(client, bot, text=step["text"])
        elif "button_text" in step and last_msg is not None:
            target_label = step["button_text"].lower()
            clicked = False
            bm = BotMessage.from_message(last_msg)
            for row in bm.buttons:
                for btn in row:
                    if target_label in btn["text"].lower():
                        last_msg = await _send_and_wait(
                            client, bot, click_msg=last_msg, button_data=btn["data"]
                        )
                        clicked = True
                        break
                if clicked:
                    break
            if not clicked:
                log.warning("Button '%s' not found in current message", step["button_text"])
                return []
        elif "button_data" in step and last_msg is not None:
            last_msg = await _send_and_wait(
                client, bot, click_msg=last_msg, button_data=step["button_data"]
            )

        if last_msg is None:
            log.warning("Lost bot response during slot check sequence")
            return []

    return _parse_slots(last_msg, specialist_lower)


def _parse_slots(msg: Message, specialist_filter: str) -> list[SlotInfo]:
    """Extract available slot information from the bot's response message.

    This is a heuristic parser – it looks for the specialist name in either
    the message text or the button labels and extracts time information.
    Adjust the parsing logic once the bot's actual response format is known.
    """
    slots: list[SlotInfo] = []
    text = msg.text or msg.message or ""

    bm = BotMessage.from_message(msg)

    for row in bm.buttons:
        for btn in row:
            label = btn["text"].lower()
            if specialist_filter in label or specialist_filter in text.lower():
                slots.append(
                    SlotInfo(
                        specialist=SPECIALIST_NAME,
                        date="",
                        time=btn["text"],
                        raw_text=text,
                        button_data=btn["data"],
                    )
                )

    if not slots and specialist_filter in text.lower():
        for line in text.splitlines():
            stripped = line.strip()
            if any(ch.isdigit() for ch in stripped) and (":" in stripped or "-" in stripped):
                slots.append(
                    SlotInfo(
                        specialist=SPECIALIST_NAME,
                        date="",
                        time=stripped,
                        raw_text=text,
                    )
                )

    return slots
