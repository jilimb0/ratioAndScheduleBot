import sqlite3
import logging
from datetime import datetime, date
from typing import List, Dict, Optional
from config import DATABASE_PATH

logger = logging.getLogger(__name__)

def init_db():
    """Инициализация базы данных"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Создание таблицы для отслеживания задач
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                task_key TEXT NOT NULL,
                task_name TEXT NOT NULL,
                completion_date DATE NOT NULL,
                completion_time TIMESTAMP NOT NULL,
                is_completed BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Создание таблицы для пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Создание индексов для быстрого поиска
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_tasks_user_date 
            ON tasks(user_id, completion_date)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_tasks_user_key_date 
            ON tasks(user_id, task_key, completion_date)
        ''')
        
        conn.commit()
        conn.close()
        
        logger.info("База данных успешно инициализирована")
        
    except Exception as e:
        logger.error(f"Ошибка при инициализации базы данных: {e}")
        raise

def register_user(user_id: int, username: str = None, first_name: str = None, last_name: str = None):
    """Регистрация нового пользователя"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO users (user_id, username, first_name, last_name, last_activity)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, last_name, datetime.now()))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Пользователь {user_id} зарегистрирован")
        
    except Exception as e:
        logger.error(f"Ошибка при регистрации пользователя {user_id}: {e}")

def update_user_activity(user_id: int):
    """Обновление последней активности пользователя"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users SET last_activity = ? WHERE user_id = ?
        ''', (datetime.now(), user_id))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        logger.error(f"Ошибка при обновлении активности пользователя {user_id}: {e}")

def mark_task_completed(user_id: int, task_key: str, task_name: str) -> bool:
    """Отметка задачи как выполненной"""
    try:
        today = date.today()
        
        # Проверяем, не выполнена ли уже задача сегодня
        if is_task_completed_today(user_id, task_key):
            return False
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO tasks (user_id, task_key, task_name, completion_date, completion_time, is_completed)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, task_key, task_name, today, datetime.now(), True))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Задача {task_key} выполнена пользователем {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при отметке задачи {task_key} для пользователя {user_id}: {e}")
        return False

def is_task_completed_today(user_id: int, task_key: str) -> bool:
    """Проверка, выполнена ли задача сегодня"""
    try:
        today = date.today()
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) FROM tasks 
            WHERE user_id = ? AND task_key = ? AND completion_date = ? AND is_completed = 1
        ''', (user_id, task_key, today))
        
        result = cursor.fetchone()[0] > 0
        conn.close()
        
        return result
        
    except Exception as e:
        logger.error(f"Ошибка при проверке задачи {task_key} для пользователя {user_id}: {e}")
        return False

def get_today_tasks_status(user_id: int) -> Dict[str, bool]:
    """Получение статуса всех задач на сегодня"""
    try:
        from config import SCHEDULE
        
        today = date.today()
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT task_key FROM tasks 
            WHERE user_id = ? AND completion_date = ? AND is_completed = 1
        ''', (user_id, today))
        
        completed_tasks = set(row[0] for row in cursor.fetchall())
        conn.close()
        
        # Создаем словарь со статусом всех задач
        status = {}
        for task_key in SCHEDULE.keys():
            status[task_key] = task_key in completed_tasks
            
        return status
        
    except Exception as e:
        logger.error(f"Ошибка при получении статуса задач для пользователя {user_id}: {e}")
        return {}

def get_user_stats(user_id: int, days: int = 7) -> Dict:
    """Получение статистики пользователя за указанное количество дней"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                completion_date,
                COUNT(*) as completed_tasks,
                task_key,
                task_name
            FROM tasks 
            WHERE user_id = ? AND completion_date >= date('now', '-{} days') AND is_completed = 1
            GROUP BY completion_date, task_key, task_name
            ORDER BY completion_date DESC
        '''.format(days), (user_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        # Группировка по датам
        stats = {}
        for row in rows:
            date_str = row[0]
            if date_str not in stats:
                stats[date_str] = []
            stats[date_str].append({
                'task_key': row[2],
                'task_name': row[3],
                'count': row[1]
            })
            
        return stats
        
    except Exception as e:
        logger.error(f"Ошибка при получении статистики для пользователя {user_id}: {e}")
        return {}

def get_completion_rate(user_id: int, days: int = 7) -> float:
    """Получение процента выполнения задач за указанный период"""
    try:
        from config import SCHEDULE
        
        total_possible_tasks = len(SCHEDULE) * days
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) FROM tasks 
            WHERE user_id = ? AND completion_date >= date('now', '-{} days') AND is_completed = 1
        '''.format(days), (user_id,))
        
        completed_tasks = cursor.fetchone()[0]
        conn.close()
        
        if total_possible_tasks == 0:
            return 0.0
            
        return (completed_tasks / total_possible_tasks) * 100
        
    except Exception as e:
        logger.error(f"Ошибка при расчете процента выполнения для пользователя {user_id}: {e}")
        return 0.0