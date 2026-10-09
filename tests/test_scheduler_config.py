"""Tests for configuration and keyboard helpers."""

from config import CATEGORIES, COMMON_TIMEZONES, SCHEDULE
from handlers import get_main_keyboard, get_timezone_inline_keyboard
from scheduler import get_task_inline_keyboard


def test_categories_structure():
    assert "work" in CATEGORIES
    assert "rest" in CATEGORIES
    assert "health" in CATEGORIES
    assert "study" in CATEGORIES
    assert "routine" in CATEGORIES
    for cat in CATEGORIES.values():
        assert "name" in cat
        assert "emoji" in cat


def test_default_schedule_structure():
    for _task_key, task_conf in SCHEDULE.items():
        assert "time" in task_conf
        assert "button_text" in task_conf
        assert "category" in task_conf
        assert "duration_minutes" in task_conf
        assert task_conf["duration_minutes"] > 0


def test_common_timezones():
    assert len(COMMON_TIMEZONES) > 0
    tz_codes = [tz[0] for tz in COMMON_TIMEZONES]
    assert "Europe/Moscow" in tz_codes
    assert "UTC" in tz_codes


def test_main_keyboard():
    keyboard = get_main_keyboard()
    assert keyboard is not None
    assert len(keyboard.keyboard) >= 3


def test_task_inline_keyboard():
    kb = get_task_inline_keyboard("morning_workout", "Выполнено ✅")
    assert kb is not None
    assert len(kb.inline_keyboard) == 2
    assert kb.inline_keyboard[0][0].callback_data == "complete_morning_workout"
    assert kb.inline_keyboard[1][0].callback_data == "snooze_morning_workout"
    assert kb.inline_keyboard[1][1].callback_data == "skip_morning_workout"


def test_timezone_inline_keyboard():
    tz_kb = get_timezone_inline_keyboard()
    assert tz_kb is not None
    assert len(tz_kb.inline_keyboard) > 0
