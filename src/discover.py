"""Interactive script to discover the @GenesisMassagesBot conversation flow.

Run this once to see every menu / button the bot offers, then use the output
to build your ``flow_config.json``.

Usage:
    python -m src.discover [--depth N] [--auth-file FILE]

On the FIRST run you will be prompted for your phone number and the
Telegram login code.  A session file is saved so subsequent runs won't
ask again.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os

from src.client import create_client, ensure_connected
from src.bot_interaction import discover_flow

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)

DEFAULT_AUTH_STEPS = [
    {"text": "/start"},
    {"share_phone": True},
    {"click_first_button": True},
]


async def main(depth: int, auth_file: str | None) -> None:
    if auth_file and os.path.exists(auth_file):
        with open(auth_file) as f:
            auth_steps = json.load(f)
        log.info("Loaded auth steps from %s", auth_file)
    else:
        auth_steps = DEFAULT_AUTH_STEPS
        log.info(
            "Using default auth steps: /start -> share phone -> confirm. "
            "Override with --auth-file if your bot's auth flow is different."
        )

    client = create_client()
    async with client:
        await ensure_connected(client)
        messages = await discover_flow(client, depth=depth, auth_steps=auth_steps)

    print("\n" + "=" * 60)
    print("DISCOVERY RESULTS (post-authentication menu)")
    print("=" * 60)
    for i, bm in enumerate(messages):
        print(f"\n--- Message {i} ---")
        print(f"Text: {bm.text[:500] if bm.text else '(empty)'}")
        if bm.buttons:
            print("Buttons:")
            for ri, row in enumerate(bm.buttons):
                for ci, btn in enumerate(row):
                    data_repr = btn["data"].hex() if btn["data"] else "None"
                    phone_tag = "  [SHARE PHONE]" if btn.get("request_phone") else ""
                    print(f"  [{ri},{ci}] \"{btn['text']}\"  data={data_repr}{phone_tag}")
    print("\n" + "=" * 60)

    print(
        "\nUse the button labels above to build your flow_config.json.\n"
        "The auth steps are already handled, so flow_config.json only needs\n"
        "the auth steps + the buttons to reach your specialist's schedule.\n"
        "\nExample flow_config.json:\n"
    )
    print(
        json.dumps(
            [
                {"text": "/start"},
                {"share_phone": True},
                {"click_first_button": True},
                {"button_text": "Example Button Label"},
            ],
            indent=2,
        )
    )
    print(
        "\nStep types:\n"
        '  {"text": "/start"}           — send a text message\n'
        '  {"share_phone": true}        — share your phone number with the bot\n'
        '  {"click_first_button": true}  — click the first button (for confirmations)\n'
        '  {"button_text": "Label"}     — click button matching this label\n'
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Discover massage bot menu flow")
    parser.add_argument("--depth", type=int, default=2, help="How deep to explore (default: 2)")
    parser.add_argument(
        "--auth-file",
        type=str,
        default=None,
        help="JSON file with auth steps to run before discovery (default: /start + share phone + confirm)",
    )
    args = parser.parse_args()
    asyncio.run(main(args.depth, args.auth_file))
