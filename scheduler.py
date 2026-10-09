import asyncio
import logging
import random
from datetime import datetime

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application

from config import CATEGORIES, MESSAGES, SCHEDULE, TIMEZONE
from database import (
    get_all_active_user_ids,
    get_all_active_users,
    get_pending_snoozed_tasks,
    get_ratio_analytics,
    get_today_tasks_status,
    get_user_schedule,
    get_user_streak,
    get_user_timezone,
    is_task_completed_today,
)

logger = logging.getLogger(__name__)

# Инициализируем планировщик
scheduler = AsyncIOScheduler(timezone=TIMEZONE)

# Хранилище дат отправки брифингов/сводок в памяти {user_id: "YYYY-MM-DD"}
_briefings_sent_today: dict[int, str] = {}
_summaries_sent_today: dict[int, str] = {}


def get_task_inline_keyboard(
    task_key: str, button_text: str = "Выполнено ✅"
) -> InlineKeyboardMarkup:
    """Создает интуитивную инлайн-клавиатуру для задачи: Выполнить, Отложить, Пропустить."""
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(f"{button_text}", callback_data=f"complete_{task_key}")],
            [
                InlineKeyboardButton("⏱ Отложить на 15м", callback_data=f"snooze_{task_key}"),
                InlineKeyboardButton("⏭ Пропустить", callback_data=f"skip_{task_key}"),
            ],
        ]
    )


async def send_user_task_reminder(
    app: Application,
    user_id: int,
    task_key: str,
    title: str,
    category: str = "routine",
    duration: int = 30,
) -> None:
    """Отправляет персональное интерактивное напоминание о задаче конкретному пользователю."""
    if is_task_completed_today(user_id, task_key):
        return

    cat_meta = CATEGORIES.get(category, {"name": "Задача", "emoji": "📌"})
    text = (
        f"{cat_meta['emoji']} **Время задачи:** {title}\n\n"
        f"Категория: {cat_meta['name']}\n"
        f"Ориентировочное время: {duration} мин.\n\n"
        "Нажмите кнопку после завершения или отложите напоминание:"
    )
    keyboard = get_task_inline_keyboard(task_key, f"{title} ✅")
    try:
        await app.bot.send_message(
            chat_id=user_id,
            text=text,
            reply_markup=keyboard,
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"Не удалось отправить задачу {task_key} пользователю {user_id}: {e}")


async def send_morning_briefing(app: Application, user_id: int) -> None:
    """Отправляет утренний брифинг с планом на день."""
    try:
        tz_name = get_user_timezone(user_id)
        tz = pytz.timezone(tz_name)
        now_local = datetime.now(tz)
        day_of_week = now_local.isoweekday()  # 1 (Mon) .. 7 (Sun)

        schedule = get_user_schedule(user_id, day_of_week=day_of_week)
        streak = get_user_streak(user_id)

        streak_text = f"🔥 Ваш стрик: **{streak} дн.**\n" if streak > 0 else ""

        briefing = [
            f"🌅 **Утренний брифинг на {now_local.strftime('%d.%m.%Y')}**\n",
            streak_text,
            "📋 **Запланировано на сегодня:**",
        ]

        if schedule:
            for task in schedule:
                cat_emoji = CATEGORIES.get(task.get("category", ""), {}).get("emoji", "📌")
                dur = task["duration_minutes"]
                task_line = f"• `{task['time_str']}` {cat_emoji} {task['title']} ({dur} мин)"
                briefing.append(task_line)
        else:
            briefing.append("На сегодня нет задач. Настройте расписание командой /tasks!")

        quote = random.choice(MESSAGES.get("motivational", ["Сделайте этот день продуктивным!"]))
        briefing.append(f"\n💬 _{quote}_")

        await app.bot.send_message(
            chat_id=user_id,
            text="\n".join(briefing),
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"Ошибка при отправке утреннего брифинга user {user_id}: {e}")


async def send_daily_summary_to_user(app: Application, user_id: int) -> None:
    """Отправляет вечернюю сводку дня и баланс времени конкретному пользователю."""
    try:
        tasks_status = get_today_tasks_status(user_id)
        schedule = get_user_schedule(user_id)
        titles = {s["task_key"]: s["title"] for s in schedule}

        completed_names = []
        for key, is_done in tasks_status.items():
            if is_done:
                name = titles.get(key) or SCHEDULE.get(key, {}).get("button_text", key).replace(
                    " ✅", ""
                )
                completed_names.append(name)

        analytics = get_ratio_analytics(user_id, days=7)
        score = analytics.get("balance_score", 0)
        ratio_val = analytics.get("work_to_rest_ratio", 1.0)

        if completed_names:
            summary = [
                "🌟 **Итоги дня и баланс:**\n",
                f"Выполнено задач: **{len(completed_names)}** из {len(tasks_status)}",
                "\n".join(f"✅ {name}" for name in completed_names),
                f"\n⚖️ Баланс работы и отдыха за неделю: **{ratio_val} : 1**",
                f"Индекс гармонии: **{score}/100**",
                f"_{analytics.get('recommendation', '')}_",
            ]
        else:
            summary = [
                "📅 Сегодня не было отмеченных задач.",
                "Завтра новый день — восстановите силы и настройтесь на баланс!",
            ]

        await app.bot.send_message(
            chat_id=user_id,
            text="\n\n".join(summary),
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"Не удалось отправить вечернюю сводку пользователю {user_id}: {e}")


async def check_user_schedules_tick(app: Application) -> None:
    """
    Основной тик планировщика (вызывается каждую минуту).
    Проверяет локальное время каждого активного пользователя,
    рассылает утренние брифинги, напоминания по расписанию и вечерние отчеты.
    """
    users = get_all_active_users()
    if not users:
        return

    # 1. Проверяем отложенные напоминания (Snoozed tasks)
    pending_snoozes = get_pending_snoozed_tasks()
    for item in pending_snoozes:
        u_id = item["user_id"]
        t_key = item["task_key"]
        sched = get_user_schedule(u_id)
        task_info = next((t for t in sched if t["task_key"] == t_key), None)
        title = (
            task_info["title"]
            if task_info
            else SCHEDULE.get(t_key, {}).get("button_text", t_key).replace(" ✅", "")
        )
        cat = task_info["category"] if task_info else "routine"
        dur = task_info["duration_minutes"] if task_info else 30
        await send_user_task_reminder(app, u_id, t_key, f"🔔 [Отложено] {title}", cat, dur)
        await asyncio.sleep(0.05)

    # 2. Проверяем регулярные задачи пользователей с учетом их таймзоны
    for u in users:
        u_id = u["user_id"]
        tz_name = u.get("timezone") or "Europe/Moscow"
        try:
            tz = pytz.timezone(tz_name)
        except Exception:
            tz = pytz.timezone("Europe/Moscow")

        now_local = datetime.now(tz)
        current_hm = now_local.strftime("%H:%M")
        today_date_str = now_local.strftime("%Y-%m-%d")
        day_of_week = now_local.isoweekday()

        # Утренний брифинг в 08:00
        if current_hm == "08:00" and _briefings_sent_today.get(u_id) != today_date_str:
            _briefings_sent_today[u_id] = today_date_str
            await send_morning_briefing(app, u_id)
            await asyncio.sleep(0.05)

        # Вечерний отчет в 22:00
        if current_hm == "22:00" and _summaries_sent_today.get(u_id) != today_date_str:
            _summaries_sent_today[u_id] = today_date_str
            await send_daily_summary_to_user(app, u_id)
            await asyncio.sleep(0.05)

        # Напоминания по задачам пользователя
        user_tasks = get_user_schedule(u_id, day_of_week=day_of_week)
        for task in user_tasks:
            if task["time_str"] == current_hm:
                await send_user_task_reminder(
                    app,
                    u_id,
                    task["task_key"],
                    task["title"],
                    task.get("category", "routine"),
                    task.get("duration_minutes", 30),
                )
                await asyncio.sleep(0.05)


# --- Сохранение совместимости со старыми вызовами ---


async def send_reminder_job(app: Application, task_key: str):
    """Задача обратной совместимости."""
    task_config = SCHEDULE.get(task_key)
    if not task_config:
        return
    user_ids = get_all_active_user_ids()
    for user_id in user_ids:
        title = task_config.get("button_text", task_key).replace(" ✅", "")
        await send_user_task_reminder(
            app,
            user_id,
            task_key,
            title,
            task_config.get("category", "routine"),
            task_config.get("duration_minutes", 30),
        )


async def send_daily_summary_job(app: Application):
    """Задача обратной совместимости: вечерняя сводка всем."""
    user_ids = get_all_active_user_ids()
    for user_id in user_ids:
        await send_daily_summary_to_user(app, user_id)


async def send_motivational_message_job(app: Application):
    """Задача: отправить случайное мотивационное сообщение активным пользователям."""
    message = random.choice(MESSAGES.get("motivational", []))
    if not message:
        return
    user_ids = get_all_active_user_ids()
    for user_id in user_ids:
        try:
            await app.bot.send_message(chat_id=user_id, text=message)
            await asyncio.sleep(0.05)
        except Exception as e:
            logger.error(f"Не удалось отправить мотивацию {user_id}: {e}")


# --- Управление планировщиком ---


async def start_scheduler(app: Application):
    """Инициализирует и запускает динамический планировщик."""
    # Ежеминутный диспетчер персональных расписаний и часовых поясов
    scheduler.add_job(
        check_user_schedules_tick,
        trigger="interval",
        minutes=1,
        args=[app],
        id="user_schedules_tick",
        replace_existing=True,
    )

    # Дневная мотивация в 13:00 и 18:00
    scheduler.add_job(
        send_motivational_message_job,
        trigger="cron",
        hour="13,18",
        minute=30,
        args=[app],
        id="motivational_broadcast",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Динамический планировщик задач запущен.")


async def shutdown_scheduler():
    """Корректно останавливает планировщик при выключении бота."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Планировщик остановлен.")
