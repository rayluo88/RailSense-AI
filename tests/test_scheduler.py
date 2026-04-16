"""Tests for src/scheduler.py — background ingestion scheduler."""

from datetime import datetime, timezone, timedelta
from unittest.mock import patch

from src.scheduler import SGT, _is_operating_hours, get_scheduler_status


def test_is_operating_hours_during_day():
    with patch("src.scheduler.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2026, 4, 16, 12, 0, tzinfo=SGT)
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        assert _is_operating_hours() is True


def test_is_operating_hours_before_start():
    with patch("src.scheduler.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2026, 4, 16, 7, 0, tzinfo=SGT)
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        assert _is_operating_hours() is False


def test_is_operating_hours_after_end():
    with patch("src.scheduler.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2026, 4, 16, 23, 0, tzinfo=SGT)
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        assert _is_operating_hours() is False


def test_is_operating_hours_at_boundary_start():
    with patch("src.scheduler.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2026, 4, 16, 9, 0, tzinfo=SGT)
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        assert _is_operating_hours() is True


def test_is_operating_hours_at_boundary_end():
    with patch("src.scheduler.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2026, 4, 16, 22, 0, tzinfo=SGT)
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        assert _is_operating_hours() is False


def test_get_scheduler_status_structure():
    status = get_scheduler_status()
    assert "enabled" in status
    assert "operating_hours" in status
    assert "currently_active" in status
    assert "tasks" in status
    assert "0900-2200 SGT" == status["operating_hours"]


def test_get_scheduler_status_disabled_without_key():
    with patch("src.scheduler.settings") as mock_settings:
        mock_settings.enable_scheduler = True
        mock_settings.lta_api_key = ""
        mock_settings.scheduler_start_hour = 9
        mock_settings.scheduler_end_hour = 22
        status = get_scheduler_status()
        assert status["enabled"] is False
