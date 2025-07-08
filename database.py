import sqlite3
import logging
from datetime import datetime, date
from functools import wraps
from typing import List, Dict, Optional, Any, Callable

# Импорты из вашего проекта
from config import DATABASE_PATH, SCHEDULE

logger = logging.getLogger(__name__)

# --- Декоратор для управления подключением к БД ---

def db_connection(func: Callable) -> Callable:
    """
    Декоратор, который управляет подключением к базе данных.
    Открывает соединение, создает курсор, выполняет функцию,
    сохраняет изменения и закрывает соединение.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            with sqlite3.connect(DATABASE_PATH) as conn:
                # Row_factory позволяет получать результаты в виде словарей
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                result = func(cursor, *args, **kwargs)
                conn.commit()
                return result
        except sqlite3.Error as e:
            # Логируем специфичные ошибки SQLite
            logger.error(f"Ошибка базы данных в функции {func.__name__}: {e}")
            # Для некоторых функций может потребоваться вернуть значение по умолчанию
            return None # или False, [], {} в зависимости от функции
    return wrapper

# --- Функции для работы с БД ---

@db_connection
def init_db(cursor: sqlite3.Cursor):
    """
    Инициализирует таблицы и индексы в базе данных.
    Добавлен UNIQUE constraint для предотвращения дубликатов задач.
    """
    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_activity TIMESTAMP NOT NULL
        )
    ''')

    # Таблица для отслеживания выполненных задач
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            task_key TEXT NOT NULL,
            completion_date DATE NOT NULL,
            completion_time TIMESTAMP NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
        )
    ''')
    
    # Уникальный индекс, чтобы одна и та же задача не могла быть выполнена дважды в день
    cursor.execute('''
        CREATE UNIQUE INDEX IF NOT EXISTS idx_user_task_date
        ON tasks(user_id, task_key, completion_date)
    ''')

    logger.info("База данных успешно инициализирована.")

@db_connection
def register_user(cursor: sqlite3.Cursor, user_id: int, username: Optional[str], first_name: Optional[str]):
    """Регистрирует нового пользователя или обновляет его данные."""
    cursor.execute('''
        INSERT INTO users (user_id, username, first_name, last_activity)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            username = excluded.username,
            first_name = excluded.first_name,
            last_activity = excluded.last_activity
    ''', (user_id, username, first_name, datetime.now()))
    logger.info(f"Пользователь {user_id} зарегистрирован или обновлен.")

@db_connection
def update_user_activity(cursor: sqlite3.Cursor, user_id: int):
    """Обновляет время последней активности пользователя."""
    cursor.execute('UPDATE users SET last_activity = ? WHERE user_id = ?', (datetime.now(), user_id))

@db_connection
def mark_task_completed(cursor: sqlite3.Cursor, user_id: int, task_key: str) -> bool:
    """
    Отмечает задачу как выполненную. Возвращает True, если задача была отмечена,
    и False, если она уже была выполнена ранее.
    """
    try:
        cursor.execute('''
            INSERT INTO tasks (user_id, task_key, completion_date, completion_time)
            VALUES (?, ?, ?, ?)
        ''', (user_id, task_key, date.today(), datetime.now()))
        logger.info(f"Задача {task_key} отмечена как выполненная для user {user_id}.")
        return True
    except sqlite3.IntegrityError:
        # Эта ошибка возникнет, если сработает UNIQUE constraint (задача уже есть)
        logger.warning(f"Попытка повторно отметить задачу {task_key} для user {user_id}.")
        return False

@db_connection
def get_today_tasks_status(cursor: sqlite3.Cursor, user_id: int) -> Dict[str, bool]:
    """Получает словарь со статусом выполнения всех задач из SCHEDULE на сегодня."""
    cursor.execute('''
        SELECT task_key FROM tasks WHERE user_id = ? AND completion_date = ?
    ''', (user_id, date.today()))
    
    completed_tasks = {row['task_key'] for row in cursor.fetchall()}
    
    status = {task_key: task_key in completed_tasks for task_key in SCHEDULE.keys()}
    return status

@db_connection
def get_user_stats(cursor: sqlite3.Cursor, user_id: int, days: int = 7) -> Dict[str, List[str]]:
    """Получает статистику выполненных задач за последние N дней."""
    start_date = date.today() - timedelta(days=days-1)
    cursor.execute('''
        SELECT completion_date, task_key FROM tasks
        WHERE user_id = ? AND completion_date >= ?
        ORDER BY completion_date DESC
    ''', (user_id, start_date))
    
    stats = {}
    for row in cursor.fetchall():
        date_str = row['completion_date']
        task_name = SCHEDULE.get(row['task_key'], {}).get('button_text', row['task_key'])
        
        if date_str not in stats:
            stats[date_str] = []
        stats[date_str].append(task_name)
        
    return stats

@db_connection
def get_completion_rate(cursor: sqlite3.Cursor, user_id: int, days: int = 7) -> float:
    """
    Рассчитывает процент выполнения задач за N дней.
    Примечание: расчет предполагает, что расписание (SCHEDULE) было неизменным.
    """
    start_date = date.today() - timedelta(days=days-1)
    
    # Считаем количество уникальных дней, когда пользователь выполнил хотя бы одну задачу
    cursor.execute('''
        SELECT COUNT(DISTINCT completion_date) FROM tasks WHERE user_id = ? AND completion_date >= ?
    ''', (user_id, start_date))
    active_days = cursor.fetchone()[0]

    if active_days == 0:
        return 0.0

    total_possible_tasks = len(SCHEDULE) * active_days
    if total_possible_tasks == 0:
        return 0.0

    cursor.execute('''
        SELECT COUNT(*) FROM tasks WHERE user_id = ? AND completion_date >= ?
    ''', (user_id, start_date))
    completed_tasks = cursor.fetchone()[0]
    
    return (completed_tasks / total_possible_tasks) * 100

@db_connection
def is_task_completed_today(user_id: int, task_key: str) -> bool:
    """Проверяет, выполнена ли задача с данным ключом у пользователя сегодня."""

    today = date.today()

    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM tasks
                WHERE user_id = ? AND task_key = ? AND completion_date = ? AND is_completed = 1
            ''', (user_id, task_key, today))
            result = cursor.fetchone()[0] > 0
            return result

    except sqlite3.Error as e:
        logger.error(
            f"[is_task_completed_today] Ошибка при проверке задачи '{task_key}' "
            f"для пользователя {user_id} на дату {today}: {e}"
        )
        return False