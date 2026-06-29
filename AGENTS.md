# Ratio & Schedule Bot

Russian-language Telegram bot for maintaining daily routines. Sends scheduled reminders, tracks completion, weekly reports with motivational messages.

## Tech Stack
- **Language:** Python 3.11
- **Framework:** python-telegram-bot v20.8
- **Scheduler:** APScheduler 3.10
- **Database:** SQLite
- **Deploy:** Render (free tier)

## Commands
- `python main.py` — run the bot
- `pip install -r requirements.txt` — install deps
- `source venv/bin/activate` — activate virtual env

## Structure
- `main.py` — entry point
- `handlers.py` — command/button handlers
- `database.py` — SQLite CRUD (decorator-based connection mgmt)
- `scheduler.py` — APScheduler jobs
- `config.py` — constants, messages, schedule (Russian)

## Conventions
- All user-facing strings in Russian
- Config-driven SCHEDULE dict
- `db_connection` decorator for SQLite lifecycle
- Supports webhook (Render) and polling (local) modes
- Procfile + render.yaml for Render deployment
