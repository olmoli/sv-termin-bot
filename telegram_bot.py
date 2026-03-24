import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

import state
from config import TERMIN_URL, VERSION
from scraper import check_appointments

logger = logging.getLogger(__name__)

SUBSCRIBERS_FILE = Path("subscribers.json")

WINDOW_OPTIONS = [
    ("1 Tag", 1),
    ("3 Tage", 3),
    ("7 Tage", 7),
    ("14 Tage", 14),
    ("Beliebig", None),
]


def _load() -> dict[int, bool]:
    if SUBSCRIBERS_FILE.exists():
        data = json.loads(SUBSCRIBERS_FILE.read_text())
        return {int(k): v for k, v in data.items()}
    return {}


def _save(subs: dict[int, bool]) -> None:
    SUBSCRIBERS_FILE.write_text(json.dumps(subs))


# Beim Start aus Datei laden
subscribers: dict[int, bool] = _load()


def _window_label() -> str:
    if state.max_days_ahead is None:
        return "Beliebig"
    return f"{state.max_days_ahead} {'Tag' if state.max_days_ahead == 1 else 'Tage'}"


def _fenster_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(label, callback_data=f"fenster:{days if days is not None else 'any'}")
        for label, days in WINDOW_OPTIONS
    ]
    return InlineKeyboardMarkup([buttons])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/start – Nutzer registrieren, Benachrichtigungen aktivieren und sofort prüfen."""
    chat_id = update.effective_chat.id
    subscribers[chat_id] = True
    _save(subscribers)
    logger.info("Nutzer %d hat den Bot gestartet.", chat_id)
    await update.message.reply_text(
        f"sv-termin-bot v{VERSION}\n\n"
        "Ich zeige dir gleich den nächsten freien Termin beim Straßenverkehrsamt Bochum.\n\n"
        "Automatische Alerts nur wenn ein Termin in dein Zeitfenster fällt (/fenster).\n\n"
        "Mit /stop kannst du die Benachrichtigungen deaktivieren."
    )

    # Sofortcheck – ignoriert das Zeitfenster, zeigt immer den besten verfügbaren Termin
    try:
        async with state.check_lock:
            available, booking_url, first_date = await asyncio.wait_for(
                check_appointments(TERMIN_URL), timeout=120
            )
            if available:
                current_date = state.parse_date(first_date)
                if current_date:
                    state.last_notified_date = current_date

        if available:
            await update.message.reply_text(
                f"Frühester verfügbarer Termin: {first_date}\n\n"
                f"Jetzt buchen:\n{booking_url}\n\n"
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


async def fenster(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/fenster – Zeitfenster für automatische Alerts einstellen."""
    await update.message.reply_text(
        f"Aktuelles Fenster: {_window_label()}\n\n"
        "Für welchen Zeitraum soll ich dich benachrichtigen?",
        reply_markup=_fenster_keyboard(),
    )


async def fenster_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Verarbeitet Tastendruck beim /fenster-Menü."""
    query = update.callback_query
    await query.answer()

    data = query.data  # e.g. "fenster:3" or "fenster:any"
    value = data.split(":")[1]

    if value == "any":
        state.max_days_ahead = None
        label = "Beliebig – ich benachrichtige dich bei allen Terminen."
    else:
        state.max_days_ahead = int(value)
        label = f"Ich benachrichtige dich nur bei Terminen innerhalb von {_window_label()}."

    state.last_notified_date = None  # Reset so next check re-evaluates
    logger.info("Zeitfenster geändert: %s", _window_label())
    await query.edit_message_text(f"✓ {label}")


def is_within_window(appointment_date: datetime) -> bool:
    """Prüft ob ein Termin innerhalb des eingestellten Zeitfensters liegt."""
    if state.max_days_ahead is None:
        return True
    deadline = datetime.now() + timedelta(days=state.max_days_ahead)
    return appointment_date <= deadline


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
    application.add_handler(CommandHandler("fenster", fenster))
    application.add_handler(CallbackQueryHandler(fenster_callback, pattern=r"^fenster:"))
    return application
