# Contributing

## Setup

```bash
git clone <repo>
cd RatioAndScheduleBot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pre-commit install
```

## Commands

- `ruff check .` — lint
- `ruff format .` — format
- `python -m pytest` — run tests
- `python main.py` — run bot

## Conventions

- Python 3.11+
- ruff for linting/formatting
- All user-facing strings in Russian
- Tests use temporary SQLite databases
