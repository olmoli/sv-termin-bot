import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logger = logging.getLogger(__name__)

# Globales Dictionary: chat_id (int) → aktiv (bool)
# Wird zur Laufzeit befüllt – kein persistenter Speicher nötig (MVP)
subscribers: dict[int, bool] = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/start – Nutzer registrieren und Benachrichtigungen aktivieren."""
    chat_id = update.effective_chat.id
    subscribers[chat_id] = True
    logger.info("Nutzer %d hat den Bot gestartet.", chat_id)
    await update.message.reply_text(
        "Du wirst benachrichtigt, sobald ein freier Termin beim "
        "Straßenverkehrsamt Bochum verfügbar ist.\n\n"
        "Mit /stop kannst du die Benachrichtigungen deaktivieren."
    )


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/stop – Benachrichtigungen für diesen Nutzer deaktivieren."""
    chat_id = update.effective_chat.id
    subscribers[chat_id] = False
    logger.info("Nutzer %d hat den Bot gestoppt.", chat_id)
    await update.message.reply_text(
        "Benachrichtigungen deaktiviert. Mit /start wieder aktivieren."
    )


async def send_alert(application: Application, url: str) -> None:
    """Sendet eine Termin-Benachrichtigung an alle aktiven Nutzer."""
    message = f"Termin verfügbar! Jetzt schnell buchen:\n{url}"
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
