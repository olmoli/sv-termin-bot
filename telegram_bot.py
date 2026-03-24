import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

import state
from config import TERMIN_URL, VERSION
from scraper import check_appointments

logger = logging.getLogger(__name__)

SUBSCRIBERS_FILE = Path("subscribers.json")


def _load() -> dict[int, bool]:
    if SUBSCRIBERS_FILE.exists():
        data = json.loads(SUBSCRIBERS_FILE.read_text())
        return {int(k): v for k, v in data.items()}
    return {}


def _save(subs: dict[int, bool]) -> None:
    SUBSCRIBERS_FILE.write_text(json.dumps(subs))


# Beim Start aus Datei laden
subscribers: dict[int, bool] = _load()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/start – Nutzer registrieren, Benachrichtigungen aktivieren und sofort prüfen."""
    chat_id = update.effective_chat.id
    subscribers[chat_id] = True
    _save(subscribers)
    logger.info("Nutzer %d hat den Bot gestartet.", chat_id)
    await update.message.reply_text(
        f"sv-termin-bot v{VERSION}\n\n"
        "Ich zeige dir gleich den nächsten freien Termin beim Straßenverkehrsamt Bochum.\n\n"
        "Danach bekommst du nur noch eine Nachricht, wenn ein früherer Termin frei wird.\n\n"
        "Mit /stop kannst du die Benachrichtigungen deaktivieren."
    )

    # Sofortcheck nach dem Registrieren
    try:
        should_notify = False
        notify_url = ""
        notify_date = ""

        async with state.check_lock:
            available, booking_url, first_date = await asyncio.wait_for(
                check_appointments(TERMIN_URL), timeout=120
            )
            if available:
                current_date = state.parse_date(first_date)
                should_notify = True
                notify_url = booking_url
                notify_date = first_date
                # Immer setzen – verhindert dass Monitor denselben Termin nochmal sendet
                if current_date:
                    state.last_notified_date = current_date

        if should_notify:
            await update.message.reply_text(
                f"Termin verfügbar!\n"
                f"Frühester Termin: {notify_date}\n\n"
                f"Jetzt buchen:\n{notify_url}\n\n"
                f"Einmal auf 'Weiter' klicken."
            )
        else:
            await update.message.reply_text("Aktuell kein freier Termin. Ich melde mich, sobald einer frei wird.")
    except Exception as e:
        logger.error("Fehler beim Sofortcheck nach /start: %s", e)


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/stop – Benachrichtigungen für diesen Nutzer deaktivieren."""
    chat_id = update.effective_chat.id
    subscribers[chat_id] = False
    _save(subscribers)
    logger.info("Nutzer %d hat den Bot gestoppt.", chat_id)
    await update.message.reply_text(
        "Benachrichtigungen deaktiviert. Mit /start wieder aktivieren."
    )


async def send_alert(application: Application, booking_url: str, first_date: str) -> None:
    """Sendet eine Termin-Benachrichtigung an alle aktiven Nutzer."""
    message = (
        f"Termin verfügbar!\n"
        f"Frühester Termin: {first_date}\n\n"
        f"Jetzt buchen:\n{booking_url}\n\n"
        f"Einmal auf 'Weiter' klicken."
    )
    active_users = [cid for cid, active in subscribers.items() if active]

    if not active_users:
        logger.info("Kein aktiver Nutzer – keine Benachrichtigung gesendet.")
        return

    for chat_id in active_users:
        try:
            await application.bot.send_message(chat_id=chat_id, text=message)
            logger.info("Benachrichtigung gesendet an %d.", chat_id)
        except Exception as e:
            logger.error("Fehler beim Senden an %d: %s", chat_id, e)


def build_application(token: str) -> Application:
    """Erstellt und konfiguriert die Telegram-Application."""
    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stop", stop))
    return application
