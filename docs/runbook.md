# Ratio & Schedule Bot — Runbook

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BOT_TOKEN` | Yes | — | Telegram bot token (from @BotFather) |
| `TIMEZONE` | No | `UTC` | Timezone (e.g. `Europe/Moscow`) |
| `PORT` | No | `8000` | Webhook server port |
| `USE_WEBHOOK` | No | `false` | Enable webhook mode (Render) |
| `WEBHOOK_URL` | No | — | Public webhook URL |

## Deployment

### Local (venv)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # edit BOT_TOKEN
python main.py
```

### Docker

```bash
docker-compose up -d
```

### Render

1. Connect GitHub repo to Render
2. Set `BOT_TOKEN` and `TIMEZONE` env vars
3. Set `Start Command`: `python main.py`

## Monitoring

- Logs: `bot.log` (local) or Render dashboard
- Health: `GET /health` on port 8080

## Troubleshooting

- **Bot not responding**: Verify `BOT_TOKEN` in .env
- **Reminders not sending**: Check `TIMEZONE` setting
- **DB errors**: Delete `bot_data.db` to reset
