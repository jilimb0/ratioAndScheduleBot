import asyncio
import logging
import os
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from handlers import (
    start_handler, status_handler, report_handler, schedule_handler,
    message_handler, button_handler
)
from scheduler import start_scheduler
from database import init_db
from config import BOT_TOKEN, PORT, USE_WEBHOOK, WEBHOOK_URL

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def main():
    """Основная функция для запуска бота"""
    try:
        # Инициализация базы данных
        init_db()
        
        # Создание приложения
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Регистрация обработчиков команд
        application.add_handler(CommandHandler("start", start_handler))
        application.add_handler(CommandHandler("статус", status_handler))
        application.add_handler(CommandHandler("status", status_handler))
        application.add_handler(CommandHandler("отчёт", report_handler))
        application.add_handler(CommandHandler("report", report_handler))
        application.add_handler(CommandHandler("расписание", schedule_handler))
        application.add_handler(CommandHandler("schedule", schedule_handler))
        
        # Обработчик кнопок
        application.add_handler(CallbackQueryHandler(button_handler))
        
        # Обработчик текстовых сообщений
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
        
        # Запуск планировщика
        await start_scheduler(application.bot)
        
        logger.info("Бот запущен и готов к работе!")
        
        # Выбор метода запуска (webhook или polling)
        if USE_WEBHOOK and WEBHOOK_URL:
            logger.info(f"Запуск с webhook: {WEBHOOK_URL}")
            await application.run_webhook(
                listen="0.0.0.0",
                port=PORT,
                url_path=BOT_TOKEN,
                webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}"
            )
        else:
            logger.info("Запуск с polling")
            await application.run_polling(
                allowed_updates=["message", "callback_query"],
                drop_pending_updates=True
            )
        
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        raisehandler(CommandHandler("отчёт", report_handler))
        application.add_handler(CommandHandler("report", report_handler))
        application.add_handler(CommandHandler("расписание", schedule_handler))
        application.add_handler(CommandHandler("schedule", schedule_handler))
        
        # Обработчик кнопок
        application.add_handler(CallbackQueryHandler(button_handler))
        
        # Обработчик текстовых сообщений
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
        
        # Запуск планировщика
        await start_scheduler(application.bot)
        
        logger.info("Бот запущен и готов к работе!")
        
        # Запуск бота
        await application.run_polling(allowed_updates=["message", "callback_query"])
        
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())