import asyncio
import logging
from telegram.ext import ApplicationBuilder

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# Предполагается, что эти файлы существуют и настроены корректно
from handlers import (
    start_handler,
    status_handler,
    report_handler,
    schedule_handler,
    message_handler,
    button_handler,
)
from scheduler import start_scheduler, shutdown_scheduler
from config import BOT_TOKEN, PORT, USE_WEBHOOK, WEBHOOK_URL
from database import (
    init_db
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
# Уменьшаем "шум" от httpx и httpcore, которые использует библиотека
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


async def post_init(application: Application):
    """
    Функция, которая будет выполнена после инициализации приложения.
    Идеальное место для запуска фоновых задач, таких как планировщик.
    """
    await start_scheduler(application)
    # Здесь можно инициализировать соединение с БД, если это необходимо
    init_db()


async def post_shutdown(application: Application):
    """
    Функция, которая будет выполнена перед завершением работы приложения.
    Используется для корректного освобождения ресурсов.
    """
    await shutdown_scheduler()
    logger.info("Планировщик остановлен.")


async def main() -> None:
    """Основная функция для запуска бота."""
    logger.info("Запуск бота...")
    
    # Создание приложения с указанием хуков жизненного цикла
    application = ApplicationBuilder().token(BOT_TOKEN).build()


    # Регистрация обработчиков команд
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("status", status_handler))
    application.add_handler(CommandHandler("report", report_handler))
    application.add_handler(CommandHandler("schedule", schedule_handler))
    
    # Обработчик кнопок
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    # Запуск бота в зависимости от настроек
    if USE_WEBHOOK and WEBHOOK_URL and PORT:
        logger.info(f"Запуск с webhook на порту {PORT}")
        await application.bot.set_webhook(WEBHOOK_URL)
        await application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=BOT_TOKEN,  # Telegram будет слать POST на /{BOT_TOKEN}
            webhook_url=WEBHOOK_URL,
        )
    else:
        logger.info("Запуск с polling")
        # allowed_updates говорит Telegram API, какие типы обновлений нам нужны
        application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    asyncio.run(main())