import logging

from telethon import TelegramClient

from src.config import TELEGRAM_API_ID, TELEGRAM_API_HASH, SESSION_NAME

log = logging.getLogger(__name__)


def create_client() -> TelegramClient:
    """Create and return a Telethon client instance."""
    return TelegramClient(SESSION_NAME, TELEGRAM_API_ID, TELEGRAM_API_HASH)


async def ensure_connected(client: TelegramClient) -> None:
    """Start the client and ensure it is authorized (interactive on first run)."""
    await client.start()
    me = await client.get_me()
    log.info("Logged in as %s (id=%s)", me.first_name, me.id)
