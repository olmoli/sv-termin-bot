import asyncio
from datetime import datetime

# Frühester Termin der zuletzt gemeldet wurde.
# Wird von /start und monitor_loop gemeinsam genutzt
# um Doppel-Benachrichtigungen zu verhindern.
last_notified_date: datetime | None = None

# Verhindert gleichzeitige Checks durch /start und monitor_loop
check_lock = asyncio.Lock()


def parse_date(first_slot: str) -> datetime | None:
    """Extrahiert Datum+Zeit aus z.B. 'Montag 13.04.2026 10:45'."""
    parts = first_slot.split()
    date_str = next((p for p in parts if "." in p), None)
    time_str = next((p for p in parts if ":" in p), None)
    if date_str and time_str:
        try:
            return datetime.strptime(f"{date_str} {time_str}", "%d.%m.%Y %H:%M")
        except ValueError:
            pass
    if date_str:
        try:
            return datetime.strptime(date_str, "%d.%m.%Y")
        except ValueError:
            pass
    return None
