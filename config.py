import os
from dotenv import load_dotenv

VERSION = "0.28"

load_dotenv()

TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_TOKEN", "")
CHECK_INTERVAL: int = int(os.getenv("CHECK_INTERVAL", "300"))

TERMIN_URL = (
    "https://termine.bochum.de/m/kfz-angelegenheiten/extern/calendar/"
    "session_expired"
    "?uid=bffa082e-0640-40b4-ad60-4a98355850ff"
    "&lang=de"
)

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN fehlt in der .env-Datei!")
