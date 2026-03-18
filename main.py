import asyncio
import logging

from config import TELEGRAM_TOKEN, CHECK_INTERVAL, TERMIN_URL
from scraper import check_appointments
from telegram_bot import build_application, send_alert

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("sv_termin_bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


async def monitor_loop(application) -> None:
    """
    Prüft alle CHECK_INTERVAL Sekunden, ob ein Termin frei ist.
    Sendet nur eine Benachrichtigung, wenn sich der Status von
    'nicht verfügbar' auf 'verfügbar' ändert (verhindert Spam).
    """
    last_available = False  # Bonus: doppelte Benachrichtigungen verhindern

    logger.info(
        "Monitor gestartet. Prüfe alle %d Sekunden: %s",
        CHECK_INTERVAL,
        TERMIN_URL,
    )

    while True:
        try:
            available = await check_appointments(TERMIN_URL)

            if available and not last_available:
                # Status wechselte von 'kein Termin' auf 'Termin frei'
                logger.info("Termin verfügbar! Sende Benachrichtigungen...")
                await send_alert(application, TERMIN_URL)
            elif not available and last_available:
                logger.info("Termin nicht mehr verfügbar.")
            else:
                logger.info(
                    "Status unverändert: %s",
                    "verfügbar" if available else "kein Termin",
                )

            last_available = available

        except Exception as e:
            logger.error("Fehler im Monitor-Loop: %s", e)

        await asyncio.sleep(CHECK_INTERVAL)


async def main() -> None:
    application = build_application(TELEGRAM_TOKEN)

    # Telegram-Bot und Monitor-Loop gleichzeitig starten
    async with application:
        await application.start()
        await application.updater.start_polling()

        logger.info("Bot läuft. Drücke Ctrl+C zum Beenden.")

        try:
            await monitor_loop(application)
        except (KeyboardInterrupt, asyncio.CancelledError):
            logger.info("Bot wird beendet...")
        finally:
            await application.updater.stop()
            await application.stop()


if __name__ == "__main__":
    asyncio.run(main())
