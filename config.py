import os
from datetime import time

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

SCHEDULE = {
    "morning_workout": {
        "time": time(8, 15),
        "message": "🏃‍♂️ Время утренней тренировки! Готов к активному старту дня?",
        "button_text": "Тренировка выполнена ✅",
    },
    "breakfast": {
        "time": time(9, 0),
        "message": "🍳 Время завтрака! Не забудь правильно питаться.",
        "button_text": "Завтрак готов ✅",
    },
    "lunch": {
        "time": time(13, 0),
        "message": "🥗 Время обеда! Пора подкрепиться.",
        "button_text": "Обед готов ✅",
    },
    "language_study": {
        "time": time(16, 0),
        "message": "📚 Время изучения языка! Не пропускай занятия.",
        "button_text": "Язык изучен ✅",
    },
    "dinner": {
        "time": time(19, 0),
        "message": "🍽️ Время ужина! Завершаем день вкусно.",
        "button_text": "Ужин готов ✅",
    },
    "daily_report": {
        "time": time(21, 0),
        "message": "📊 Время подготовить отчёт о дне! Как дела?",
        "button_text": "Отчёт готов ✅",
    },
}

TIMEZONE = os.getenv("TIMEZONE", "UTC")
DATABASE_PATH = os.getenv("DATABASE_PATH", "bot_data.db")

MESSAGES = {
    "start": (
        "🤖 Привет! Я твой личный помощник по распорядку дня.\n\n"
        "📋 Доступные команды:\n"
        "• /статус - текущий статус задач\n"
        "• /отчет - отправить отчет за день\n"
        "• /расписание - показать расписание\n\n"
        "Я буду напоминать тебе о важных делах и следить за их выполнением! 💪"
    ),
    "task_completed": "✅ Отлично! Задача выполнена.",
    "task_already_completed": "ℹ️ Эта задача уже выполнена сегодня.",
    "unknown_message": "🤔 Не понимаю. Используй команды или отвечай на мои напоминания.",
    "no_tasks_today": "📅 На сегодня задач нет или все выполнены!",
    "status_header": "📊 Статус задач на сегодня:",
    "report_header": "📝 Пожалуйста, напишите ваш отчёт за день:",
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
