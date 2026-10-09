import os
from datetime import time

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

CATEGORIES = {
    "work": {"name": "Работа", "emoji": "💼"},
    "rest": {"name": "Отдых", "emoji": "🎮"},
    "health": {"name": "Здоровье и спорт", "emoji": "🏃"},
    "study": {"name": "Обучение", "emoji": "📚"},
    "routine": {"name": "Рутина и быт", "emoji": "🍳"},
}

SCHEDULE = {
    "morning_workout": {
        "time": time(8, 15),
        "message": "🏃‍♂️ Время утренней тренировки! Готов к активному старту дня?",
        "button_text": "Тренировка выполнена ✅",
        "category": "health",
        "duration_minutes": 45,
    },
    "breakfast": {
        "time": time(9, 0),
        "message": "🍳 Время завтрака! Не забудь правильно питаться.",
        "button_text": "Завтрак готов ✅",
        "category": "routine",
        "duration_minutes": 30,
    },
    "lunch": {
        "time": time(13, 0),
        "message": "🥗 Время обеда! Пора подкрепиться.",
        "button_text": "Обед готов ✅",
        "category": "routine",
        "duration_minutes": 45,
    },
    "language_study": {
        "time": time(16, 0),
        "message": "📚 Время изучения языка! Не пропускай занятия.",
        "button_text": "Язык изучен ✅",
        "category": "study",
        "duration_minutes": 60,
    },
    "dinner": {
        "time": time(19, 0),
        "message": "🍽️ Время ужина! Завершаем день вкусно.",
        "button_text": "Ужин готов ✅",
        "category": "routine",
        "duration_minutes": 45,
    },
    "daily_report": {
        "time": time(21, 0),
        "message": "📊 Время подготовить отчёт о дне! Как дела?",
        "button_text": "Отчёт готов ✅",
        "category": "work",
        "duration_minutes": 30,
    },
}

TIMEZONE = os.getenv("TIMEZONE", "UTC")
DATABASE_PATH = os.getenv("DATABASE_PATH", "bot_data.db")
PRO_PRICE_STARS = int(os.getenv("PRO_PRICE_STARS", "150"))
WEBAPP_URL = os.getenv("WEBAPP_URL", "")

COMMON_TIMEZONES = [
    ("Europe/Moscow", "🇷🇺 Москва (UTC+3)"),
    ("Asia/Yekaterinburg", "🇷🇺 Екатеринбург (UTC+5)"),
    ("Asia/Almaty", "🇰🇿 Алматы (UTC+5)"),
    ("Asia/Tashkent", "🇺🇿 Ташкент (UTC+5)"),
    ("Asia/Tbilisi", "🇬🇪 Тбилиси (UTC+4)"),
    ("Asia/Yerevan", "🇦🇲 Ереван (UTC+4)"),
    ("Asia/Dubai", "🇦🇪 Дубай (UTC+4)"),
    ("Europe/Kyiv", "🇺🇦 Киев (UTC+2/3)"),
    ("Europe/Berlin", "🇩🇪 Берлин (UTC+1/2)"),
    ("Europe/London", "🇬🇧 Лондон (UTC+0/1)"),
    ("UTC", "🌐 UTC (+0)"),
]

MESSAGES = {
    "start": (
        "🤖 Привет! Я твой личный помощник по распорядку дня и балансу времени.\n\n"
        "📋 Доступные команды:\n"
        "• /status (или Статус) — текущий статус задач на сегодня\n"
        "• /ratio (или Баланс) — инфографика соотношения работы и отдыха\n"
        "• /report (или Отчёт) — отчет по дням за неделю\n"
        "• /schedule (или Расписание) — ваше персональное расписание\n"
        "• /briefing — утренний брифинг на сегодня\n"
        "• /tasks — управление вашими привычками и задачами\n"
        "• /timezone — выбор вашего часового пояса\n"
        "• /pro — подписка за Telegram Stars\n"
        "• /share — поделиться карточкой продуктивности\n\n"
        "Я помогу держать баланс между делами и отдыхом! 💪"
    ),
    "task_completed": "✅ Отлично! Задача выполнена.",
    "task_already_completed": "ℹ️ Эта задача уже выполнена сегодня.",
    "task_snoozed": "⏱ Задача отложена на 15 минут.",
    "task_skipped": "⏭ Задача пропущена на сегодня.",
    "unknown_message": "🤔 Не понимаю. Используй команды или кнопки меню.",
    "no_tasks_today": "📅 На сегодня задач нет или все выполнены!",
    "status_header": "📊 Статус задач на сегодня:",
    "report_header": "📝 Ваш отчёт за 7 дней:",
    "schedule_header": "🕐 Расписание задач:",
    "task_pending": "⏳ Ожидает выполнения",
    "task_completed_status": "✅ Выполнено",
    "task_missed": "❌ Пропущено",
    "report_submitted": "✅ Спасибо! Ваш отчёт сохранён.",
    "cancel_report": "❌ Отчёт отменён.",
    "motivational": [
        "Отличная работа! Продолжай в том же духе! 💪",
        "Ты сегодня просто огонь! 🔥",
        "Каждый день ты становишься лучше! 🌟",
        "Молодец! Так держать! 👏",
        "Ты справляешься отлично! 🎯",
    ],
}

WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", 8000))
USE_WEBHOOK = os.getenv("USE_WEBHOOK", "false").lower() == "true"
