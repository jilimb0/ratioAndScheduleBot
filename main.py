import asyncio
import json
import logging
import os
from logging.handlers import RotatingFileHandler

from aiohttp import web

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
from tma_validator import parse_and_validate_init_data

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


async def health_server():
    """Health check endpoint on PORT, serves WebApp, and validates TMA initData using aiohttp."""
    routes = web.RouteTableDef()

    @routes.get("/")
    @routes.get("/health")
    async def handle_health(_request: web.Request):
        return web.Response(
            text="ok",
            content_type="text/plain",
            headers={"Access-Control-Allow-Origin": "*", "X-Content-Type-Options": "nosniff"},
        )

    @routes.get("/webapp")
    @routes.get("/webapp/")
    @routes.get("/webapp/index.html")
    async def handle_webapp(_request: web.Request):
        if WEBAPP_CONTENT:
            return web.Response(
                body=WEBAPP_CONTENT,
                content_type="text/html",
                charset="utf-8",
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "X-Content-Type-Options": "nosniff",
                    "X-Frame-Options": "SAMEORIGIN",
                },
            )
        return web.Response(status=404, text="WebApp not found")

    @routes.route("*", "/api/validate")
    async def handle_validate(request: web.Request):
        init_data = request.headers.get("x-telegram-init-data") or request.query_string
        if not init_data and request.can_read_body:
            try:
                body_json = await request.json()
                if isinstance(body_json, dict):
                    init_data = body_json.get("initData") or body_json.get("init_data")
            except Exception:
                pass

        valid, data, err = parse_and_validate_init_data(init_data, BOT_TOKEN)
        if not valid:
            err_msg = err or "Invalid initData"
            return web.json_response(
                {"ok": False, "error": err_msg},
                status=401,
                headers={"Access-Control-Allow-Origin": "*", "X-Content-Type-Options": "nosniff"},
            )

        user_info = data.get("user") if data else None
        return web.json_response(
            {"ok": True, "user": user_info},
            headers={"Access-Control-Allow-Origin": "*", "X-Content-Type-Options": "nosniff"},
        )

    app = web.Application(client_max_size=1024 * 1024)
    app.add_routes(routes)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"Health and WebApp server listening on port {PORT} via aiohttp")

    while True:
        await asyncio.sleep(3600)


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
