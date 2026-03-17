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

from src.config import MASSAGE_BOT_USERNAME, NO_SLOTS_TEXT, SPECIALIST_NAME

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


async def _wait_for_buttons(
    client: TelegramClient,
    bot_entity,
    timeout: int = RESPONSE_TIMEOUT,
) -> Message | None:
    """Wait until the bot sends a message that has buttons (inline or keyboard).

    Useful after steps like share_phone where the bot may send a plain text
    acknowledgement first, then a separate message with confirmation buttons.
    """
    deadline = time.monotonic() + timeout
    seen_ids: set[int] = set()

    while time.monotonic() < deadline:
        msgs = await client.get_messages(bot_entity, limit=3)
        for msg in msgs:
            if msg.out or msg.id in seen_ids:
                continue
            seen_ids.add(msg.id)
            if msg.reply_markup:
                log.info("Found message with buttons: %s", (msg.text or "")[:100])
                return msg
        await asyncio.sleep(1)

    return None


async def _click_first_available_button(
    client: TelegramClient,
    bot_entity,
    last_msg: Message | None,
) -> Message | None:
    """Find and click the first non-phone-request button.

    If *last_msg* has no buttons, waits for the bot to send a new message
    that does have buttons (the bot may send multiple messages in sequence,
    e.g. acknowledgement first, then confirmation with buttons).
    """
    msg = last_msg
    if msg is not None:
        bm = BotMessage.from_message(msg)
        has_clickable = any(
            not btn.get("request_phone")
            for row in bm.buttons
            for btn in row
        )
        if not has_clickable:
            log.info("Current message has no clickable buttons, waiting for next message...")
            msg = await _wait_for_buttons(client, bot_entity, timeout=RESPONSE_TIMEOUT)
    else:
        log.info("No current message, waiting for a message with buttons...")
        msg = await _wait_for_buttons(client, bot_entity, timeout=RESPONSE_TIMEOUT)

    if msg is None:
        log.warning("No message with buttons found after waiting")
        return None

    bm = BotMessage.from_message(msg)
    for row in bm.buttons:
        for btn in row:
            if btn.get("request_phone"):
                continue
            label = btn["text"]
            log.info("Auto-clicking button: [%s]", label)
            if btn["data"] is not None:
                return await _send_and_wait(
                    client, bot_entity, click_msg=msg, button_data=btn["data"]
                )
            else:
                return await _send_and_wait(client, bot_entity, text=label)

    log.warning("No clickable buttons found in message")
    return None


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


async def run_auth_steps(
    client: TelegramClient,
    auth_steps: list[dict],
) -> Message | None:
    """Execute authentication steps and return the bot's final response.

    Uses the same step format as check_slots: text, share_phone,
    click_first_button, button_text.
    """
    bot = await client.get_entity(MASSAGE_BOT_USERNAME)
    last_msg: Message | None = None

    for step in auth_steps:
        if step.get("share_phone"):
            last_msg = await _send_phone_contact(client, bot)
        elif step.get("click_first_button"):
            last_msg = await _click_first_available_button(client, bot, last_msg)
        elif "text" in step:
            last_msg = await _send_and_wait(client, bot, text=step["text"])
        elif "button_text" in step and last_msg is not None:
            target_label = step["button_text"].lower()
            bm = BotMessage.from_message(last_msg)
            for row in bm.buttons:
                for btn in row:
                    if target_label in btn["text"].lower():
                        if btn["data"] is not None:
                            last_msg = await _send_and_wait(
                                client, bot, click_msg=last_msg, button_data=btn["data"]
                            )
                        else:
                            last_msg = await _send_and_wait(client, bot, text=btn["text"])
                        break

        if last_msg is None:
            log.warning("Lost bot response during auth step: %s", step)
            return None

    return last_msg


async def discover_flow(
    client: TelegramClient,
    depth: int = 3,
    auth_steps: list[dict] | None = None,
) -> list[BotMessage]:
    """Walk the bot's menu tree up to *depth* levels, returning every response.

    If *auth_steps* is provided, those steps are executed first (e.g. /start,
    share phone, confirm identity) and discovery begins from the post-auth
    menu. Otherwise, discovery starts from /start.
    """
    bot = await client.get_entity(MASSAGE_BOT_USERNAME)
    collected: list[BotMessage] = []

    if auth_steps:
        log.info("=== Running %d auth step(s) before discovery ===", len(auth_steps))
        response = await run_auth_steps(client, auth_steps)
        if response is None:
            log.warning("Auth steps failed, no response from bot")
            return collected
        log.info("=== Auth complete. Starting discovery (depth=%d) ===", depth)
    else:
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

            if is_phone:
                log.info("%s   [SHARE PHONE button — skipping during discovery]", indent)
                continue

            log.info("%s-> Pressing button [%s] (data=%s)", indent, label, data)

            try:
                if data is not None:
                    resp = await _send_and_wait(client, bot_entity, click_msg=parent_msg, button_data=data)
                else:
                    resp = await _send_and_wait(client, bot_entity, text=label)
            except Exception as e:
                log.warning("%s   Error clicking button [%s]: %s", indent, label, e)
                continue

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
        elif step.get("click_first_button"):
            last_msg = await _click_first_available_button(client, bot, last_msg)
            if last_msg is None:
                log.warning("click_first_button failed — no buttons found")
                return []
        elif "text" in step:
            last_msg = await _send_and_wait(client, bot, text=step["text"])
        elif "button_text" in step and last_msg is not None:
            target_label = step["button_text"].lower()
            clicked = False
            bm = BotMessage.from_message(last_msg)
            for row in bm.buttons:
                for btn in row:
                    if target_label in btn["text"].lower():
                        if btn["data"] is not None:
                            last_msg = await _send_and_wait(
                                client, bot, click_msg=last_msg, button_data=btn["data"]
                            )
                        else:
                            last_msg = await _send_and_wait(client, bot, text=btn["text"])
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
    """Check the bot's response for available slots.

    If the response contains NO_SLOTS_TEXT (e.g. "Немає вільних слотів"),
    there are no available slots.  Any other response means slots are
    available — return a SlotInfo with the full response text and any
    buttons the bot shows (likely dates/times to book).
    """
    text = msg.text or msg.message or ""
    no_slots_indicator = NO_SLOTS_TEXT.lower()

    if no_slots_indicator in text.lower():
        log.info("Bot says no slots available: %s", text[:150])
        return []

    log.info("Slots appear to be available! Response: %s", text[:300])

    bm = BotMessage.from_message(msg)

    slots: list[SlotInfo] = []
    for row in bm.buttons:
        for btn in row:
            if btn["text"] == "« Назад":
                continue
            slots.append(
                SlotInfo(
                    specialist=SPECIALIST_NAME,
                    date="",
                    time=btn["text"],
                    raw_text=text,
                    button_data=btn["data"],
                )
            )

    if not slots:
        slots.append(
            SlotInfo(
                specialist=SPECIALIST_NAME,
                date="",
                time="",
                raw_text=text,
            )
        )

    return slots
