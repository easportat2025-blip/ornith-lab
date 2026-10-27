import datetime as dt

import ops_health as h


def test_age_minutes_parses_z():
    now = dt.datetime(2026, 10, 27, 3, 0, tzinfo=dt.timezone.utc)
    assert h.age_minutes("2026-10-27T02:50:00Z", now) == 10.0


def test_age_minutes_invalid():
    assert h.age_minutes("") is None
    assert h.age_minutes("not-a-date") is None


def test_decide_actions_healthy_loop():
    runs = {
        "kaggle-watchdog.yml": {"status": "completed", "age_minutes": 5},
        "ops-tick.yml": {"status": "in_progress", "age_minutes": 2},
    }
    assert h.decide_actions(runs, stale_minutes=25) == []


def test_decide_actions_active_watchdog_never_duplicates():
    runs = {
        "kaggle-watchdog.yml": {"status": "in_progress", "age_minutes": 99},
        "ops-tick.yml": {"status": "completed", "age_minutes": 99},
    }
    assert h.decide_actions(runs, stale_minutes=25) == []


def test_decide_actions_stale_watchdog():
    runs = {
        "kaggle-watchdog.yml": {"status": "completed", "age_minutes": 30},
        "ops-tick.yml": {"status": "completed", "age_minutes": 5},
    }
    actions = h.decide_actions(runs, stale_minutes=25)
    assert actions == [{
        "workflow": "kaggle-watchdog.yml",
        "reason": "watchdog stale or missing",
        "inputs": {"auto_push": "true"},
    }]


def test_decide_actions_stale_tick_fresh_watchdog():
    runs = {
        "kaggle-watchdog.yml": {"status": "completed", "age_minutes": 5},
        "ops-tick.yml": {"status": "completed", "age_minutes": 30},
    }
    actions = h.decide_actions(runs, stale_minutes=25)
    assert actions == [{
        "workflow": "ops-tick.yml",
        "reason": "ops-tick stale or missing; re-seed timer",
        "inputs": {"delay_seconds": "0"},
    }]


def test_decide_actions_both_stale_redispatches_both():
    actions = h.decide_actions({}, stale_minutes=25)
    assert [a["workflow"] for a in actions] == [
        "kaggle-watchdog.yml", "ops-tick.yml"]


def test_decide_actions_missing_run_is_stale():
    assert h.decide_actions({}, stale_minutes=25)[0]["workflow"] == "kaggle-watchdog.yml"


def test_decide_actions_disabled():
    runs = {
        "kaggle-watchdog.yml": {"status": "completed", "age_minutes": 999},
        "ops-tick.yml": {"status": "completed", "age_minutes": 999},
    }
    assert h.decide_actions(runs, enabled=False, stale_minutes=25) == []


def test_load_json_missing(tmp_path):
    assert h.load_json(str(tmp_path / "missing.json"), {"a": 1}) == {"a": 1}
