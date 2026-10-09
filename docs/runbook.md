# Ratio & Schedule Bot — Runbook

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BOT_TOKEN` | Yes | — | Telegram bot token (from @BotFather) |
| `TIMEZONE` | No | `Europe/Moscow` | Default fallback timezone |
| `PORT` | No | `8000` | Webhook / HTTP server port |
| `USE_WEBHOOK` | No | `false` | Enable webhook mode (Render) |
| `WEBHOOK_URL` | No | — | Public webhook URL |
| `PRO_PRICE_STARS` | No | `150` | Price in Telegram Stars for 30-day Pro (~$2.99) |
| `WEBAPP_URL` | No | — | Public URL to Mini App (e.g. `https://<host>/webapp`) |

## Endpoints

- `GET /health` — Health check endpoint (for Render / Railway)
- `GET /webapp` — Telegram Mini App (интерактивный таймлайн и редактор дня)

## Features & Commands

- `/start` — Запуск и главное меню
- `/status` — Статус задач на сегодня, выполнение и стрик
- `/ratio` (или `/balance`) — Недельная аналитика соотношения работы и отдыха, Work/Rest Ratio, Life Balance Score
- `/report` — Отчет по дням за неделю
- `/schedule` — Персональное расписание дня
- `/briefing` — Утренний брифинг с задачами и цитатой
- `/tasks` — Управление персональными привычками
- `/addtask <Имя> <HH:MM> [категория] [мин]` — Быстрое добавление задачи
- `/deltask <ключ>` — Удаление задачи
- `/timezone` — Выбор персонального часового пояса
- `/pro` — Подписка за Telegram Stars
- `/share` — Карточка продуктивности для сторис и каналов

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
2. Set `BOT_TOKEN`, `TIMEZONE`, and optionally `WEBAPP_URL` env vars
3. Set `Start Command`: `python main.py`
4. Attach a **Persistent Disk** mounted to `/data` and set `DATABASE_PATH=/data/bot_data.db` to prevent database wipes across deploys.

## Внешние настройки (Не зависящие от кода / BotFather)

Для полноценной работы бота в Telegram необходимо один раз настроить параметры в [@BotFather](https://t.me/BotFather):

### 1. Меню команд (`/setcommands`)
Отправьте боту `@BotFather` команду `/setcommands`, выберите вашего бота и отправьте следующий список:
```text
start - Запустить бота и главное меню
status - Статус задач на сегодня и стрик
ratio - Анализ баланса работы и отдыха
schedule - Расписание задач
report - Отчет по дням за неделю
briefing - Утренний брифинг
tasks - Управление привычками
timezone - Выбор часового пояса
pro - Подписка за Telegram Stars
share - Поделиться карточкой продуктивности
```

### 2. Кнопка запуска Mini App в меню (`/setmenubutton`)
1. В `@BotFather` вызовите команду `/setmenubutton`.
2. Выберите бота.
3. Отправьте URL вашего веб-приложения: `https://<ваш-домен-на-render>/webapp`
4. Укажите заголовок кнопки: `Таймлайн 📱`

### 3. Telegram Stars для цифровых товаров
Платежи в Telegram Stars (`currency="XTR"`) включены по умолчанию в API Telegram и не требуют подключения сторонних платежных систем.
Вывод заработанных Stars осуществляется владельцем бота через платформу **Fragment** (TON).

