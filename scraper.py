import logging
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

logger = logging.getLogger(__name__)

# Texte, die auf FREIE Termine hinweisen
FREE_KEYWORDS = [
    "frei",
    "termin verfügbar",
    "verfügbar",
    "buchen",
    "freier termin",
    "wählen sie",
]

# Texte, die auf KEINE freien Termine hinweisen
BUSY_KEYWORDS = [
    "kein termin",
    "keine termine",
    "keine freien termine",
    "leider",
    "ausgebucht",
    "nicht verfügbar",
]


async def check_appointments(url: str) -> bool:
    """
    Öffnet die Terminseite mit Playwright und prüft,
    ob freie Termine vorhanden sind.

    Gibt True zurück, wenn ein freier Termin gefunden wurde,
    sonst False.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()

        try:
            logger.info("Öffne Seite: %s", url)
            await page.goto(url, timeout=30_000)

            # Warte bis das DOM vollständig geladen ist
            await page.wait_for_load_state("domcontentloaded", timeout=15_000)

            # Kurze Pause für dynamisch nachgeladene Inhalte (JS-Rendering)
            await page.wait_for_timeout(3_000)

            page_text = (await page.inner_text("body")).lower()
            logger.debug("Seitentext (ersten 300 Zeichen): %s", page_text[:300])

            # Zuerst auf "kein Termin"-Hinweise prüfen
            for keyword in BUSY_KEYWORDS:
                if keyword in page_text:
                    logger.info("Kein Termin: '%s' gefunden.", keyword)
                    return False

            # Dann auf freie Termine prüfen
            for keyword in FREE_KEYWORDS:
                if keyword in page_text:
                    logger.info("Freier Termin möglich: '%s' gefunden.", keyword)
                    return True

            # Fallback: unklar → als nicht verfügbar werten
            logger.warning("Kein eindeutiges Ergebnis auf der Seite gefunden.")
            return False

        except PlaywrightTimeout:
            logger.error("Timeout beim Laden der Seite: %s", url)
            return False
        except Exception as e:
            logger.error("Unerwarteter Fehler beim Scraping: %s", e)
            return False
        finally:
            await browser.close()
