import requests
from bs4 import BeautifulSoup


def check_for_appointments(url: str) -> tuple[bool, str]:
    """
    Prüft die Terminseite auf verfügbare Termine.
    Gibt (True, Nachricht) zurück, wenn Termine gefunden wurden.
    """
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # TODO: Diesen Abschnitt an die konkrete Website anpassen.
        # Beispiel: Nach einem Element suchen, das "kein Termin" anzeigt.
        page_text = soup.get_text().lower()

        no_appointment_keywords = [
            "kein termin",
            "keine termine",
            "leider kein",
            "nicht verfügbar",
            "momentan keine",
        ]

        for keyword in no_appointment_keywords:
            if keyword in page_text:
                return False, f"Kein Termin verfügbar (gefunden: '{keyword}')"

        # Wenn kein "kein Termin"-Hinweis gefunden wurde, könnte ein Termin frei sein
        return True, f"Möglicherweise freie Termine auf {url}!"

    except requests.RequestException as e:
        return False, f"Fehler beim Abrufen der Seite: {e}"
