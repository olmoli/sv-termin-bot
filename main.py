import asyncio
import logging
import os
import time

from dotenv import load_dotenv

from bot import send_notification
from monitor import check_for_appointments

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("sv_termin_bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def main():
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    termin_url = os.getenv("TERMIN_URL")
    interval = int(os.getenv("CHECK_INTERVAL", "60"))

    if not all([bot_token, chat_id, termin_url]):
        logger.error(
            "Fehlende Konfiguration. Bitte .env-Datei prüfen (TELEGRAM_BOT_TOKEN, "
            "TELEGRAM_CHAT_ID, TERMIN_URL)."
        )
        return

    logger.info("sv-termin-bot gestartet. Prüfe alle %d Sekunden: %s", interval, termin_url)

    last_status = None

    while True:
        available, message = check_for_appointments(termin_url)
        logger.info(message)

        # Nur benachrichtigen, wenn sich der Status geändert hat
        if available != last_status:
            last_status = available
            if available:
                alert = f"Termin verfügbar! {message}\n\nJetzt buchen: {termin_url}"
                asyncio.run(send_notification(bot_token, chat_id, alert))
            else:
                logger.info("Kein Termin verfügbar – keine Benachrichtigung.")

        time.sleep(interval)


if __name__ == "__main__":
    main()
