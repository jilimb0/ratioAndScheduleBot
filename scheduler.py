import asyncio
import logging
from datetime import datetime, time, timedelta
from typing import Dict, Set
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from config import SCHEDULE
from database import get_user_stats, update_user_activity

logger = logging.getLogger(__name__)

class TaskScheduler:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.active_users: Set[int] = set()
        self.running = False
        
    def add_user(self, user_id: int):
        """Добавление пользователя в активные"""
        self.active_users.add(user_id)
        logger.info(f"Пользователь {user_id} добавлен в активные")
        
    def remove_user(self, user_id: int):
        """Удаление пользователя из активных"""
        self.active_users.discard(user_id)
        logger.info(f"Пользователь {user_id} удален из активных")
        
    async def send_reminder(self, user_id: int, task_key: str, task_config: Dict):
        """Отправка напоминания пользователю"""
        try:
            # Создаем кнопку для отметки выполнения
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    task_config["button_text"], 
                    callback_data=f"complete_{task_key}"
                )]
            ])
            
            await self.bot.send_message(
                chat_id=user_id,
                text=task_config["message"],
                reply_markup=keyboard
            )
            
            logger.info(f"Напоминание {task_key} отправлено пользователю {user_id}")
            
        except Exception as e:
            logger.error(f"Ошибка при отправке напоминания {task_key} пользователю {user_id}: {e}")
            # Если не удалось отправить сообщение, возможно пользователь заблокировал бота
            if "blocked" in str(e).lower() or "not found" in str(e).lower():
                self.remove_user(user_id)
                
    async def check_and_send_reminders(self):
        """Проверка времени и отправка напоминаний"""
        current_time = datetime.now().time()
        
        for task_key, task_config in SCHEDULE.items():
            task_time = task_config["time"]
            
            # Проверяем, совпадает ли текущее время с временем задачи (с точностью до минуты)
            if (current_time.hour == task_time.hour and 
                current_time.minute == task_time.minute):
                
                # Отправляем напоминания всем активным пользователям
                for user_id in self.active_users.copy():
                    await self.send_reminder(user_id, task_key, task_config)
                    
                # Небольшая задержка между отправками
                await asyncio.sleep(0.1)
                
    async def send_daily_summary(self):
        """Отправка ежедневной сводки в конце дня"""
        try:
            summary_time = time(22, 0)  # 22:00
            current_time = datetime.now().time()
            
            if (current_time.hour == summary_time.hour and 
                current_time.minute == summary_time.minute):
                
                for user_id in self.active_users.copy():
                    try:
                        stats = get_user_stats(user_id, days=1)
                        if stats:
                            today_str = datetime.now().strftime("%Y-%m-%d")
                            today_tasks = stats.get(today_str, [])
                            
                            if today_tasks:
                                summary = "🌟 Сводка дня:\n\n"
                                for task in today_tasks:
                                    summary += f"✅ {task['task_name']}\n"
                                summary += f"\n🎯 Выполнено задач: {len(today_tasks)}"
                            else:
                                summary = "📅 Сегодня задачи не выполнялись. Завтра новый день - новые возможности! 💪"
                                
                            await self.bot.send_message(
                                chat_id=user_id,
                                text=summary
                            )
                            
                    except Exception as e:
                        logger.error(f"Ошибка при отправке сводки пользователю {user_id}: {e}")
                        
        except Exception as e:
            logger.error(f"Ошибка при отправке ежедневных сводок: {e}")
            
    async def scheduler_loop(self):
        """Основной цикл планировщика"""
        self.running = True
        logger.info("Планировщик запущен")
        
        while self.running:
            try:
                await self.check_and_send_reminders()
                await self.send_daily_summary()
                
                # Ожидаем 60 секунд перед следующей проверкой
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"Ошибка в цикле планировщика: {e}")
                await asyncio.sleep(60)
                
    def stop(self):
        """Остановка планировщика"""
        self.running = False
        logger.info("Планировщик остановлен")

# Глобальный экземпляр планировщика
scheduler = None

async def start_scheduler(bot: Bot):
    """Запуск планировщика"""
    global scheduler
    scheduler = TaskScheduler(bot)
    
    # Запускаем планировщик в фоновом режиме
    asyncio.create_task(scheduler.scheduler_loop())
    
def get_scheduler() -> TaskScheduler:
    """Получение экземпляра планировщика"""
    global scheduler
    return scheduler

async def send_motivational_message():
    """Отправка мотивационных сообщений"""
    motivational_messages = [
        "💪 Помни: каждый день - это новая возможность стать лучше!",
        "🌟 Маленькие шаги каждый день приводят к большим результатам!",
        "🎯 Ты можешь больше, чем думаешь. Продолжай идти к цели!",
        "🚀 Успех - это сумма небольших усилий, повторяемых изо дня в день!",
        "⭐ Будь терпелив с собой. Прогресс требует времени!",
    ]
    
    import random
    message = random.choice(motivational_messages)
    
    if scheduler:
        for user_id in scheduler.active_users.copy():
            try:
                await scheduler.bot.send_message(
                    chat_id=user_id,
                    text=message
                )
            except Exception as e:
                logger.error(f"Ошибка при отправке мотивационного сообщения пользователю {user_id}: {e}")

# Функция для отправки мотивационных сообщений в случайное время
async def schedule_motivational_messages():
    """Планирование мотивационных сообщений"""
    import random
    
    while True:
        # Ждем случайное время от 2 до 6 часов
        wait_time = random.randint(2*3600, 6*3600)
        await asyncio.sleep(wait_time)
        
        # Отправляем мотивационное сообщение в рабочее время (9:00 - 20:00)
        current_hour = datetime.now().hour
        if 9 <= current_hour <= 20:
            await send_motivational_message()