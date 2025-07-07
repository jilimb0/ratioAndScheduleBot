import logging
from datetime import datetime, date
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CallbackContext
from database import (
    register_user, update_user_activity, mark_task_completed, 
    get_today_tasks_status, get_user_stats, get_completion_rate,
    is_task_completed_today
)
from scheduler import get_scheduler
from config import SCHEDULE, MESSAGES

logger = logging.getLogger(__name__)

# Создаем основную клавиатуру
def get_main_keyboard():
    """Создание основной клавиатуры"""
    keyboard = [
        [KeyboardButton("📊 Статус"), KeyboardButton("📋 Отчёт")],
        [KeyboardButton("🕐 Расписание"), KeyboardButton("ℹ️ Помощь")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    try:
        user = update.effective_user
        user_id = user.id
        
        # Регистрируем пользователя
        register_user(user_id, user.username, user.first_name, user.last_name)
        
        # Добавляем пользователя в активные для планировщика
        scheduler = get_scheduler()
        if scheduler:
            scheduler.add_user(user_id)
            
        # Отправляем приветственное сообщение с клавиатурой
        await update.message.reply_text(
            MESSAGES["start"],
            reply_markup=get_main_keyboard()
        )
        
        logger.info(f"Пользователь {user_id} ({user.username}) запустил бота")
        
    except Exception as e:
        logger.error(f"Ошибка в start_handler: {e}")
        await update.message.reply_text("Произошла ошибка. Попробуйте позже.")

async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /статус"""
    try:
        user_id = update.effective_user.id
        update_user_activity(user_id)
        
        # Получаем статус задач на сегодня
        tasks_status = get_today_tasks_status(user_id)
        
        if not tasks_status:
            await update.message.reply_text(MESSAGES["no_tasks_today"])
            return
            
        # Формируем сообщение со статусом
        status_text = MESSAGES["status_header"] + "\n\n"
        
        for task_key, is_completed in tasks_status.items():
            if task_key in SCHEDULE:
                task_name = SCHEDULE[task_key]["button_text"].replace(" ✅", "")
                task_time = SCHEDULE[task_key]["time"].strftime("%H:%M")
                
                status_icon = "✅" if is_completed else "⏳"
                status_text += f"{status_icon} {task_time} - {task_name}\n"
                
        # Добавляем статистику
        completion_rate = get_completion_rate(user_id, days=7)
        status_text += f"\n📈 Выполнение за неделю: {completion_rate:.1f}%"
        
        await update.message.reply_text(status_text)
        
    except Exception as e:
        logger.error(f"Ошибка в status_handler: {e}")
        await update.message.reply_text("Произошла ошибка при получении статуса.")

async def report_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /отчёт"""
    try:
        user_id = update.effective_user.id
        update_user_activity(user_id)
        
        # Получаем статистику за последние 7 дней
        stats = get_user_stats(user_id, days=7)
        
        if not stats:
            await update.message.reply_text("📅 За последние 7 дней данных нет.")
            return
            
        report_text = MESSAGES["report_header"] + "\n\n"
        
        # Сортируем даты по убыванию
        sorted_dates = sorted(stats.keys(), reverse=True)
        
        for date_str in sorted_dates[:7]:  # Показываем только последние 7 дней
            tasks = stats[date_str]
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            formatted_date = date_obj.strftime("%d.%m.%Y")
            
            if date_obj.date() == date.today():
                formatted_date += " (сегодня)"
            elif date_obj.date() == date.today() - timedelta(days=1):
                formatted_date += " (вчера)"
                
            report_text += f"📅 {formatted_date}:\n"
            
            for task in tasks:
                task_name = task['task_name'].replace(" ✅", "")
                report_text += f"  ✅ {task_name}\n"
                
            report_text += "\n"
            
        # Добавляем общую статистику
        completion_rate = get_completion_rate(user_id, days=7)
        report_text += f"📊 Общая эффективность: {completion_rate:.1f}%"
        
        await update.message.reply_text(report_text)
        
    except Exception as e:
        logger.error(f"Ошибка в report_handler: {e}")
        await update.message.reply_text("Произошла ошибка при создании отчёта.")

async def schedule_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /расписание"""
    try:
        user_id = update.effective_user.id
        update_user_activity(user_id)
        
        schedule_text = MESSAGES["schedule_header"] + "\n\n"
        
        # Сортируем задачи по времени
        sorted_tasks = sorted(SCHEDULE.items(), key=lambda x: x[1]["time"])
        
        for task_key, task_config in sorted_tasks:
            task_time = task_config["time"].strftime("%H:%M")
            task_name = task_config["button_text"].replace(" ✅", "")
            
            # Проверяем, выполнена ли задача сегодня
            is_completed = is_task_completed_today(user_id, task_key)
            status_icon = "✅" if is_completed else "⏰"
            
            schedule_text += f"{status_icon} {task_time} - {task_name}\n"
            
        await update.message.reply_text(schedule_text)
        
    except Exception as e:
        logger.error(f"Ошибка в schedule_handler: {e}")
        await update.message.reply_text("Произошла ошибка при показе расписания.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        update_user_activity(user_id)
        
        # Разбираем callback_data
        if query.data.startswith("complete_"):
            task_key = query.data.replace("complete_", "")
            
            if task_key in SCHEDULE:
                task_config = SCHEDULE[task_key]
                task_name = task_config["button_text"]
                
                # Пытаемся отметить задачу как выполненную
                if mark_task_completed(user_id, task_key, task_name):
                    await query.edit_message_text(
                        text=f"{task_config['message']}\n\n{MESSAGES['task_completed']}"
                    )
                    
                    # Отправляем мотивирующее сообщение
                    motivational_messages = [
                        "🎉 Отлично! Так держать!",
                        "💪 Ты молодец! Продолжай в том же духе!",
                        "⭐ Супер! Еще один шаг к цели!",
                        "🚀 Великолепно! Ты на правильном пути!",
                        "🌟 Браво! Каждое выполненное дело приближает к успеху!"
                    ]
                    
                    import random
                    motivation = random.choice(motivational_messages)
                    await context.bot.send_message(chat_id=user_id, text=motivation)
                    
                else:
                    await query.edit_message_text(
                        text=f"{task_config['message']}\n\n{MESSAGES['task_already_completed']}"
                    )
                    
            else:
                await query.edit_message_text("Неизвестная задача.")
                
    except Exception as e:
        logger.error(f"Ошибка в button_handler: {e}")
        await query.edit_message_text("Произошла ошибка при обработке нажатия.")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    try:
        user_id = update.effective_user.id
        message_text = update.message.text.lower()
        update_user_activity(user_id)
        
        # Обрабатываем нажатия на кнопки клавиатуры
        if message_text in ["📊 статус", "статус"]:
            await status_handler(update, context)
            return
            
        elif message_text in ["📋 отчёт", "отчёт"]:
            await report_handler(update, context)
            return
            
        elif message_text in ["🕐 расписание", "расписание"]:
            await schedule_handler(update, context)
            return
            
        elif message_text in ["ℹ️ помощь", "помощь"]:
            await start_handler(update, context)
            return
            
        # Обрабатываем простые ответы о выполнении задач
        task_keywords = {
            "тренировка": "morning_workout",
            "тренировку": "morning_workout",
            "зарядка": "morning_workout",
            "завтрак": "breakfast",
            "поел": "breakfast",
            "завтракал": "breakfast",
            "обед": "lunch",
            "пообедал": "lunch",
            "язык": "language_study",
            "английский": "language_study",
            "изучение": "language_study",
            "ужин": "dinner",
            "поужинал": "dinner",
            "отчёт": "daily_report",
            "отчет": "daily_report",
            "доклад": "daily_report"
        }
        
        # Ищем совпадения в тексте сообщения
        for keyword, task_key in task_keywords.items():
            if keyword in message_text:
                if any(word in message_text for word in ["сделал", "выполнил", "готов", "сделана", "выполнена"]):
                    if task_key in SCHEDULE:
                        task_config = SCHEDULE[task_key]
                        task_name = task_config["button_text"]
                        
                        if mark_task_completed(user_id, task_key, task_name):
                            await update.message.reply_text(
                                f"✅ Отлично! {task_name.replace(' ✅', '')} отмечено как выполненное!"
                            )
                        else:
                            await update.message.reply_text(
                                f"ℹ️ {task_name.replace(' ✅', '')} уже выполнено сегодня."
                            )
                        return
                        
        # Если не нашли совпадений, отправляем стандартное сообщение
        await update.message.reply_text(
            MESSAGES["unknown_message"],
            reply_markup=get_main_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Ошибка в message_handler: {e}")
        await update.message.reply_text("Произошла ошибка при обработке сообщения.")