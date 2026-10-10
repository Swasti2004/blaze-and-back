"""Rule-based feasibility filters.

The model never sees places that cannot work: wrong weather, no time, too far
for the energy level. Doing this with plain rules keeps the model's job small
and makes the safety behaviour predictable and testable.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .models import Energy, Place, Weather

MIN_STAY_MIN = 10  # a trip is not worth it if you can only stay a few minutes
MAX_CANDIDATES = 12  # keeps the prompt short for small local models
MAX_ONE_WAY_MIN: dict[str, int] = {"low": 15, "medium": 30, "high": 60}

# Weather thresholds are simple heuristics, not medical or safety guarantees.
RAIN_CHANCE_BLOCK_PCT = 60
RAIN_MM_BLOCK = 0.3
WIND_BLOCK_KMH = 50
COLD_BLOCK_C = -10
HEAT_BLOCK_C = 38


@dataclass
class FilterResult:
    candidates: list[Place] = field(default_factory=list)
    blocked_reason: str | None = None


def stay_minutes(place: Place, minutes: int) -> int:
    """Minutes left at the place after walking there and back."""
    return minutes - 2 * place.walk_minutes


def weather_block_reason(weather: Weather, allow_after_dark: bool) -> str | None:
    if weather.thunderstorm:
        return "Thunderstorms are around, so outdoor suggestions are paused. Try again later."
    if weather.rain_chance_pct >= RAIN_CHANCE_BLOCK_PCT or weather.precipitation_mm >= RAIN_MM_BLOCK:
        return (
            f"Rain looks likely in the next few hours ({weather.rain_chance_pct}% chance). "
            "Try again when it clears."
        )
    if weather.wind_kmh >= WIND_BLOCK_KMH:
        return "It is very windy right now, so outdoor suggestions are paused."
    if weather.feels_like_c <= COLD_BLOCK_C:
        return "It feels extremely cold outside, so outdoor suggestions are paused."
    if weather.feels_like_c >= HEAT_BLOCK_C:
        return "It feels extremely hot outside, so outdoor suggestions are paused."
    if not weather.is_day and not allow_after_dark:
        return "It is dark outside. Suggestions pause after dark by default; try again in daylight."
    return None


def filter_places(
    places: list[Place],
    weather: Weather,
    minutes: int,
    energy: Energy,
    allow_after_dark: bool = False,
) -> FilterResult:
    reason = weather_block_reason(weather, allow_after_dark)
    if reason:
        return FilterResult(blocked_reason=reason)

    max_one_way = MAX_ONE_WAY_MIN[energy]
    keep: list[Place] = []
    for place in places:
        if place.walk_minutes > max_one_way:
            continue
        if stay_minutes(place, minutes) < MIN_STAY_MIN:
            continue
        if energy == "low" and place.category == "peak":
            continue
        keep.append(place)

    keep.sort(key=lambda p: p.walk_minutes)
    keep = keep[:MAX_CANDIDATES]
    if not keep:
        return FilterResult(
            blocked_reason=(
                f"Nothing nearby fits {minutes} minutes at {energy} energy. "
                "Try a longer window or a higher energy level."
            )
        )
    return FilterResult(candidates=keep)
