import asyncio
import logging
import os
from logging.handlers import RotatingFileHandler

from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
)

from config import BOT_TOKEN, PORT, USE_WEBHOOK, WEBHOOK_URL
from database import init_db
from handlers import (
    add_task_handler,
    briefing_handler,
    button_handler,
    del_task_handler,
    message_handler,
    precheckout_handler,
    pro_subscription_handler,
    ratio_handler,
    report_handler,
    schedule_handler,
    share_card_handler,
    start_handler,
    status_handler,
    successful_payment_handler,
    tasks_management_handler,
    timezone_handler,
    webapp_data_handler,
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

WEBAPP_FILE = os.path.join(os.path.dirname(__file__), "webapp", "index.html")
WEBAPP_CONTENT = b""
if os.path.exists(WEBAPP_FILE):
    with open(WEBAPP_FILE, "rb") as f:
        WEBAPP_CONTENT = f.read()


from tma_validator import parse_and_validate_init_data, validate_init_data

async def health_server():
    """Health check endpoint on PORT, serves Telegram WebApp at /webapp, and protects TMA API endpoints."""

    async def handle_client(reader, writer):
        try:
            line = await reader.readline()
            req_str = line.decode("utf-8", errors="ignore")
            parts = req_str.split(" ")
            method = parts[0] if len(parts) > 0 else "GET"
            full_path = parts[1] if len(parts) > 1 else "/"
            path = full_path.split("?")[0]
            query_str = full_path.split("?")[1] if "?" in full_path else ""

            # Read headers
            headers = {}
            while True:
                h_line = await reader.readline()
                if not h_line or h_line == b"\r\n" or h_line == b"\n":
                    break
                h_str = h_line.decode("utf-8", errors="ignore").strip()
                if ":" in h_str:
                    hk, hv = h_str.split(":", 1)
                    headers[hk.strip().lower()] = hv.strip()

            if path in ("/webapp", "/webapp/", "/webapp/index.html") and WEBAPP_CONTENT:
                resp = (
                    b"HTTP/1.1 200 OK\r\n"
                    b"Content-Type: text/html; charset=utf-8\r\n"
                    b"Access-Control-Allow-Origin: *\r\n"
                    b"Content-Length: "
                    + str(len(WEBAPP_CONTENT)).encode()
                    + b"\r\n\r\n"
                    + WEBAPP_CONTENT
                )
            elif path == "/api/validate":
                init_data = headers.get("x-telegram-init-data") or query_str
                valid, data, err = parse_and_validate_init_data(init_data, BOT_TOKEN)
                if not valid:
                    err_body = json.dumps({"ok": False, "error": err or "Invalid initData"}).encode("utf-8")
                    resp = (
                        b"HTTP/1.1 401 Unauthorized\r\n"
                        b"Content-Type: application/json; charset=utf-8\r\n"
                        b"Access-Control-Allow-Origin: *\r\n"
                        b"Content-Length: " + str(len(err_body)).encode() + b"\r\n\r\n"
                        + err_body
                    )
                else:
                    success_body = json.dumps({"ok": True, "user": data.get("user")}).encode("utf-8")
                    resp = (
                        b"HTTP/1.1 200 OK\r\n"
                        b"Content-Type: application/json; charset=utf-8\r\n"
                        b"Access-Control-Allow-Origin: *\r\n"
                        b"Content-Length: " + str(len(success_body)).encode() + b"\r\n\r\n"
                        + success_body
                    )
            else:
                resp = b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nAccess-Control-Allow-Origin: *\r\n\r\nok"

            writer.write(resp)
            await writer.drain()
        except Exception as e:
            logger.debug(f"Error serving client in health_server: {e}")
        finally:
            writer.close()

    server = await asyncio.start_server(handle_client, "0.0.0.0", PORT, reuse_address=True)
    logger.info(f"Health and WebApp server listening on port {PORT}")
    async with server:
        await server.serve_forever()



async def post_init(application: Application):
    """
    Выполняется после инициализации приложения:
    инициализирует БД и запускает планировщик.
    """
    init_db()
    await start_scheduler(application)
    logger.info("База данных и планировщик инициализированы.")


async def post_shutdown(application: Application):
    """
    Выполняется перед завершением работы приложения:
    корректно останавливает планировщик.
    """
    await shutdown_scheduler()
    logger.info("Планировщик остановлен.")


def main() -> None:
    """Основная функция для запуска бота."""
    logger.info("Запуск бота...")

    # Создание приложения с хуками жизненного цикла
    application = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    # Регистрация обработчиков команд
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("status", status_handler))
    application.add_handler(CommandHandler("report", report_handler))
    application.add_handler(CommandHandler("schedule", schedule_handler))
    application.add_handler(CommandHandler(["ratio", "balance"], ratio_handler))
    application.add_handler(CommandHandler("briefing", briefing_handler))
    application.add_handler(CommandHandler("tasks", tasks_management_handler))
    application.add_handler(CommandHandler("addtask", add_task_handler))
    application.add_handler(CommandHandler("deltask", del_task_handler))
    application.add_handler(CommandHandler("timezone", timezone_handler))
    application.add_handler(CommandHandler("pro", pro_subscription_handler))
    application.add_handler(CommandHandler("share", share_card_handler))

    # Обработчики платежей Telegram Stars
    application.add_handler(PreCheckoutQueryHandler(precheckout_handler))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))

    # Обработчик данных из Telegram WebApp
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, webapp_data_handler))

    # Обработчик инлайн-кнопок
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
        logger.info("Запуск с polling + health/webapp endpoint")
        asyncio.ensure_future(health_server())
        application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
