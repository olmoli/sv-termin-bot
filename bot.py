import asyncio
import logging
import os

from telegram import Bot
from telegram.error import TelegramError

logger = logging.getLogger(__name__)


async def send_notification(bot_token: str, chat_id: str, message: str) -> None:
    """Sendet eine Telegram-Nachricht."""
    try:
        bot = Bot(token=bot_token)
        await bot.send_message(chat_id=chat_id, text=message)
        logger.info("Benachrichtigung gesendet: %s", message)
    except TelegramError as e:
        logger.error("Fehler beim Senden der Telegram-Nachricht: %s", e)
