import logging
import random
from telegram.ext import Application
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import SCHEDULE, MESSAGES  # Конфигурация задач и сообщений
from database import get_all_active_user_ids, is_task_completed_today, get_today_tasks_status # Новая функция в database.py

logger = logging.getLogger(__name__)

# Инициализируем планировщик
scheduler = AsyncIOScheduler(timezone="Europe/Moscow") # Укажите ваш часовой пояс

# --- Функции-задачи (Jobs) ---

async def send_reminder_job(app: Application, task_key: str):
    """Задача: отправить напоминание по конкретной задаче всем активным пользователям."""
    task_config = SCHEDULE.get(task_key)
    if not task_config:
        logger.warning(f"Конфигурация для задачи {task_key} не найдена.")
        return

    logger.info(f"Запускаю рассылку напоминания для задачи: {task_key}")
    
    # 1. Получаем ID всех активных пользователей прямо из БД
    user_ids = get_all_active_user_ids()
    if not user_ids:
        logger.info("Нет активных пользователей для отправки напоминаний.")
        return

    # 2. Создаем кнопку один раз
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            task_config["button_text"],
            callback_data=f"complete_{task_key}"
        )
    ]])

    # 3. Рассылаем напоминания
    for user_id in user_ids:
        # Проверяем, не выполнил ли пользователь уже эту задачу
        if not is_task_completed_today(user_id, task_key):
            try:
                await app.bot.send_message(
                    chat_id=user_id,
                    text=task_config["message"],
                    reply_markup=keyboard
                )
                await asyncio.sleep(0.1) # Небольшая задержка между отправками
            except Exception as e:
                logger.error(f"Не удалось отправить напоминание {task_key} пользователю {user_id}: {e}")


async def send_daily_summary_job(app: Application):
    """Задача: отправить в конце дня сводку о выполненных задачах."""
    logger.info("Запускаю рассылку ежедневных сводок.")
    user_ids = get_all_active_user_ids()

    for user_id in user_ids:
        try:
            tasks_status = get_today_tasks_status(user_id)
            completed_tasks = [
                SCHEDULE[key]['button_text'].replace(" ✅", "")
                for key, done in tasks_status.items() if done
            ]

            if completed_tasks:
                summary = "🌟 **Сводка дня:**\n\n"
                summary += "\n".join(f"✅ {name}" for name in completed_tasks)
                summary += f"\n\nОтличная работа! Выполнено задач: **{len(completed_tasks)}** 💪"
            else:
                summary = "📅 Сегодня не было отмечено выполненных задач. Завтра — новый день для достижений!"
            
            await app.bot.send_message(chat_id=user_id, text=summary, parse_mode='Markdown')
            await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"Не удалось отправить сводку пользователю {user_id}: {e}")


async def send_motivational_message_job(app: Application):
    """Задача: отправить случайное мотивационное сообщение."""
    logger.info("Запускаю рассылку мотивационных сообщений.")
    message = random.choice(MESSAGES.get("motivational", []))
    if not message:
        return

    user_ids = get_all_active_user_ids()
    for user_id in user_ids:
        try:
            await app.bot.send_message(chat_id=user_id, text=message)
            await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"Не удалось отправить мотивацию пользователю {user_id}: {e}")


# --- Управление планировщиком ---

async def start_scheduler(app: Application):
    """
    Инициализирует и запускает все задачи в планировщике.
    Вызывается один раз при старте бота через post_init.
    """
    # 1. Добавляем задачу-напоминание для каждого элемента в SCHEDULE
    for task_key, config in SCHEDULE.items():
        task_time = config['time']
        scheduler.add_job(
            send_reminder_job,
            trigger='cron',
            hour=task_time.hour,
            minute=task_time.minute,
            args=[app, task_key],
            id=f"reminder_{task_key}" # Уникальный ID для каждой задачи
        )
        logger.info(f"Задача-напоминание '{task_key}' запланирована на {task_time.strftime('%H:%M')}.")

    # 2. Добавляем задачу для ежедневной сводки
    scheduler.add_job(send_daily_summary_job, trigger='cron', hour=22, minute=0, args=[app], id="daily_summary")
    logger.info("Задача для ежедневной сводки запланирована на 22:00.")

    # 3. Добавляем задачу для мотивационных сообщений (например, в 10, 14, 18 часов)
    scheduler.add_job(send_motivational_message_job, trigger='cron', hour='10,14,18', minute=5, args=[app], id="motivational")
    logger.info("Задача для мотивационных сообщений запланирована на 10:05, 14:05, 18:05.")
    
    # Запускаем сам планировщик
    scheduler.start()
    logger.info("Планировщик запущен со всеми задачами.")


async def shutdown_scheduler():
    """Корректно останавливает планировщик при выключении бота."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Планировщик остановлен.")