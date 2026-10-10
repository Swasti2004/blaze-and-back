"""Deterministic ranking used when the local model is unavailable or misbehaves.

This keeps the app useful with no model running, and it gives the model's
output something simple to be compared against.
"""

from __future__ import annotations

from .filters import stay_minutes
from .models import Effort, Energy, History, Pick, Place, Weather

_ACTIVITY = {
    "park": "Walk a loop and sit somewhere green",
    "garden": "Take a slow stroll through the garden",
    "nature": "Walk the paths of the reserve at an easy pace",
    "viewpoint": "Walk up to the viewpoint and take in the view",
    "peak": "Climb to the top and come back down",
    "beach": "Walk along the shore",
}

# Interest word -> categories it points to. Unknown words fall back to a name match.
_INTEREST_CATEGORIES = {
    "quiet": {"garden", "nature"},
    "water": {"beach"},
    "views": {"viewpoint", "peak"},
    "greenery": {"park", "garden", "nature"},
    "exercise": {"peak", "nature", "park"},
    "photography": {"viewpoint", "garden", "beach"},
}
_WATER_WORDS = ("river", "lake", "pond", "canal", "creek", "waterfront", "beach")

_EFFORT_ORDER: list[Effort] = ["easy", "moderate", "active"]

MIN_DURATION = 10
MAX_DURATION = 40


def effort_for(place: Place) -> Effort:
    base = {"peak": "active", "nature": "moderate"}.get(place.category, "easy")
    index = _EFFORT_ORDER.index(base)  # type: ignore[arg-type]
    if place.walk_minutes > 20:
        index = min(index + 1, 2)
    return _EFFORT_ORDER[index]


def _interest_hits(place: Place, interests: list[str]) -> list[str]:
    name = place.name.lower()
    hits = []
    for interest in interests:
        categories = _INTEREST_CATEGORIES.get(interest, set())
        by_category = place.category in categories
        by_name = interest in name or (
            interest == "water" and any(word in name for word in _WATER_WORDS)
        )
        if by_category or by_name:
            hits.append(interest)
    return hits


def _score(place: Place, energy: Energy, interests: list[str], history: History) -> float:
    effort = effort_for(place)
    score = -float(place.walk_minutes)
    score += 6 * min(len(_interest_hits(place, interests)), 2)
    if place.id in history.recent_place_ids:
        score -= 10
    if energy == "low":
        score += {"easy": 4, "moderate": 0, "active": -4}[effort]
    if history.recent_load_minutes >= 90:
        score += {"easy": 2, "moderate": -2, "active": -6}[effort]
    return score


def rank_fallback(
    candidates: list[Place],
    minutes: int,
    energy: Energy,
    interests: list[str],
    history: History,
    weather: Weather,
    limit: int = 3,
) -> list[Pick]:
    ranked = sorted(
        candidates,
        key=lambda p: _score(p, energy, interests, history),
        reverse=True,
    )[:limit]
    picks = []
    for place in ranked:
        stay = stay_minutes(place, minutes)
        hits = _interest_hits(place, interests)
        reason = (
            f"{place.walk_minutes} minute walk, {weather.summary} outside, "
            f"and it fits your {minutes} minutes."
        )
        if hits:
            reason += f" Matches your interest in {hits[0]}."
        picks.append(
            Pick(
                place_id=place.id,
                activity=_ACTIVITY.get(place.category, "Take a walk and enjoy being outside"),
                reason=reason,
                duration_minutes=max(MIN_DURATION, min(stay, MAX_DURATION)),
                effort=effort_for(place),
            )
        )
    return picks

