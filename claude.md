# sv-termin-bot — Project Knowledge Base

**Version: v0.22**

---

## 1. Project Overview

A Telegram bot that monitors the Straßenverkehrsamt Bochum (Bochum vehicle registration office) appointment booking system and notifies subscribers the moment a new appointment slot becomes available.

**Problem solved:** Appointment slots are scarce and disappear fast. This bot polls the booking website every 5 minutes and sends immediate Telegram alerts when new (earlier) slots appear.

**Target URL:** Bochum traffic office appointment system (defined in `config.py` as `TERMIN_URL`)

---

## 2. Current Status

- **Version:** v0.22
- **State:** MVP complete and functional
- **Active subscribers:** 1 (chat_id: 836882040)
- **Check interval:** 300 seconds (5 minutes, configurable via `.env`)
- **Monitoring logic:** Only notifies if a NEW (earlier) appointment date is found; no duplicate alerts

---

## 3. Architecture

### Module Overview

```
main.py           Entry point; starts Telegram bot + monitor loop
config.py         Loads .env, defines constants (VERSION, TOKEN, URL, interval)
scraper.py        Playwright browser automation to extract appointment data
telegram_bot.py   Bot command handlers (/start, /stop) + alert distribution
state.py          Shared async state: last_notified_date, check_lock
subscribers.json  Persisted user subscriptions {chat_id: bool}
```

### End-to-End Flow

1. `main()` starts the Telegram Application and launches `monitor_loop()` as a background task.
2. `monitor_loop()` runs indefinitely: acquire lock → scrape → compare date → maybe alert → sleep → repeat.
3. `scraper.check_appointments()` launches headless Chromium, navigates the booking UI, and returns `(available: bool, booking_url: str, first_slot: str)`.
4. Deduplication: only notifies if `first_slot` date is earlier than `state.last_notified_date` (or if nothing has been notified yet).
5. `send_alert()` sends a Telegram message to all subscribers with `status=True`.

### Scraper Navigation Flow

```
session-expired page
  → click "Neuen Termin buchen"
  → select first service in dropdown
  → click "Weiter"
  → check for "tage mit verfügbaren terminen" in page text
  → extract earliest date (button.card.big) + time (button.card:not(.big))
```

### Concurrency

`asyncio.Lock` (`state.check_lock`) prevents the `/start` handler and `monitor_loop` from running the scraper simultaneously.

---

## 4. Setup & Deployment

### Local Development

- Python 3.11+
- `pip install -r requirements.txt`
- `playwright install chromium`
- Copy `.env.example` → `.env` and fill in:
  ```
  TELEGRAM_TOKEN=<bot token from @BotFather>
  CHECK_INTERVAL=300   # optional, default 300s
  ```
- `python main.py`

### Railway.com Hosting

**Hosting platform:** [railway.com](https://railway.com)

Railway uses [Nixpacks](https://nixpacks.com) for builds. Playwright requires an explicit browser install step that Railway does NOT run by default.

**Fix:** [nixpacks.toml](nixpacks.toml) at the project root instructs Railway to run `playwright install --with-deps chromium` during the build phase. The `--with-deps` flag installs all required OS-level Chromium dependencies (libnss, libatk, etc.).

```toml
[phases.install]
cmds = [
  "pip install -r requirements.txt",
  "playwright install --with-deps chromium"
]

[start]
cmd = "python main.py"
```

**Environment variables to set in Railway dashboard:**
- `TELEGRAM_TOKEN` — required
- `CHECK_INTERVAL` — optional (default 300s)

**Known issue (resolved):**
> `BrowserType.launch: Executable doesn't exist at /root/.cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell`
> **Cause:** Playwright browsers were not installed during build.
> **Fix:** `nixpacks.toml` with `playwright install --with-deps chromium`.

### Logs

Dual output: console + `sv_termin_bot.log` (UTF-8, includes timestamps).

---

## 5. Key Files

| File | Role |
|------|------|
| [main.py](main.py) | Entry point; `monitor_loop()` + `main()` |
| [config.py](config.py) | `VERSION`, `TELEGRAM_TOKEN`, `CHECK_INTERVAL`, `TERMIN_URL` |
| [scraper.py](scraper.py) | `check_appointments(url)` → Playwright automation |
| [telegram_bot.py](telegram_bot.py) | `/start`, `/stop`, `send_alert()`, subscriber persistence |
| [state.py](state.py) | `last_notified_date`, `check_lock`, `parse_date()` |
| [requirements.txt](requirements.txt) | `python-telegram-bot==21.6`, `playwright>=1.50.0`, `python-dotenv==1.0.1` |
| [.env.example](.env.example) | Template for environment variables |
| [subscribers.json](subscribers.json) | Persisted `{chat_id: bool}` subscriptions |
| [nixpacks.toml](nixpacks.toml) | Railway build config: installs Playwright + Chromium |

---

## 6. Decisions & Assumptions

- **Playwright over requests/BeautifulSoup:** The booking site is session-based and requires real browser navigation; a plain HTTP scraper would not work.
- **File-based persistence (JSON):** No database needed for MVP scale (few subscribers). Simple and portable.
- **Deduplication by earliest date:** Prevents alert spam when the same slot stays open across multiple check cycles. Resets when no appointments exist, ready for the next alert.
- **asyncio.Lock for scraper:** Ensures only one Playwright session runs at a time, avoiding resource conflicts and race conditions.
- **German date parsing:** `state.parse_date()` handles the format `"Montag 13.04.2026 10:45"` as returned by the booking UI.

---

## 7. TODO / Next Steps

- [ ] Add `/status` command: let users query current availability on demand
- [ ] Support multiple office locations or service types (make service selection configurable)
- [ ] Dockerize for easy deployment on a server/VPS
- [ ] Add retry logic in scraper for transient network errors
- [ ] Persist `last_notified_date` to disk (currently lost on restart)
- [ ] Admin command to list/count active subscribers
- [ ] Unit tests for `state.parse_date()` and scraper response parsing

---

## 8. Claude Working Rules

These rules apply to all future changes in this project:

### R1 — Documentation Requirement
After every relevant code change, update `claude.md` to reflect the new state. This file is the single source of truth.

### R2 — Version Management (CRITICAL)
- Current version lives in **two places** and must stay in sync:
  - `claude.md` (top of file, `**Version: vX.XX**`)
  - `config.py` (`VERSION = "X.XX"`)
- After every commit or meaningful update: increment by +0.01
  - Example: v0.22 → v0.23 → v0.24

### R3 — Consistency
All code changes must be reflected in the documentation. No outdated or conflicting information.

### R4 — Clarity over verbosity
Keep documentation concise and structured. Avoid padding.

### R5 — Current Status always accurate
The "Current Status" section and TODO list must always reflect the real state of the project.