# sv-termin-bot — Project Knowledge Base

**Version: v0.25**

---

## 1. Project Overview

A Telegram bot that monitors the Straßenverkehrsamt Bochum (Bochum vehicle registration office) appointment booking system and notifies subscribers the moment a new appointment slot becomes available.

**Problem solved:** Appointment slots are scarce and disappear fast. This bot polls the booking website every 5 minutes and sends immediate Telegram alerts when new (earlier) slots appear.

**Target URL:** Bochum traffic office appointment system (defined in `config.py` as `TERMIN_URL`)

---

## 2. Current Status

- **Version:** v0.25
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

Railway uses [Nixpacks](https://nixpacks.com) for builds. Playwright requires special handling because Railway's Nixpacks uses a **multi-stage build**: system packages installed via `apt-get` during the build stage do NOT carry over to the runtime image. Only app files under `/app` persist.

**Two-part fix in [nixpacks.toml](nixpacks.toml):**

1. `[phases.setup]` — declares Chromium's OS-level shared libraries as `aptPkgs`. Nixpacks bakes these into the **runtime** image, so they're available when the app runs.
2. `[phases.install]` — installs pip packages and downloads the Chromium browser binary to `/app/ms-playwright` (controlled via `PLAYWRIGHT_BROWSERS_PATH` env var).

```toml
[phases.setup]
aptPkgs = [
  "libglib2.0-0", "libnss3", "libnspr4", "libatk1.0-0",
  "libatk-bridge2.0-0", "libcups2", "libdrm2", "libdbus-1-3",
  "libxcb1", "libxkbcommon0", "libx11-6", "libxcomposite1",
  "libxdamage1", "libxext6", "libxfixes3", "libxrandr2",
  "libgbm1", "libpango-1.0-0", "libcairo2", "libasound2",
  "libxss1", "libgtk-3-0"
]

[phases.install]
cmds = [
  "pip install -r requirements.txt",
  "python -m playwright install chromium"
]

[start]
cmd = "python main.py"
```

**Environment variables to set in Railway dashboard:**
- `TELEGRAM_TOKEN` — required
- `PLAYWRIGHT_BROWSERS_PATH` — set to `/app/ms-playwright` (puts browser binary inside the app layer so it survives the multi-stage build)
- `CHECK_INTERVAL` — optional (default 300s)

**Custom Build Command in Railway UI:**
```
pip install -r requirements.txt && python -m playwright install chromium
```
This overrides `[phases.install]` in nixpacks.toml but `[phases.setup]` (aptPkgs) is still respected.

**Known issues (all resolved):**

| Error | Cause | Fix |
|-------|-------|-----|
| `Executable doesn't exist at /root/.cache/ms-playwright/...` | Browser not installed during build | `nixpacks.toml` + custom build command |
| Browser found but `libglib-2.0.so.0: cannot open shared object file` | OS libs installed at build time but not copied to runtime image | Declare libs in `[phases.setup] aptPkgs` |
| Browser installed to `/root/.cache` but not found at runtime | Nixpacks multi-stage build discards `/root/.cache` | Set `PLAYWRIGHT_BROWSERS_PATH=/app/ms-playwright` |

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
| [nixpacks.toml](nixpacks.toml) | Railway build config: aptPkgs for Chromium deps + browser install |

---

## 6. Decisions & Assumptions

- **Playwright over requests/BeautifulSoup:** The booking site is session-based and requires real browser navigation; a plain HTTP scraper would not work.
- **File-based persistence (JSON):** No database needed for MVP scale (few subscribers). Simple and portable.
- **Deduplication by earliest date:** Prevents alert spam when the same slot stays open across multiple check cycles. Resets when no appointments exist, ready for the next alert.
- **asyncio.Lock for scraper:** Ensures only one Playwright session runs at a time, avoiding resource conflicts and race conditions.
- **German date parsing:** `state.parse_date()` handles the format `"Montag 13.04.2026 10:45"` as returned by the booking UI.
- **PLAYWRIGHT_BROWSERS_PATH=/app/ms-playwright:** Redirects Chromium install to the app directory, which survives Railway's multi-stage Nixpacks build. Without this, the browser lands in `/root/.cache` which is discarded at runtime.

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
After every relevant code change, update `CLAUDE.md` to reflect the new state. This file is the single source of truth.

### R2 — Version Management (CRITICAL)
- Current version lives in **two places** and must stay in sync:
  - `CLAUDE.md` (top of file, `**Version: vX.XX**` AND in section 2 `**Version:** vX.XX`)
  - `config.py` (`VERSION = "X.XX"`)
- After every commit or meaningful update: increment by +0.01
  - Example: v0.24 → v0.25 → v0.26
- **Never skip the version bump.** If you made a change, bump the version.

### R3 — Consistency
All code changes must be reflected in the documentation. No outdated or conflicting information.

### R4 — Clarity over verbosity
Keep documentation concise and structured. Avoid padding.

### R5 — Current Status always accurate
The "Current Status" section and TODO list must always reflect the real state of the project.
