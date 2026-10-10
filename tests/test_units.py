"""Unit tests for the pure logic: geo, weather, places, filters, fallback, prompt."""

from __future__ import annotations

import pytest

from app.fallback import effort_for, rank_fallback
from app.filters import filter_places, stay_minutes, weather_block_reason
from app.geo import coarsen, haversine_m
from app.models import History, Place, SuggestRequest, Weather
from app.places import parse_overpass, walk_minutes
from app.prompt import build_user_prompt
from app.weather import describe_code, parse_weather
from tests.conftest import OVERPASS, WEATHER_OK


def make_weather(**over) -> Weather:
    base = dict(temperature_c=18, feels_like_c=17, precipitation_mm=0, rain_chance_pct=5,
                wind_kmh=8, is_day=True, thunderstorm=False, summary="partly cloudy")
    base.update(over)
    return Weather(**base)


def make_place(pid="way/1", name="Test Park", category="park", walk=8) -> Place:
    return Place(id=pid, name=name, category=category, lat=51.5, lon=-0.12,
                 distance_m=walk * 60, walk_minutes=walk)


# ---------- geo ----------
def test_haversine_zero_and_one_degree():
    assert haversine_m(10, 10, 10, 10) == 0
    assert haversine_m(0, 0, 1, 0) == pytest.approx(111_195, rel=0.01)


def test_coarsen_rounds():
    assert coarsen(51.50123, -0.12987, 3) == (51.501, -0.13)


# ---------- weather ----------
def test_parse_weather_takes_max_rain_chance():
    w = parse_weather(WEATHER_OK)
    assert w.rain_chance_pct == 15
    assert w.summary == "partly cloudy"
    assert w.is_day and not w.thunderstorm


def test_parse_weather_handles_missing_hourly_and_thunder():
    payload = {"current": {"temperature_2m": 10, "weather_code": 95}}
    w = parse_weather(payload)
    assert w.thunderstorm and w.rain_chance_pct == 0
    assert describe_code(12345) == "mixed conditions"


# ---------- places ----------
def test_parse_overpass_skips_unnamed_and_sorts_nearest_first():
    places = parse_overpass(OVERPASS, 51.5, -0.125)
    names = [p.name for p in places]
    assert "Riverside Park" in names and len(names) == 4
    assert names == sorted(names, key=lambda n: next(p.distance_m for p in places if p.name == n))


def test_parse_overpass_dedupes_same_name_nearby():
    payload = {"elements": [
        {"type": "way", "id": 1, "center": {"lat": 51.5, "lon": -0.12},
         "tags": {"leisure": "park", "name": "Same Park"}},
        {"type": "way", "id": 2, "center": {"lat": 51.5003, "lon": -0.12},
         "tags": {"leisure": "park", "name": "same park"}},
    ]}
    assert len(parse_overpass(payload, 51.5, -0.12)) == 1


def test_names_are_sanitised():
    payload = {"elements": [{"type": "node", "id": 1, "lat": 51.5, "lon": -0.12,
                             "tags": {"leisure": "park", "name": "Nice\nPark\x00" + "x" * 200}}]}
    name = parse_overpass(payload, 51.5, -0.12)[0].name
    assert "\n" not in name and "\x00" not in name and len(name) <= 80


def test_walk_minutes_never_zero():
    assert walk_minutes(0) == 1
    assert walk_minutes(800) == 13


# ---------- filters ----------
def test_weather_blocks():
    assert "Thunderstorms" in weather_block_reason(make_weather(thunderstorm=True), False)
    assert "Rain" in weather_block_reason(make_weather(rain_chance_pct=70), False)
    assert "windy" in weather_block_reason(make_weather(wind_kmh=60), False)
    assert "dark" in weather_block_reason(make_weather(is_day=False), False)
    assert weather_block_reason(make_weather(is_day=False), True) is None
    assert weather_block_reason(make_weather(), False) is None


def test_time_budget_counts_round_trip():
    near, far = make_place("a", walk=10), make_place("b", walk=25)
    res = filter_places([near, far], make_weather(), minutes=45, energy="high")
    assert [p.id for p in res.candidates] == ["a"]  # far: 50 min round trip, no time to stay
    assert stay_minutes(near, 45) == 25


def test_low_energy_limits_distance_and_excludes_peaks():
    places = [make_place("a", walk=10), make_place("b", walk=20), make_place("c", category="peak", walk=5)]
    res = filter_places(places, make_weather(), minutes=120, energy="low")
    assert [p.id for p in res.candidates] == ["a"]


def test_nothing_fits_gives_helpful_reason():
    res = filter_places([make_place(walk=30)], make_weather(), minutes=30, energy="medium")
    assert res.candidates == [] and "Nothing nearby" in res.blocked_reason


# ---------- fallback ----------
def test_fallback_prefers_closer_and_matching_interest():
    near, far_view = make_place("near", walk=5), make_place("view", category="viewpoint", walk=9)
    picks = rank_fallback([near, far_view], 90, "medium", ["views"], History(), make_weather())
    assert picks[0].place_id == "view"  # interest bonus beats 4 extra minutes of walking


def test_fallback_avoids_recent_and_tired_high_effort():
    a, b = make_place("a", walk=5), make_place("b", walk=6)
    history = History(recent_place_ids=["a"])
    assert rank_fallback([a, b], 90, "medium", [], history, make_weather())[0].place_id == "b"

    peak, park = make_place("p", category="peak", walk=5), make_place("q", walk=8)
    tired = History(recent_load_minutes=120)
    assert rank_fallback([peak, park], 90, "high", [], tired, make_weather())[0].place_id == "q"


def test_effort_bumps_with_long_walk():
    assert effort_for(make_place(category="park", walk=10)) == "easy"
    assert effort_for(make_place(category="park", walk=25)) == "moderate"
    assert effort_for(make_place(category="peak", walk=5)) == "active"


# ---------- prompt / request ----------
def test_prompt_contains_only_candidate_data():
    prompt = build_user_prompt(60, "medium", ["quiet"], make_weather(), [make_place()], History())
    assert '"stay_minutes_available": 44' in prompt and "way/1" in prompt


def test_request_needs_a_location():
    with pytest.raises(ValueError):
        SuggestRequest(minutes=30)
    assert SuggestRequest(minutes=30, place="  Oslo ").place == "Oslo"
    assert SuggestRequest(minutes=30, lat=1, lon=2, interests=["Quiet ", "quiet", ""]).interests == ["quiet"]
