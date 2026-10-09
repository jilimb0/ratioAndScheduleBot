import logging
import sqlite3
from collections.abc import Callable
from datetime import date, datetime, timedelta
from functools import wraps
from typing import Any, Optional

from config import CATEGORIES, DATABASE_PATH, SCHEDULE, TIMEZONE

logger = logging.getLogger(__name__)


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
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                result = func(cursor, *args, **kwargs)
                conn.commit()
                return result
        except sqlite3.Error as e:
            logger.error(f"Ошибка базы данных в функции {func.__name__}: {e}")
            return None

    return wrapper


@db_connection
def init_db(cursor: sqlite3.Cursor) -> None:
    """Инициализирует таблицы, индексы и выполняет миграции схемы."""
    # Таблица пользователей
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            timezone TEXT DEFAULT 'Europe/Moscow',
            is_pro INTEGER DEFAULT 0,
            pro_until TIMESTAMP,
            created_at TIMESTAMP,
            last_activity TIMESTAMP NOT NULL
        )
    """)

    # Миграция колонок users, если таблица была создана ранее без них
    cursor.execute("PRAGMA table_info(users)")
    existing_user_cols = {row["name"] for row in cursor.fetchall()}
    if "timezone" not in existing_user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN timezone TEXT DEFAULT 'Europe/Moscow'")
    if "is_pro" not in existing_user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN is_pro INTEGER DEFAULT 0")
    if "pro_until" not in existing_user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN pro_until TIMESTAMP")
    if "created_at" not in existing_user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN created_at TIMESTAMP")

    # Таблица пользовательских расписаний и привычек (Custom schedules & habits)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            task_key TEXT NOT NULL,
            title TEXT NOT NULL,
            time_str TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'routine',
            duration_minutes INTEGER NOT NULL DEFAULT 30,
            days_of_week TEXT NOT NULL DEFAULT '1,2,3,4,5,6,7',
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
            UNIQUE(user_id, task_key)
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_user_schedules_active
        ON user_schedules(user_id, is_active)
    """)

    # Таблица для отслеживания выполненных задач
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            task_key TEXT NOT NULL,
            category TEXT DEFAULT 'routine',
            duration_minutes INTEGER DEFAULT 30,
            status TEXT DEFAULT 'completed',
            completion_date DATE NOT NULL,
            completion_time TIMESTAMP NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
        )
    """)

    # Миграция колонок tasks
    cursor.execute("PRAGMA table_info(tasks)")
    existing_task_cols = {row["name"] for row in cursor.fetchall()}
    if "category" not in existing_task_cols:
        cursor.execute("ALTER TABLE tasks ADD COLUMN category TEXT DEFAULT 'routine'")
    if "duration_minutes" not in existing_task_cols:
        cursor.execute("ALTER TABLE tasks ADD COLUMN duration_minutes INTEGER DEFAULT 30")
    if "status" not in existing_task_cols:
        cursor.execute("ALTER TABLE tasks ADD COLUMN status TEXT DEFAULT 'completed'")

    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_user_task_date
        ON tasks(user_id, task_key, completion_date)
    """)

    # Таблица подписок и транзакций Telegram Stars
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            telegram_payment_charge_id TEXT,
            provider_payment_charge_id TEXT,
            amount_stars INTEGER NOT NULL,
            created_at TIMESTAMP NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
        )
    """)

    # Таблица отложенных напоминаний (Snooze)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS snoozed_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            task_key TEXT NOT NULL,
            snooze_until TIMESTAMP NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
        )
    """)

    logger.info("База данных успешно инициализирована.")


@db_connection
def register_user(
    cursor: sqlite3.Cursor,
    user_id: int,
    username: Optional[str],
    first_name: Optional[str],
) -> None:
    """Регистрирует нового пользователя или обновляет его данные."""
    now = datetime.now()
    default_tz = "Europe/Moscow" if TIMEZONE == "UTC" else TIMEZONE
    cursor.execute(
        """
        INSERT INTO users (
            user_id, username, first_name, timezone, is_pro, created_at, last_activity
        )
        VALUES (?, ?, ?, ?, 0, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            username = excluded.username,
            first_name = excluded.first_name,
            last_activity = excluded.last_activity
    """,
        (user_id, username, first_name, default_tz, now, now),
    )

    # Инициализация персонального расписания по умолчанию, если оно еще не заполнено
    cursor.execute("SELECT COUNT(*) FROM user_schedules WHERE user_id = ?", (user_id,))
    count = cursor.fetchone()[0]
    if count == 0:
        for key, conf in SCHEDULE.items():
            title = conf.get("button_text", key).replace(" ✅", "")
            t_str = conf["time"].strftime("%H:%M")
            cat = conf.get("category", "routine")
            dur = conf.get("duration_minutes", 30)
            cursor.execute(
                """
                INSERT OR IGNORE INTO user_schedules (
                    user_id, task_key, title, time_str, category,
                    duration_minutes, days_of_week, is_active, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, '1,2,3,4,5,6,7', 1, ?)
            """,
                (user_id, key, title, t_str, cat, dur, now),
            )

    logger.info(f"Пользователь {user_id} зарегистрирован или обновлен.")


@db_connection
def get_user(cursor: sqlite3.Cursor, user_id: int) -> Optional[dict[str, Any]]:
    """Получить информацию о пользователе."""
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


@db_connection
def set_user_timezone(cursor: sqlite3.Cursor, user_id: int, timezone_str: str) -> bool:
    """Установить часовой пояс пользователя."""
    cursor.execute(
        "UPDATE users SET timezone = ?, last_activity = ? WHERE user_id = ?",
        (timezone_str, datetime.now(), user_id),
    )
    return cursor.rowcount > 0


@db_connection
def get_user_timezone(cursor: sqlite3.Cursor, user_id: int) -> str:
    """Получить часовой пояс пользователя."""
    cursor.execute("SELECT timezone FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if row and row["timezone"]:
        return row["timezone"]
    return "Europe/Moscow" if TIMEZONE == "UTC" else TIMEZONE


@db_connection
def update_user_activity(cursor: sqlite3.Cursor, user_id: int) -> None:
    """Обновляет время последней активности пользователя."""
    cursor.execute(
        "UPDATE users SET last_activity = ? WHERE user_id = ?",
        (datetime.now(), user_id),
    )


@db_connection
def is_user_pro(cursor: sqlite3.Cursor, user_id: int) -> bool:
    """Проверяет, активен ли у пользователя статус Pro."""
    cursor.execute("SELECT is_pro, pro_until FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row:
        return False
    if row["is_pro"] and row["pro_until"]:
        pro_until = (
            datetime.fromisoformat(row["pro_until"])
            if isinstance(row["pro_until"], str)
            else row["pro_until"]
        )
        if pro_until > datetime.now():
            return True
        # Срок истек — снимаем флаг
        cursor.execute("UPDATE users SET is_pro = 0 WHERE user_id = ?", (user_id,))
        return False
    return bool(row["is_pro"])


@db_connection
def activate_user_pro(cursor: sqlite3.Cursor, user_id: int, days: int = 30) -> bool:
    """Активирует или продлевает Pro-подписку пользователю."""
    cursor.execute("SELECT pro_until FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    now = datetime.now()
    if row and row["pro_until"]:
        current_until = (
            datetime.fromisoformat(row["pro_until"])
            if isinstance(row["pro_until"], str)
            else row["pro_until"]
        )
        new_until = max(now, current_until) + timedelta(days=days)
    else:
        new_until = now + timedelta(days=days)

    cursor.execute(
        "UPDATE users SET is_pro = 1, pro_until = ? WHERE user_id = ?",
        (new_until, user_id),
    )
    return True


@db_connection
def record_payment(
    cursor: sqlite3.Cursor,
    user_id: int,
    telegram_charge_id: str,
    provider_charge_id: str,
    amount_stars: int,
) -> bool:
    """Сохраняет запись об успешной оплате подписки."""
    cursor.execute(
        """
        INSERT INTO payments (
            user_id, telegram_payment_charge_id, provider_payment_charge_id,
            amount_stars, created_at
        )
        VALUES (?, ?, ?, ?, ?)
    """,
        (user_id, telegram_charge_id, provider_charge_id, amount_stars, datetime.now()),
    )
    activate_user_pro(user_id, days=30)
    return True


# --- Управление расписанием и привычками пользователя ---


@db_connection
def get_user_schedule(
    cursor: sqlite3.Cursor, user_id: int, day_of_week: Optional[int] = None
) -> list[dict[str, Any]]:
    """
    Возвращает список запланированных задач пользователя.
    day_of_week: 1 (Пн) .. 7 (Вс). Если указан, фильтрует по дням недели.
    """
    cursor.execute(
        """
        SELECT * FROM user_schedules
        WHERE user_id = ? AND is_active = 1
        ORDER BY time_str ASC
    """,
        (user_id,),
    )
    rows = [dict(row) for row in cursor.fetchall()]

    if day_of_week is not None:
        target_str = str(day_of_week)
        rows = [r for r in rows if target_str in r.get("days_of_week", "").split(",")]

    return rows


@db_connection
def add_user_task(
    cursor: sqlite3.Cursor,
    user_id: int,
    task_key: str,
    title: str,
    time_str: str,
    category: str = "routine",
    duration_minutes: int = 30,
    days_of_week: str = "1,2,3,4,5,6,7",
) -> bool:
    """Добавить или обновить задачу в расписании пользователя."""
    cursor.execute(
        """
        INSERT INTO user_schedules (
            user_id, task_key, title, time_str, category,
            duration_minutes, days_of_week, is_active, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
        ON CONFLICT(user_id, task_key) DO UPDATE SET
            title = excluded.title,
            time_str = excluded.time_str,
            category = excluded.category,
            duration_minutes = excluded.duration_minutes,
            days_of_week = excluded.days_of_week,
            is_active = 1
    """,
        (
            user_id,
            task_key,
            title,
            time_str,
            category,
            duration_minutes,
            days_of_week,
            datetime.now(),
        ),
    )
    return True


@db_connection
def delete_user_task(cursor: sqlite3.Cursor, user_id: int, task_key: str) -> bool:
    """Удалить задачу из расписания пользователя."""
    cursor.execute(
        "DELETE FROM user_schedules WHERE user_id = ? AND task_key = ?",
        (user_id, task_key),
    )
    return cursor.rowcount > 0


# --- Отметка выполнения, откладывание и пропуск ---


@db_connection
def mark_task_completed(
    cursor: sqlite3.Cursor,
    user_id: int,
    task_key: str,
    task_name: Optional[str] = None,
    category: Optional[str] = None,
    duration: Optional[int] = None,
) -> bool:
    """
    Отмечает задачу как выполненную. Возвращает True, если задача была отмечена,
    и False, если она уже была выполнена ранее сегодня.
    """
    # Определяем категорию и длительность, если не переданы
    if not category or not duration:
        cursor.execute(
            """
            SELECT category, duration_minutes FROM user_schedules
            WHERE user_id = ? AND task_key = ?
            """,
            (user_id, task_key),
        )
        row = cursor.fetchone()
        if row:
            category = category or row["category"]
            duration = duration or row["duration_minutes"]
        elif task_key in SCHEDULE:
            category = category or SCHEDULE[task_key].get("category", "routine")
            duration = duration or SCHEDULE[task_key].get("duration_minutes", 30)
        else:
            category = category or "routine"
            duration = duration or 30

    try:
        cursor.execute(
            """
            INSERT INTO tasks (
                user_id, task_key, category, duration_minutes, status,
                completion_date, completion_time
            )
            VALUES (?, ?, ?, ?, 'completed', ?, ?)
        """,
            (user_id, task_key, category, duration, date.today(), datetime.now()),
        )
        # Очищаем отложенные напоминания для этой задачи
        cursor.execute(
            "DELETE FROM snoozed_tasks WHERE user_id = ? AND task_key = ?",
            (user_id, task_key),
        )
        logger.info(f"Задача {task_key} отмечена как выполненная для user {user_id}.")
        return True
    except sqlite3.IntegrityError:
        logger.warning(f"Попытка повторно отметить задачу {task_key} для user {user_id}.")
        return False


@db_connection
def snooze_task(cursor: sqlite3.Cursor, user_id: int, task_key: str, minutes: int = 15) -> datetime:
    """Отложить напоминание по задаче на N минут."""
    snooze_until = datetime.now() + timedelta(minutes=minutes)
    cursor.execute(
        """
        INSERT INTO snoozed_tasks (user_id, task_key, snooze_until)
        VALUES (?, ?, ?)
    """,
        (user_id, task_key, snooze_until),
    )
    logger.info(f"Задача {task_key} для user {user_id} отложена до {snooze_until}.")
    return snooze_until


@db_connection
def skip_task(cursor: sqlite3.Cursor, user_id: int, task_key: str) -> bool:
    """Пропустить задачу на сегодня."""
    try:
        cursor.execute(
            """
            INSERT INTO tasks (
                user_id, task_key, category, duration_minutes, status,
                completion_date, completion_time
            )
            VALUES (?, ?, 'routine', 0, 'skipped', ?, ?)
        """,
            (user_id, task_key, date.today(), datetime.now()),
        )
        cursor.execute(
            "DELETE FROM snoozed_tasks WHERE user_id = ? AND task_key = ?", (user_id, task_key)
        )
        return True
    except sqlite3.IntegrityError:
        return False


@db_connection
def is_task_completed_today(cursor: sqlite3.Cursor, user_id: int, task_key: str) -> bool:
    """Проверка, выполнена или пропущена ли задача сегодня."""
    try:
        today = date.today()
        cursor.execute(
            """
            SELECT COUNT(*) FROM tasks
            WHERE user_id = ? AND task_key = ? AND completion_date = ?
        """,
            (user_id, task_key, today),
        )
        row = cursor.fetchone()
        return (row[0] > 0) if row else False
    except sqlite3.Error as e:
        logger.error(f"Ошибка при проверке задачи {task_key} для пользователя {user_id}: {e}")
        return False


@db_connection
def get_today_tasks_status(cursor: sqlite3.Cursor, user_id: int) -> dict[str, bool]:
    """Получает словарь со статусом выполнения всех активных задач на сегодня."""
    cursor.execute(
        """
        SELECT task_key, status FROM tasks WHERE user_id = ? AND completion_date = ?
    """,
        (user_id, date.today()),
    )
    completed_tasks = {row["task_key"]: row["status"] for row in cursor.fetchall()}

    # Загружаем задачи пользователя из user_schedules
    cursor.execute(
        "SELECT task_key FROM user_schedules WHERE user_id = ? AND is_active = 1", (user_id,)
    )
    custom_tasks = [row["task_key"] for row in cursor.fetchall()]

    keys_to_check = custom_tasks if custom_tasks else list(SCHEDULE.keys())
    status = {task_key: completed_tasks.get(task_key) == "completed" for task_key in keys_to_check}
    return status


@db_connection
def get_user_stats(cursor: sqlite3.Cursor, user_id: int, days: int = 7) -> dict[str, list[Any]]:
    """Получает статистику выполненных задач за последние N дней."""
    start_date = date.today() - timedelta(days=days - 1)
    cursor.execute(
        """
        SELECT completion_date, task_key, category, duration_minutes, status
        FROM tasks
        WHERE user_id = ? AND completion_date >= ? AND status = 'completed'
        ORDER BY completion_date DESC
    """,
        (user_id, start_date),
    )
    completed_rows = cursor.fetchall()

    # Получаем словарь заголовков задач для пользователя
    cursor.execute("SELECT task_key, title FROM user_schedules WHERE user_id = ?", (user_id,))
    titles = {row["task_key"]: row["title"] for row in cursor.fetchall()}

    stats: dict[str, list[Any]] = {}
    for row in completed_rows:
        date_str = str(row["completion_date"])
        task_key = row["task_key"]
        default_conf = SCHEDULE.get(task_key, {})
        task_name = titles.get(task_key) or default_conf.get("button_text", task_key).replace(
            " ✅", ""
        )

        if date_str not in stats:
            stats[date_str] = []
        stats[date_str].append(task_name)

    return stats


@db_connection
def get_completion_rate(cursor: sqlite3.Cursor, user_id: int, days: int = 7) -> float:
    """Рассчитывает процент выполнения задач за N дней."""
    start_date = date.today() - timedelta(days=days - 1)

    cursor.execute(
        """
        SELECT COUNT(DISTINCT completion_date) FROM tasks
        WHERE user_id = ? AND completion_date >= ? AND status = 'completed'
    """,
        (user_id, start_date),
    )
    active_days = cursor.fetchone()[0]
    if active_days == 0:
        return 0.0

    cursor.execute(
        "SELECT COUNT(*) FROM user_schedules WHERE user_id = ? AND is_active = 1", (user_id,)
    )
    sched_count = cursor.fetchone()[0]
    tasks_per_day = sched_count if sched_count > 0 else len(SCHEDULE)

    total_possible = tasks_per_day * active_days
    if total_possible == 0:
        return 0.0

    cursor.execute(
        """
        SELECT COUNT(*) FROM tasks
        WHERE user_id = ? AND completion_date >= ? AND status = 'completed'
    """,
        (user_id, start_date),
    )
    completed_count = cursor.fetchone()[0]

    return min(100.0, (completed_count / total_possible) * 100)


# --- Аналитика соотношения (Ratio Analytics Engine) ---


@db_connection
def get_ratio_analytics(cursor: sqlite3.Cursor, user_id: int, days: int = 7) -> dict[str, Any]:
    """
    Рассчитывает детальную аналитику баланса работы и отдыха (Work/Life/Rest Ratio).
    Возвращает разбивку по категориям, соотношение, скор баланса и рекомендации.
    """
    start_date = date.today() - timedelta(days=days - 1)
    cursor.execute(
        """
        SELECT category, COUNT(*) as task_count, SUM(duration_minutes) as total_mins
        FROM tasks
        WHERE user_id = ? AND completion_date >= ? AND status = 'completed'
        GROUP BY category
    """,
        (user_id, start_date),
    )

    category_data: dict[str, dict[str, Any]] = {}
    for cat_key, meta in CATEGORIES.items():
        category_data[cat_key] = {
            "name": meta["name"],
            "emoji": meta["emoji"],
            "minutes": 0,
            "count": 0,
            "percentage": 0.0,
        }

    total_minutes = 0
    total_tasks = 0

    for row in cursor.fetchall():
        cat = row["category"] or "routine"
        if cat not in category_data:
            category_data[cat] = {
                "name": cat.capitalize(),
                "emoji": "📌",
                "minutes": 0,
                "count": 0,
                "percentage": 0.0,
            }
        mins = row["total_mins"] or 0
        cnt = row["task_count"] or 0
        category_data[cat]["minutes"] = mins
        category_data[cat]["count"] = cnt
        total_minutes += mins
        total_tasks += cnt

    if total_minutes > 0:
        for cat in category_data.values():
            cat["percentage"] = round((cat["minutes"] / total_minutes) * 100, 1)

    work_mins = category_data.get("work", {}).get("minutes", 0) + category_data.get(
        "study", {}
    ).get("minutes", 0)
    rest_mins = category_data.get("rest", {}).get("minutes", 0) + category_data.get(
        "health", {}
    ).get("minutes", 0)

    # Вычисление Work/Rest Ratio
    if rest_mins > 0:
        work_to_rest_ratio = round(work_mins / rest_mins, 2)
    elif work_mins > 0:
        work_to_rest_ratio = 9.99
    else:
        work_to_rest_ratio = 1.0

    # Расчет индекса гармонии / баланса (Life Balance Score: 0-100)
    # Идеальное соотношение продуктивности и восстановления — от 1.5:1 до 2.5:1
    if total_minutes == 0:
        balance_score = 0
        recommendation = (
            "За последние 7 дней пока нет выполненных задач. Начните с первой привычки!"
        )
    elif 1.2 <= work_to_rest_ratio <= 2.5 and rest_mins > 0:
        balance_score = 92
        recommendation = (
            "🌟 Прекрасный баланс! Нагрузка и восстановление гармонично сбалансированы."
        )
    elif work_to_rest_ratio > 3.0:
        balance_score = max(40, 100 - int(work_to_rest_ratio * 15))
        recommendation = (
            "⚠️ Высокий риск перегрузки! Время работы значительно превышает отдых. "
            "Запланируйте паузы."
        )
    elif work_to_rest_ratio < 0.8:
        balance_score = 70
        recommendation = (
            "💡 Много времени на восстановление. Отличное время добавить важные рабочие цели!"
        )
    else:
        balance_score = 80
        recommendation = "👍 Стабильный темп. Продолжайте фиксировать привычки."

    # Генерация визуальных прогресс-баров
    visual_bars = []
    for _cat_key, data in category_data.items():
        if data["minutes"] > 0 or total_minutes == 0:
            pct = data["percentage"]
            filled_len = int(round(pct / 10))
            bar = "█" * filled_len + "░" * (10 - filled_len)
            hours = round(data["minutes"] / 60, 1)
            visual_bars.append(f"{data['emoji']} {data['name']}:\n  `{bar}` {pct}% ({hours}ч)")

    return {
        "days": days,
        "total_tasks": total_tasks,
        "total_minutes": total_minutes,
        "total_hours": round(total_minutes / 60, 1),
        "work_minutes": work_mins,
        "rest_minutes": rest_mins,
        "work_to_rest_ratio": work_to_rest_ratio,
        "balance_score": balance_score,
        "recommendation": recommendation,
        "categories": category_data,
        "visual_bars": visual_bars,
    }


@db_connection
def get_user_streak(cursor: sqlite3.Cursor, user_id: int) -> int:
    """Подсчитывает непрерывную серию дней (streak) выполнения хотя бы одной задачи."""
    cursor.execute(
        """
        SELECT DISTINCT completion_date FROM tasks
        WHERE user_id = ? AND status = 'completed'
        ORDER BY completion_date DESC
    """,
        (user_id,),
    )
    rows = cursor.fetchall()
    if not rows:
        return 0

    dates = [datetime.strptime(str(row["completion_date"]), "%Y-%m-%d").date() for row in rows]
    today = date.today()
    streak = 0
    curr = today

    # Если сегодня еще не отмечено, проверяем со вчерашнего дня
    if dates and dates[0] == today:
        streak += 1
        curr = today - timedelta(days=1)
    elif dates and dates[0] == today - timedelta(days=1):
        curr = today - timedelta(days=1)
    else:
        return 0

    for d in dates[streak:]:
        if d == curr:
            streak += 1
            curr -= timedelta(days=1)
        elif d < curr:
            break

    return streak


@db_connection
def get_all_active_user_ids(cursor: sqlite3.Cursor) -> list[int]:
    """Возвращает список ID всех пользователей, которые были активны за последние 30 дней."""
    thirty_days_ago = datetime.now() - timedelta(days=30)
    cursor.execute("SELECT user_id FROM users WHERE last_activity > ?", (thirty_days_ago,))
    return [row["user_id"] for row in cursor.fetchall()]


@db_connection
def get_all_active_users(cursor: sqlite3.Cursor) -> list[dict[str, Any]]:
    """Возвращает полную информацию об активных пользователях для планировщика."""
    thirty_days_ago = datetime.now() - timedelta(days=30)
    cursor.execute(
        "SELECT user_id, username, timezone, is_pro FROM users WHERE last_activity > ?",
        (thirty_days_ago,),
    )
    return [dict(row) for row in cursor.fetchall()]


@db_connection
def get_pending_snoozed_tasks(cursor: sqlite3.Cursor) -> list[dict[str, Any]]:
    """Возвращает список задач, для которых наступило время повторного напоминания."""
    now = datetime.now()
    cursor.execute(
        """
        SELECT id, user_id, task_key FROM snoozed_tasks
        WHERE snooze_until <= ?
    """,
        (now,),
    )
    rows = [dict(r) for r in cursor.fetchall()]
    if rows:
        ids = [str(r["id"]) for r in rows]
        cursor.execute(f"DELETE FROM snoozed_tasks WHERE id IN ({','.join(ids)})")
    return rows
