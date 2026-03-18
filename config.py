import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_TOKEN", "")
CHECK_INTERVAL: int = int(os.getenv("CHECK_INTERVAL", "300"))

TERMIN_URL = (
    "https://termine.bochum.de/m/kfz-angelegenheiten/extern/calendar/"
    "?uid=bffa082e-0640-40b4-ad60-4a98355850ff"
    "&wsid=647c0088-fbf4-4556-80b4-986beb841905"
    "&lang=de"
)

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN fehlt in der .env-Datei!")
