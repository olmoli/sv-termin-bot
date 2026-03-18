import asyncio
import logging

from config import TELEGRAM_TOKEN, CHECK_INTERVAL, TERMIN_URL, VERSION
from scraper import check_appointments
from telegram_bot import build_application, send_alert
import state

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
    logger.info(
        "Monitor gestartet. Prüfe alle %d Sekunden: %s",
        CHECK_INTERVAL,
        TERMIN_URL,
    )

    while True:
        try:
            should_notify = False
            notify_url = ""
            notify_date = ""

            async with state.check_lock:
                available, booking_url, first_date = await check_appointments(TERMIN_URL)

                if available:
                    current_date = state.parse_date(first_date)
                    if current_date and (
                        state.last_notified_date is None
                        or current_date < state.last_notified_date
                    ):
                        should_notify = True
                        notify_url = booking_url
                        notify_date = first_date
                        state.last_notified_date = current_date
                        logger.info("Neuer frühester Termin: %s – sende Benachrichtigung.", first_date)
                    else:
                        logger.info("Bekannter oder späterer Termin (%s) – keine Benachrichtigung.", first_date)
                else:
                    if state.last_notified_date is not None:
                        logger.info("Keine Termine mehr verfügbar – Reset.")
                        state.last_notified_date = None
                    else:
                        logger.info("Kein Termin verfügbar.")

            if should_notify:
                await send_alert(application, notify_url, notify_date)

        except Exception as e:
            logger.error("Fehler im Monitor-Loop: %s", e)

        await asyncio.sleep(CHECK_INTERVAL)


async def main() -> None:
    application = build_application(TELEGRAM_TOKEN)

    async with application:
        await application.start()
        await application.updater.start_polling()

        logger.info("sv-termin-bot v%s gestartet.", VERSION)

        try:
            await monitor_loop(application)
        except (KeyboardInterrupt, asyncio.CancelledError):
            logger.info("Bot wird beendet...")
        finally:
            await application.updater.stop()
            await application.stop()


if __name__ == "__main__":
    asyncio.run(main())
