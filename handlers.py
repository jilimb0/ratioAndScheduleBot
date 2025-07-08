import logging
import random
from datetime import datetime, date, timedelta

from telegram import Update
from telegram.ext import ContextTypes
from telegram import ReplyKeyboardMarkup, KeyboardButton

# Предполагается, что эти файлы существуют и настроены корректно
from database import (
    register_user,
    update_user_activity,
    mark_task_completed,
    get_today_tasks_status,
    get_user_stats,
    get_completion_rate,
    is_task_completed_today,
)
from config import SCHEDULE, MESSAGES

logger = logging.getLogger(__name__)

# --- Клавиатуры ---

def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Возвращает основную клавиатуру с кнопками."""
    keyboard = [
        [KeyboardButton("📊 Статус"), KeyboardButton("📈 Отчёт")],
        [KeyboardButton("🗓 Расписание"), KeyboardButton("ℹ️ Помощь")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

# --- Обработчики команд и кнопок ---

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start и кнопки 'Помощь'."""
    user = update.effective_user
    try:
        # Регистрация или обновление данных пользователя в БД
        register_user(user_id=user.id, username=user.username, first_name=user.first_name)
        logger.info(f"Пользователь {user.id} ({user.username}) запустил/перезапустил бота.")

        await update.message.reply_text(
            MESSAGES.get("start", "Добро пожаловать!"),
            reply_markup=get_main_keyboard(),
        )
    except Exception as e:
        logger.error(f"Ошибка в start_handler для user_id {user.id}: {e}")
        await update.message.reply_text("Произошла ошибка при запуске. Попробуйте позже.")


async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает статус выполнения задач на сегодня."""
    user = update.effective_user
    try:
        update_user_activity(user.id)
        tasks_status = get_today_tasks_status(user.id)

        if not tasks_status:
            await update.message.reply_text(MESSAGES.get("no_tasks_today", "На сегодня задач нет."))
            return

        status_lines = [MESSAGES.get("status_header", "Статус на сегодня:")]
        for task_key, is_completed in tasks_status.items():
            task_config = SCHEDULE.get(task_key)
            if task_config:
                task_name = task_config.get("button_text", task_key).replace(" ✅", "")
                task_time = task_config.get("time").strftime("%H:%M")
                status_icon = "✅" if is_completed else "⏳"
                status_lines.append(f"{status_icon} {task_time} - {task_name}")

        completion_rate = get_completion_rate(user.id, days=7)
        status_lines.append(f"\n📈 Выполнение за неделю: {completion_rate:.1f}%")

        await update.message.reply_text("\n".join(status_lines))
    except Exception as e:
        logger.error(f"Ошибка в status_handler для user_id {user.id}: {e}")
        await update.message.reply_text("Не удалось получить статус. Попробуйте снова.")


async def report_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает отчёт о выполненных задачах за последнюю неделю."""
    user = update.effective_user
    try:
        update_user_activity(user.id)
        stats = get_user_stats(user.id, days=7)

        if not stats:
            await update.message.reply_text("📊 За последние 7 дней данных для отчёта нет.")
            return

        report_lines = [MESSAGES.get("report_header", "Отчёт за 7 дней:")]
        sorted_dates = sorted(stats.keys(), reverse=True)

        for date_str in sorted_dates:
            tasks = stats[date_str]
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            
            day_label = ""
            if date_obj == date.today():
                day_label = " (сегодня)"
            elif date_obj == date.today() - timedelta(days=1):
                day_label = " (вчера)"
            
            report_lines.append(f"\n📅 {date_obj.strftime('%d.%m.%Y')}{day_label}:")
            for task in tasks:
                task_name = task.get('task_name', 'Неизвестная задача').replace(" ✅", "")
                report_lines.append(f"  ✅ {task_name}")

        completion_rate = get_completion_rate(user.id, days=7)
        report_lines.append(f"\n\n📊 Общая эффективность: {completion_rate:.1f}%")

        await update.message.reply_text("\n".join(report_lines))
    except Exception as e:
        logger.error(f"Ошибка в report_handler для user_id {user.id}: {e}")
        await update.message.reply_text("Не удалось создать отчёт.")


async def schedule_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает полное расписание задач."""
    user = update.effective_user
    try:
        update_user_activity(user.id)
        schedule_lines = [MESSAGES.get("schedule_header", "Ваше расписание:")]
        
        sorted_tasks = sorted(SCHEDULE.items(), key=lambda item: item[1].get("time"))

        for task_key, task_config in sorted_tasks:
            task_time = task_config.get("time").strftime("%H:%M")
            task_name = task_config.get("button_text", task_key).replace(" ✅", "")
            is_completed = is_task_completed_today(user.id, task_key)
            status_icon = "✅" if is_completed else "⏰"
            schedule_lines.append(f"{status_icon} {task_time} - {task_name}")

        await update.message.reply_text("\n".join(schedule_lines))
    except Exception as e:
        logger.error(f"Ошибка в schedule_handler для user_id {user.id}: {e}")
        await update.message.reply_text("Не удалось показать расписание.")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на inline-кнопки (например, 'Выполнить')."""
    query = update.callback_query
    await query.answer()  # Обязательно подтвердить получение callback'а

    user = query.from_user
    task_key = query.data.replace("complete_", "")
    
    try:
        update_user_activity(user.id)
        task_config = SCHEDULE.get(task_key)

        if not task_config:
            await query.edit_message_text("Ошибка: задача не найдена.")
            return

        task_name = task_config.get("button_text", "Задача")
        if mark_task_completed(user.id, task_key, task_name):
            await query.edit_message_text(
                f"{task_config.get('message', '')}\n\n{MESSAGES.get('task_completed', 'Задача выполнена!')}"
            )
            # Отправляем отдельное мотивирующее сообщение
            motivational_message = random.choice(MESSAGES.get("motivational", ["Отлично!"]))
            await context.bot.send_message(chat_id=user.id, text=motivational_message)
        else:
            await query.edit_message_text(
                f"{task_config.get('message', '')}\n\n{MESSAGES.get('task_already_completed', 'Задача уже была выполнена.')}"
            )
    except Exception as e:
        logger.error(f"Ошибка в button_handler для user_id {user.id} и task_key {task_key}: {e}")
        await query.edit_message_text("Произошла ошибка при обработке нажатия.")


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик всех текстовых сообщений, включая нажатия на Reply-кнопки."""
    user = update.effective_user
    text = update.message.text.lower().strip()

    # Убираем эмодзи для более простого сравнения
    clean_text = text.replace("📊 ", "").replace("📈 ", "").replace("🗓 ", "").replace("ℹ️ ", "")

    try:
        # Маршрутизация на основе текста кнопки
        if clean_text == "статус":
            await status_handler(update, context)
        elif clean_text == "отчёт":
            await report_handler(update, context)
        elif clean_text == "расписание":
            await schedule_handler(update, context)
        elif clean_text == "помощь":
            await start_handler(update, context)
        else:
            # Если текст не похож на кнопку, отправляем стандартный ответ
            await update.message.reply_text(
                MESSAGES.get("unknown_message", "Я вас не понимаю."),
                reply_markup=get_main_keyboard()
            )
    except Exception as e:
        logger.error(f"Ошибка в message_handler для user_id {user.id} с текстом '{text}': {e}")
        await update.message.reply_text("Произошла ошибка при обработке вашего сообщения.")