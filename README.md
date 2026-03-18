# sv-termin-bot

Telegram Bot, der freie Termine beim **Straßenverkehrsamt Bochum** überwacht und sofort benachrichtigt.

## Voraussetzungen

- Python 3.11+
- Ein Telegram Bot Token (von [@BotFather](https://t.me/BotFather))

## Setup

### 1. Abhängigkeiten installieren

```bash
pip install -r requirements.txt
```

### 2. Playwright Chromium installieren

```bash
playwright install chromium
```

### 3. Konfiguration

Kopiere `.env.example` zu `.env` und trage deinen Token ein:

```bash
cp .env.example .env
```

Inhalt der `.env`:

```
TELEGRAM_TOKEN=dein_token_hier
CHECK_INTERVAL=300
```

### 4. Bot starten

```bash
python main.py
```

## Nutzung

Im Telegram-Chat mit deinem Bot:

| Befehl | Aktion |
|--------|--------|
| `/start` | Benachrichtigungen aktivieren |
| `/stop` | Benachrichtigungen deaktivieren |

## Funktionsweise

- Der Bot prüft alle 5 Minuten (konfigurierbar) die Terminseite
- Sobald ein freier Termin erkannt wird, erhalten alle aktiven Nutzer eine Nachricht
- Doppelte Benachrichtigungen werden verhindert (nur bei Statuswechsel)
- Nutzer werden im Arbeitsspeicher gespeichert (MVP – kein DB nötig)

## Projektstruktur

```
sv-termin-bot/
├── main.py           # Einstiegspunkt, startet Bot + Monitor-Loop
├── scraper.py        # Playwright-Scraper für die Terminseite
├── telegram_bot.py   # Bot-Handler (/start, /stop) + Alert-Funktion
├── config.py         # Konfiguration aus .env
├── requirements.txt
├── .env.example
└── README.md
```

## Hinweis

Falls die Seite kein eindeutiges Ergebnis liefert, sollte `scraper.py` angepasst werden –
z.B. nach einem konkreten CSS-Selektor oder Button-Text der Website suchen.
