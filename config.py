import os
from datetime import time
import asyncio
import logging

from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from telegram.ext._utils.types import CCT

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния для диалога отчета
REPORT_TEXT = 0

# Токен бота (получить от @BotFather)
BOT_TOKEN = os.getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')

# Расписание напоминаний
SCHEDULE = {
    "morning_workout": {"time": time(8, 15), "message": "🏃‍♂️ Время утренней тренировки! Готов к активному старту дня?", "button_text": "Тренировка выполнена ✅"},
    "breakfast": {"time": time(9, 0), "message": "🍳 Время завтрака! Не забудь правильно питаться.", "button_text": "Завтрак готов ✅"},
    "lunch": {"time": time(13, 0), "message": "🥗 Время обеда! Пора подкрепиться.", "button_text": "Обед готов ✅"},
    "language_study": {"time": time(16, 0), "message": "📚 Время изучения языка! Не пропускай занятия.", "button_text": "Язык изучен ✅"},
    "dinner": {"time": time(19, 0), "message": "🍽️ Время ужина! Завершаем день вкусно.", "button_text": "Ужин готов ✅"},
    "daily_report": {"time": time(21, 0), "message": "📊 Время подготовить отчёт о дне! Как дела?", "button_text": "Отчёт готов ✅"},
}

# Часовой пояс (по умолчанию UTC)
TIMEZONE = os.getenv('TIMEZONE', 'UTC')

# Настройки базы данных (просто объявление)
DATABASE_PATH = "bot_data.db"  # Вам потребуется реализовать взаимодействие с БД

# Сообщения бота
MESSAGES = {
    "start": """🤖 Привет! Я твой личный помощник по распорядку дня.

📋 Доступные команды:
• /статус - текущий статус задач
• /отчет - отправить отчет за день
• /расписание - показать расписание

Я буду напоминать тебе о важных делах и следить за их выполнением! 💪
    """,
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
    "cancel_report": "❌ Отчёт отменён."
}

# Настройки для веб-сервера (для деплоя)
PORT = int(os.getenv('PORT', 8000))
WEBHOOK_URL = os.getenv('WEBHOOK_URL', '')
USE_WEBHOOK = os.getenv('USE_WEBHOOK', 'False').lower() == 'true'

# Словарь для хранения статуса выполнения задач для каждого пользователя
user_task_status = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет приветственное сообщение и показывает доступные команды."""
    await update.message.reply_text(MESSAGES["start"])


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает текущий статус задач на сегодня для пользователя."""
    user_id = update.effective_user.id
    today = context.user_data.get('today_date', None) # Потребуется реализовать логику отслеживания даты

    if user_id not in user_task_status or today is None or user_task_status[user_id].get(today) is None:
        await update.message.reply_text(MESSAGES["no_tasks_today"])
        return

    status_message = [MESSAGES["status_header"]]
    for task_name, status in user_task_status[user_id][today].items():
        if task_name in SCHEDULE:
            status_message.append(f"• {SCHEDULE[task_name].get('message', task_name)}: {MESSAGES.get(f'task_{status}', status)}")
    await update.message.reply_text("\n".join(status_message))


async def schedule_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает расписание задач."""
    schedule_message = [MESSAGES["schedule_header"]]
    for task_name, details in SCHEDULE.items():
        schedule_message.append(f"• {task_name}: {details['time'].strftime('%H:%M')}, {details['message']}")
    await update.message.reply_text("\n".join(schedule_message))


async def report_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начинает диалог для получения отчета."""
    await update.message.reply_text(MESSAGES["report_header"], reply_markup=ReplyKeyboardRemove())
    return REPORT_TEXT


async def report_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получает текст отчета."""
    user_report = update.message.text
    context.user_data['daily_report'] = user_report
    await update.message.reply_text(MESSAGES["report_submitted"])
    return ConversationHandler.END


async def report_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отменяет сбор отчета."""
    await update.message.reply_text(MESSAGES["cancel_report"], reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


async def handle_task_completion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает нажатие на кнопку выполнения задачи."""
    query = update.callback_query
    await query.answer()  # Отправляет пустое уведомление, чтобы убрать "часики"
    task_name = query.data
    user_id = query.from_user.id
    today = context.user_data.get('today_date', None) # Потребуется реализовать логику отслеживания даты

    if today is None:
        return

    if user_id not in user_task_status:
        user_task_status[user_id] = {today: {}}
    elif today not in user_task_status[user_id]:
        user_task_status[user_id][today] = {}

    if task_name in user_task_status[user_id][today] and user_task_status[user_id][today][task_name] == "completed":
        await query.message.reply_text(MESSAGES["task_already_completed"])
        return

    user_task_status[user_id][today][task_name] = "completed"
    await query.message.reply_text(MESSAGES["task_completed"])


async def send_scheduled_reminders(app: CCT) -> None:
    """Отправляет запланированные напоминания."""
    while True:
        now = datetime.now(timezone(TIMEZONE))
        today_str = now.strftime("%Y-%m-%d")
        for task_name, details in SCHEDULE.items():
            if now.hour == details['time'].hour and now.minute == details['time'].minute:
                message = details['message']
                button_text = details['button_text']
                keyboard = [[InlineKeyboardButton(button_text, callback_data=task_name)]]
                reply_markup = InlineKeyboardMarkup(keyboard)

                # Здесь должна быть логика рассылки напоминаний всем пользователям.
                # Вам потребуется хранить user_id пользователей, подписанных на напоминания.
                # Пример (нужно заменить на вашу реальную логику):
                # for user_id in get_all_user_ids():
                #     try:
                #         await app.bot.send_message(user_id, message, reply_markup=reply_markup)
                #         # Инициализация статуса задачи на сегодня для пользователя, если еще не сделано
                #         if user_id not in user_task_status or today_str not in user_task_status[user_id]:
                #             user_task_status[user_id] = user_task_status.get(user_id, {})
                #             user_task_status[user_id][today_str] = user_task_status[user_id].get(today_str, {})
                #             user_task_status[user_id][today_str][task_name] = "pending"
                #     except Exception as e:
                #         logger.error(f"Не удалось отправить напоминание пользователю {user_id}: {e}")
        await asyncio.sleep(60)  # Проверять каждую минуту


async def post_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает отчет за день."""
    user_id = update.effective_user.id
    report = context.user_data.get('daily_report', 'Отчёт не был составлен.')
    await update.message.reply_text(f"{MESSAGES['report_header']}\n{report}")


async def main() -> None:
    """Запускает бота."""
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("статус", status)) # Исправлено название команды
    application.add_handler(CommandHandler("расписание", schedule_command))
    application.add_handler(CommandHandler("отчет", report_start))

    # Обработчик диалога отчета
    report_handler = ConversationHandler(
        entry_points=[CommandHandler('отчет', report_start)],
        states={
            REPORT_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, report_text)],
        },
        fallbacks=[CommandHandler('cancel', report_cancel)],
    )
    application.add_handler(report_handler)

    # Обработчик нажатий кнопок
    application.add_handler(CallbackQueryHandler(handle_task_completion))

    # Обработчик для показа отчета (вызывается после завершения диалога)
    application.add_handler(CommandHandler("показать_отчет", post_report)) # Добавлена команда для просмотра отчета

    # Обработчик неизвестных команд
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_message))

    # Запуск фоновой задачи для отправки напоминаний
    asyncio.create_task(send_scheduled_reminders(application))

    # Запуск бота
    if USE_WEBHOOK and WEBHOOK_URL:
        await application.bot.set_webhook(WEBHOOK_URL)
        await application.run_webhook(listen="0.0.0.0", port=PORT, webhook_url=WEBHOOK_URL)
    else:
        await application.run_polling()


async def unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает неизвестные сообщения."""
    await update.message.reply_text(MESSAGES["unknown_message"])


if __name__ == "__main__":
    asyncio.run(main())