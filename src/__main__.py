"""Entry point for the massage slot monitor.

Usage:
    python -m src
"""

import asyncio
import logging

from src.client import create_client, ensure_connected
from src.monitor import run_monitor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


async def main() -> None:
    client = create_client()
    async with client:
        await ensure_connected(client)
        await run_monitor(client)


if __name__ == "__main__":
    asyncio.run(main())
