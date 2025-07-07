import os
from datetime import time

# Токен бота (получить от @BotFather)
BOT_TOKEN = os.getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')

# Расписание напоминаний
SCHEDULE = {
    "morning_workout": {
        "time": time(8, 15),
        "message": "🏃‍♂️ Время утренней тренировки! Готов к активному старту дня?",
        "button_text": "Тренировка выполнена ✅"
    },
    "breakfast": {
        "time": time(9, 0),
        "message": "🍳 Время завтрака! Не забудь правильно питаться.",
        "button_text": "Завтрак готов ✅"
    },
    "lunch": {
        "time": time(13, 0),
        "message": "🥗 Время обеда! Пора подкрепиться.",
        "button_text": "Обед готов ✅"
    },
    "language_study": {
        "time": time(16, 0),
        "message": "📚 Время изучения языка! Не пропускай занятия.",
        "button_text": "Язык изучен ✅"
    },
    "dinner": {
        "time": time(19, 0),
        "message": "🍽️ Время ужина! Завершаем день вкусно.",
        "button_text": "Ужин готов ✅"
    },
    "daily_report": {
        "time": time(21, 0),
        "message": "📊 Время подготовить отчёт о дне! Как дела?",
        "button_text": "Отчёт готов ✅"
    }
}

# Часовой пояс (по умолчанию UTC)
TIMEZONE = os.getenv('TIMEZONE', 'UTC')

# Настройки базы данных
DATABASE_PATH = "bot_data.db"

# Сообщения бота
MESSAGES = {
    "start": """
🤖 Привет! Я твой личный помощник по распорядку дня.

📋 Доступные команды:
• /статус - текущий статус задач
• /отчёт - отчёт за день
• /расписание - показать расписание

Я буду напоминать тебе о важных делах и следить за их выполнением! 💪
    """,
    
    "task_completed": "✅ Отлично! Задача выполнена.",
    "task_already_completed": "ℹ️ Эта задача уже выполнена сегодня.",
    "unknown_message": "🤔 Не понимаю. Используй команды или отвечай на мои напоминания.",
    
    "no_tasks_today": "📅 На сегодня задач нет или все выполнены!",
    "status_header": "📊 Статус задач на сегодня:",
    "report_header": "📋 Отчёт за день:",
    "schedule_header": "🕐 Расписание задач:",
    
    "task_pending": "⏳ Ожидает выполнения",
    "task_completed_status": "✅ Выполнено",
    "task_missed": "❌ Пропущено"
}

# Настройки для веб-сервера (для деплоя)
PORT = int(os.getenv('PORT', 8000))
WEBHOOK_URL = os.getenv('WEBHOOK_URL', '')
USE_WEBHOOK = os.getenv('USE_WEBHOOK', 'False').lower() == 'true'