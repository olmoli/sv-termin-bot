import logging
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

logger = logging.getLogger(__name__)


async def check_appointments(url: str) -> tuple[bool, str]:
    """
    Navigiert durch den Buchungsflow und prüft ob freie Termine vorhanden sind.

    Gibt (True, booking_url) zurück wenn Termine verfügbar,
    sonst (False, "").

    booking_url ist die frische Session-URL – direkt klickbar für 60 Minuten.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            timezone_id="Europe/Berlin",
            locale="de-DE",
        )

        try:
            # Schritt 1: Session-Expired-Seite laden
            logger.info("Starte neue Session: %s", url)
            await page.goto(url, timeout=30_000)
            await page.wait_for_load_state("domcontentloaded", timeout=15_000)

            # Schritt 2: Neuen Termin buchen → frische Session mit neuer wsid
            await page.locator("text=Neuen Termin buchen").click()
            await page.wait_for_load_state("domcontentloaded", timeout=15_000)
            await page.wait_for_timeout(1_500)

            # Schritt 3: Erste Dienstleistung auf 1 setzen
            selects = await page.query_selector_all("select")
            if not selects:
                logger.error("Keine Auswahl-Dropdowns gefunden.")
                return False, "", ""
            await selects[0].select_option("1")
            await page.wait_for_timeout(500)

            # Schritt 4: Weiter klicken → Kalenderseite
            await page.locator("button", has_text="Weiter").click()
            await page.wait_for_load_state("domcontentloaded", timeout=15_000)
            await page.wait_for_timeout(3_000)

            page_text = (await page.inner_text("body")).lower()
            logger.debug("Kalenderseite (ersten 300 Zeichen): %s", page_text[:300])

            if "tage mit verfügbaren terminen" in page_text:
                # Ersten verfügbaren Tag auslesen und anklicken
                first_date_btn = page.locator("button.card.big").first
                first_date_text = (await first_date_btn.inner_text()).strip().replace("\n", " ")
                await first_date_btn.click()
                await page.wait_for_timeout(800)

                # Erste verfügbare Uhrzeit auslesen
                first_time_btn = page.locator("button.card:not(.big)").first
                first_time_text = (await first_time_btn.inner_text()).strip()

                first_slot = f"{first_date_text} {first_time_text}"
                logger.info("Frühester Termin: %s", first_slot)
                return True, page.url, first_slot

            logger.info("Keine freien Termine gefunden.")
            return False, "", ""

        except PlaywrightTimeout:
            logger.error("Timeout beim Laden der Seite.")
            return False, "", ""
        except Exception as e:
            logger.error("Unerwarteter Fehler beim Scraping: %s", e)
            return False, "", ""
        finally:
            await browser.close()
