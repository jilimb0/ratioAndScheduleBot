"""Tests for database.py — uses temporary SQLite files."""

import os
import tempfile
from datetime import date

import pytest

from config import DATABASE_PATH, SCHEDULE
from database import (
    get_all_active_user_ids,
    get_completion_rate,
    get_today_tasks_status,
    get_user_stats,
    init_db,
    is_task_completed_today,
    mark_task_completed,
    register_user,
)


@pytest.fixture(autouse=True)
def temp_db():
    """Use a temporary database file for each test."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_path = tmp.name
    orig_path = DATABASE_PATH
    import database as db_module

    db_module.DATABASE_PATH = tmp_path
    init_db()
    yield
    os.unlink(tmp_path)
    db_module.DATABASE_PATH = orig_path


def test_init_db_creates_tables():
    """Tables should be created without error."""
    import sqlite3

    import database as db_module

    conn = sqlite3.connect(db_module.DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}
    assert "users" in tables
    assert "tasks" in tables
    conn.close()


def test_register_user_creates_record():
    register_user(user_id=1, username="testuser", first_name="Test")
    stats = get_today_tasks_status(1)
    assert isinstance(stats, dict)


def test_register_user_updates_existing():
    register_user(user_id=1, username="oldname", first_name="Old")
    register_user(user_id=1, username="newname", first_name="New")


def test_mark_task_completed_returns_true():
    result = mark_task_completed(1, "morning_workout")
    assert result is True


def test_mark_task_completed_duplicate_returns_false():
    mark_task_completed(1, "morning_workout")
    result = mark_task_completed(1, "morning_workout")
    assert result is False


def test_get_today_tasks_status_shows_completed():
    mark_task_completed(1, "morning_workout")
    status = get_today_tasks_status(1)
    assert status.get("morning_workout") is True
    assert status.get("breakfast") is False


def test_get_today_tasks_status_all_pending():
    status = get_today_tasks_status(1)
    for key in SCHEDULE:
        assert status.get(key) is False, f"{key} should be False"


def test_get_user_stats_returns_tasks_by_date():
    mark_task_completed(1, "morning_workout")
    mark_task_completed(1, "breakfast")
    stats = get_user_stats(1, days=7)
    today_str = date.today().isoformat()
    assert today_str in stats
    assert len(stats[today_str]) == 2


def test_get_user_stats_empty_for_no_data():
    stats = get_user_stats(999, days=7)
    assert stats == {}


def test_get_completion_rate_returns_float():
    mark_task_completed(1, "morning_workout")
    rate = get_completion_rate(1, days=7)
    assert isinstance(rate, float)
    assert 0 <= rate <= 100


def test_get_completion_rate_zero_for_no_activity():
    rate = get_completion_rate(999, days=7)
    assert rate == 0.0


def test_is_task_completed_today_true():
    mark_task_completed(1, "morning_workout")
    assert is_task_completed_today(1, "morning_workout") is True


def test_is_task_completed_today_false():
    assert is_task_completed_today(1, "morning_workout") is False


def test_is_task_completed_today_unknown_user():
    assert is_task_completed_today(999, "morning_workout") is False


def test_get_all_active_user_ids_returns_list():
    register_user(user_id=1, username="test", first_name="Test")
    register_user(user_id=2, username="test2", first_name="Test2")
    users = get_all_active_user_ids()
    assert 1 in users
    assert 2 in users


def test_get_all_active_user_ids_excludes_inactive():
    register_user(user_id=1, username="active", first_name="Active")
    users = get_all_active_user_ids()
    assert isinstance(users, list)


def test_mark_all_tasks_completed():
    for task_key in SCHEDULE:
        mark_task_completed(1, task_key)
    status = get_today_tasks_status(1)
    for key in SCHEDULE:
        assert status.get(key) is True


def test_multiple_users_independent():
    mark_task_completed(1, "morning_workout")
    assert is_task_completed_today(2, "morning_workout") is False
    mark_task_completed(2, "morning_workout")
    assert is_task_completed_today(1, "morning_workout") is True
    assert is_task_completed_today(2, "morning_workout") is True


def test_multiple_days_stats():
    mark_task_completed(1, "morning_workout")
    mark_task_completed(1, "breakfast")
    stats = get_user_stats(1, days=30)
    today_str = date.today().isoformat()
    assert today_str in stats
    assert len(stats[today_str]) == 2


def test_user_timezone():
    from database import get_user_timezone, set_user_timezone

    register_user(1, "tzuser", "Tz")
    set_user_timezone(1, "Asia/Almaty")
    assert get_user_timezone(1) == "Asia/Almaty"


def test_user_schedules_crud():
    from database import add_user_task, delete_user_task, get_user_schedule

    register_user(1, "scheduser", "Sched")
    sched = get_user_schedule(1)
    assert len(sched) > 0

    add_user_task(
        1,
        "deep_work",
        "Глубокая работа",
        "10:00",
        category="work",
        duration_minutes=90,
        days_of_week="1,2,3,4,5",
    )
    sched_updated = get_user_schedule(1)
    keys = [item["task_key"] for item in sched_updated]
    assert "deep_work" in keys

    # Filter by day of week (Friday = 5, Sunday = 7)
    friday_tasks = [t["task_key"] for t in get_user_schedule(1, day_of_week=5)]
    sunday_tasks = [t["task_key"] for t in get_user_schedule(1, day_of_week=7)]
    assert "deep_work" in friday_tasks
    assert "deep_work" not in sunday_tasks

    delete_user_task(1, "deep_work")
    sched_deleted = get_user_schedule(1)
    keys_after = [item["task_key"] for item in sched_deleted]
    assert "deep_work" not in keys_after


def test_snooze_and_skip():
    from database import get_pending_snoozed_tasks, skip_task, snooze_task

    register_user(1, "snoozer", "Snooze")
    snooze_until = snooze_task(1, "morning_workout", minutes=-1)
    assert snooze_until is not None

    pending = get_pending_snoozed_tasks()
    assert any(p["task_key"] == "morning_workout" for p in pending)

    res = skip_task(1, "breakfast")
    assert res is True
    assert is_task_completed_today(1, "breakfast") is True


def test_ratio_analytics():
    from database import get_ratio_analytics

    register_user(1, "ratiouser", "Ratio")
    mark_task_completed(1, "language_study", category="study", duration=60)
    mark_task_completed(1, "morning_workout", category="health", duration=45)

    analytics = get_ratio_analytics(1, days=7)
    assert analytics["total_tasks"] == 2
    assert analytics["total_minutes"] == 105
    assert analytics["work_minutes"] == 60
    assert analytics["rest_minutes"] == 45
    assert analytics["work_to_rest_ratio"] > 0
    assert 0 <= analytics["balance_score"] <= 100
    assert len(analytics["visual_bars"]) > 0


def test_user_streak():
    from database import get_user_streak

    register_user(1, "streakuser", "Streak")
    assert get_user_streak(1) == 0

    mark_task_completed(1, "morning_workout")
    assert get_user_streak(1) == 1


def test_pro_activation_and_payments():
    from database import activate_user_pro, is_user_pro, record_payment

    register_user(1, "prouser", "Pro")
    assert is_user_pro(1) is False

    activate_user_pro(1, days=30)
    assert is_user_pro(1) is True

    record_payment(1, "tg_123", "prov_123", 150)
    assert is_user_pro(1) is True
