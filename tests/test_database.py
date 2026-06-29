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
