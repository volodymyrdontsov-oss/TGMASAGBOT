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

RESPONSE_TIMEOUT = 15
POLL_INTERVAL = 0.4


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


# ---------------------------------------------------------------------------
# Low-level helpers with proper message-ID tracking
# ---------------------------------------------------------------------------

async def _get_baseline(client: TelegramClient, bot_entity) -> tuple[int, str]:
    """Return (id, text) of the most recent message in the chat."""
    msgs = await client.get_messages(bot_entity, limit=1)
    if msgs:
        return msgs[0].id, (msgs[0].text or msgs[0].message or "")
    return 0, ""


async def _wait_for_change(
    client: TelegramClient,
    bot_entity,
    baseline_id: int,
    baseline_text: str,
    watched_msg_id: int | None = None,
    timeout: int = RESPONSE_TIMEOUT,
) -> Message | None:
    """Wait for either a NEW message (id > baseline_id) or an EDIT to an
    existing message (watched_msg_id with changed text).

    This solves the core timing problem: inline button clicks typically
    edit the same message, while text commands and phone sharing create
    new messages. This function handles both cases simultaneously.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        msgs = await client.get_messages(bot_entity, limit=5)
        for msg in msgs:
            if not msg.out and msg.id > baseline_id:
                return msg

        if watched_msg_id is not None:
            refreshed = await client.get_messages(bot_entity, ids=watched_msg_id)
            if refreshed:
                current_text = refreshed.text or refreshed.message or ""
                if current_text != baseline_text:
                    return refreshed

        await asyncio.sleep(POLL_INTERVAL)
    return None


async def _wait_for_button_message(
    client: TelegramClient,
    bot_entity,
    after_id: int,
    timeout: int = RESPONSE_TIMEOUT,
) -> Message | None:
    """Wait for a new non-outgoing message with buttons and id > after_id."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        msgs = await client.get_messages(bot_entity, limit=5)
        for msg in msgs:
            if not msg.out and msg.id > after_id and msg.reply_markup:
                return msg
        await asyncio.sleep(POLL_INTERVAL)
    return None


async def _send_text_and_wait(
    client: TelegramClient,
    bot_entity,
    text: str,
) -> Message | None:
    """Send a text message and wait for the bot's response."""
    baseline_id, baseline_text = await _get_baseline(client, bot_entity)
    await client.send_message(bot_entity, text)
    await asyncio.sleep(0.5)
    return await _wait_for_change(
        client, bot_entity,
        baseline_id=baseline_id,
        baseline_text=baseline_text,
    )


async def _click_button_and_wait(
    client: TelegramClient,
    bot_entity,
    msg: Message,
    button_data: bytes,
) -> Message | None:
    """Click an inline callback button and wait for the bot's response.

    Checks for both a new message AND an edit to the clicked message,
    whichever comes first.
    """
    baseline_id, _ = await _get_baseline(client, bot_entity)
    original_text = msg.text or msg.message or ""
    await msg.click(data=button_data)
    await asyncio.sleep(0.5)
    return await _wait_for_change(
        client, bot_entity,
        baseline_id=baseline_id,
        baseline_text=original_text,
        watched_msg_id=msg.id,
    )


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

    baseline_id, baseline_text = await _get_baseline(client, bot_entity)

    await client.send_file(
        bot_entity,
        InputMediaContact(
            phone_number=phone,
            first_name=me.first_name or "",
            last_name=me.last_name or "",
            vcard="",
        ),
    )

    await asyncio.sleep(1)
    return await _wait_for_change(
        client, bot_entity,
        baseline_id=baseline_id,
        baseline_text=baseline_text,
    )


# ---------------------------------------------------------------------------
# Step execution (shared by check_slots, run_auth_steps)
# ---------------------------------------------------------------------------

async def _execute_step(
    client: TelegramClient,
    bot_entity,
    step: dict,
    last_msg: Message | None,
) -> Message | None:
    """Execute a single flow step and return the bot's response."""

    if step.get("share_phone"):
        log.info("Step: share_phone")
        return await _send_phone_contact(client, bot_entity)

    if step.get("click_first_button"):
        log.info("Step: click_first_button")
        return await _do_click_first_button(client, bot_entity, last_msg)

    if "text" in step:
        log.info("Step: send text '%s'", step["text"])
        return await _send_text_and_wait(client, bot_entity, step["text"])

    if "button_text" in step:
        target = step["button_text"]
        log.info("Step: click button matching '%s'", target)
        return await _do_click_button_by_text(client, bot_entity, last_msg, target)

    if "button_data" in step and last_msg is not None:
        data = step["button_data"]
        if isinstance(data, str):
            data = bytes.fromhex(data)
        log.info("Step: click button by data")
        return await _click_button_and_wait(client, bot_entity, last_msg, data)

    log.warning("Unknown step type: %s", step)
    return last_msg


async def _do_click_first_button(
    client: TelegramClient,
    bot_entity,
    last_msg: Message | None,
) -> Message | None:
    """Click the first available non-phone-request button.

    If the current message has no buttons, waits for one that does.
    """
    msg = last_msg
    baseline = last_msg.id if last_msg else 0

    if msg is not None:
        bm = BotMessage.from_message(msg)
        has_clickable = any(
            not btn.get("request_phone")
            for row in bm.buttons
            for btn in row
        )
        if not has_clickable:
            log.info("Current message has no clickable buttons, waiting for next...")
            msg = await _wait_for_button_message(client, bot_entity, after_id=baseline)

    if msg is None:
        log.warning("No message with buttons found")
        return None

    bm = BotMessage.from_message(msg)
    for row in bm.buttons:
        for btn in row:
            if btn.get("request_phone"):
                continue
            label = btn["text"]
            log.info("Auto-clicking button: [%s]", label)
            if btn["data"] is not None:
                return await _click_button_and_wait(client, bot_entity, msg, btn["data"])
            else:
                return await _send_text_and_wait(client, bot_entity, label)

    log.warning("No clickable buttons in message")
    return None


async def _do_click_button_by_text(
    client: TelegramClient,
    bot_entity,
    last_msg: Message | None,
    target_label: str,
) -> Message | None:
    """Click a button whose label contains *target_label*.

    If the current message doesn't have the button, waits for a new
    message that does (handles delayed bot responses).
    """
    target_lower = target_label.lower()
    baseline = last_msg.id if last_msg else 0

    # First try the current message
    if last_msg is not None:
        result = _find_button(last_msg, target_lower)
        if result is not None:
            msg, btn = result
            if btn["data"] is not None:
                return await _click_button_and_wait(client, bot_entity, msg, btn["data"])
            else:
                return await _send_text_and_wait(client, bot_entity, btn["text"])

    # Button not in current message — wait for a new message with buttons
    log.info("Button '%s' not in current message, waiting for new message...", target_label)
    deadline = time.monotonic() + RESPONSE_TIMEOUT
    while time.monotonic() < deadline:
        msgs = await client.get_messages(bot_entity, limit=5)
        for msg in msgs:
            if msg.out or msg.id <= baseline:
                continue
            result = _find_button(msg, target_lower)
            if result is not None:
                found_msg, btn = result
                log.info("Found button '%s' in message id=%d", target_label, found_msg.id)
                if btn["data"] is not None:
                    return await _click_button_and_wait(client, bot_entity, found_msg, btn["data"])
                else:
                    return await _send_text_and_wait(client, bot_entity, btn["text"])
        await asyncio.sleep(POLL_INTERVAL)

    log.warning("Button '%s' not found after waiting", target_label)
    return None


def _find_button(msg: Message, target_lower: str) -> tuple[Message, dict] | None:
    """Search for a button matching target_lower in the message."""
    bm = BotMessage.from_message(msg)
    for row in bm.buttons:
        for btn in row:
            if target_lower in btn["text"].lower():
                return msg, btn
    return None


# ---------------------------------------------------------------------------
# Auth & discovery
# ---------------------------------------------------------------------------

async def run_auth_steps(
    client: TelegramClient,
    auth_steps: list[dict],
) -> Message | None:
    """Execute authentication steps and return the bot's final response."""
    bot = await client.get_entity(MASSAGE_BOT_USERNAME)
    last_msg: Message | None = None

    for i, step in enumerate(auth_steps):
        log.info("Auth step %d/%d: %s", i + 1, len(auth_steps), step)
        last_msg = await _execute_step(client, bot, step, last_msg)
        if last_msg is None:
            log.warning("Auth failed at step %d: %s", i + 1, step)
            return None
        log.info("Auth step %d response: %s", i + 1, (last_msg.text or "")[:100])

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
        response = await _send_text_and_wait(client, bot, "/start")
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
                    resp = await _click_button_and_wait(client, bot_entity, parent_msg, data)
                else:
                    resp = await _send_text_and_wait(client, bot_entity, label)
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


# ---------------------------------------------------------------------------
# Monitoring: check_slots
# ---------------------------------------------------------------------------

async def check_slots(
    client: TelegramClient,
    button_sequence: list[dict],
) -> list[SlotInfo]:
    """Follow *button_sequence* to reach the slots page and return any
    available slots matching SPECIALIST_NAME."""
    bot = await client.get_entity(MASSAGE_BOT_USERNAME)
    specialist_lower = SPECIALIST_NAME.lower()
    last_msg: Message | None = None

    for i, step in enumerate(button_sequence):
        last_msg = await _execute_step(client, bot, step, last_msg)
        if last_msg is None:
            log.warning("Lost bot response at step %d: %s", i + 1, step)
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
