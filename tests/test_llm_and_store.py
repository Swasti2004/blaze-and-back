"""Tests for validating model output and for the local feedback store."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from app.llm import LLMError, parse_picks
from app.store import Store

ALLOWED = {"way/1": 40, "way/2": 20}


def reply(items):
    return json.dumps({"suggestions": items})


def good(pid="way/1", duration=30):
    return {"place_id": pid, "activity": "Walk a loop", "reason": "Mild and close.",
            "duration_minutes": duration, "effort": "easy"}


def test_valid_reply_is_accepted():
    picks = parse_picks(reply([good()]), ALLOWED)
    assert len(picks) == 1 and picks[0].duration_minutes == 30


def test_code_fences_and_surrounding_text_are_tolerated():
    fenced = "```json\n" + reply([good()]) + "\n```"
    assert len(parse_picks(fenced, ALLOWED)) == 1
    chatty = "Sure! Here you go: " + reply([good()]) + " Enjoy."
    assert len(parse_picks(chatty, ALLOWED)) == 1


def test_invented_ids_and_duplicates_are_dropped():
    picks = parse_picks(reply([good("way/999"), good("way/1"), good("way/1")]), ALLOWED)
    assert [p.place_id for p in picks] == ["way/1"]


def test_duration_is_clamped_to_time_available():
    picks = parse_picks(reply([good("way/2", duration=500), good("way/1", duration=1)]), ALLOWED)
    assert picks[0].duration_minutes == 20 and picks[1].duration_minutes == 5


def test_bad_fields_are_dropped_not_crashed_on():
    bad_effort = {**good(), "effort": "extreme"}
    weird = {**good("way/2"), "duration_minutes": "soon"}
    unhashable = {**good(), "place_id": ["x"]}
    with pytest.raises(LLMError):
        parse_picks(reply([bad_effort, weird, unhashable, "text", 5]), ALLOWED)


@pytest.mark.parametrize("raw", ["", "not json at all", "[1, 2]", '{"suggestions": "nope"}', "{bad"])
def test_unusable_replies_raise(raw):
    with pytest.raises(LLMError):
        parse_picks(raw, ALLOWED)


def test_store_history_windows(tmp_path):
    store = Store(str(tmp_path / "s.db"))
    now = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)
    store.record(place_id="a", place_name="A", category="park", action="done",
                 effort="easy", duration_minutes=40, now=now - timedelta(hours=3))
    store.record(place_id="b", place_name="B", category="park", action="accepted",
                 now=now - timedelta(days=2))
    store.record(place_id="c", place_name="C", category="park", action="done",
                 duration_minutes=30, now=now - timedelta(days=5))
    store.record(place_id="d", place_name="D", category="park", action="skipped", now=now)
    history = store.history(now=now)
    assert set(history.recent_place_ids) == {"a", "b"}  # skipped and old ones excluded
    assert history.recent_load_minutes == 40
    assert history.done_last_7d == 2


def test_store_rejects_unknown_action(tmp_path):
    store = Store(str(tmp_path / "s.db"))
    with pytest.raises(Exception):
        store.record(place_id="a", place_name="A", category="park", action="exploded")


def test_store_list_recent_and_clear(tmp_path):
    store = Store(str(tmp_path / "s.db"))
    assert store.list_recent() == []
    store.record(place_id="p1", place_name="Park 1", category="park", action="accepted")
    store.record(place_id="p2", place_name="Park 2", category="garden", action="done", duration_minutes=25)
    recent = store.list_recent(limit=10)
    assert len(recent) == 2
    assert recent[0]["place_name"] == "Park 2"  # most recent first
    assert recent[1]["place_name"] == "Park 1"

    store.clear()
    assert store.list_recent() == []

