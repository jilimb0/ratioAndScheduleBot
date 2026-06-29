import asyncio
import logging
from logging.handlers import RotatingFileHandler

from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from config import BOT_TOKEN, PORT, USE_WEBHOOK, WEBHOOK_URL
from database import init_db
from handlers import (
    button_handler,
    message_handler,
    report_handler,
    schedule_handler,
    start_handler,
    status_handler,
)
from scheduler import shutdown_scheduler, start_scheduler

# Structured logging with rotation
handler = RotatingFileHandler("bot.log", maxBytes=5 * 1024 * 1024, backupCount=3)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[handler, logging.StreamHandler()],
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


async def health_server():
    """Simple health endpoint on port 8080."""

    async def handle_client(_reader, writer):
        writer.write(b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\nok")
        await writer.drain()
        writer.close()

    server = await asyncio.start_server(handle_client, "0.0.0.0", 8080, reuse_address=True)
    logger.info("Health endpoint listening on port 8080")
    async with server:
        await server.serve_forever()


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


def main() -> None:
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
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=BOT_TOKEN,
            webhook_url=f"https://ratioandschedulebot.onrender.com/{BOT_TOKEN}",
        )
    else:
        logger.info("Запуск с polling")
        # allowed_updates говорит Telegram API, какие типы обновлений нам нужны
        application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
