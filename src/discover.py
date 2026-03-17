"""Interactive script to discover the @GenesisMassagesBot conversation flow.

Run this once to see every menu / button the bot offers, then use the output
to build your ``flow_config.json``.

Usage:
    python -m src.discover [--depth N]

On the FIRST run you will be prompted for your phone number and the
Telegram login code.  A session file is saved so subsequent runs won't
ask again.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging

from src.client import create_client, ensure_connected
from src.bot_interaction import discover_flow

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)


async def main(depth: int) -> None:
    client = create_client()
    async with client:
        await ensure_connected(client)
        messages = await discover_flow(client, depth=depth)

    print("\n" + "=" * 60)
    print("DISCOVERY RESULTS")
    print("=" * 60)
    for i, bm in enumerate(messages):
        print(f"\n--- Message {i} ---")
        print(f"Text: {bm.text[:300] if bm.text else '(empty)'}")
        if bm.buttons:
            print("Buttons:")
            for ri, row in enumerate(bm.buttons):
                for ci, btn in enumerate(row):
                    data_repr = btn["data"].hex() if btn["data"] else "None"
                    print(f"  [{ri},{ci}] \"{btn['text']}\"  data={data_repr}")
    print("\n" + "=" * 60)

    print(
        "\nUse the information above to create flow_config.json.\n"
        "Example:\n"
    )
    print(
        json.dumps(
            [
                {"text": "/start"},
                {"button_text": "Example Button Label"},
            ],
            indent=2,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Discover massage bot menu flow")
    parser.add_argument("--depth", type=int, default=2, help="How deep to explore (default: 2)")
    args = parser.parse_args()
    asyncio.run(main(args.depth))
