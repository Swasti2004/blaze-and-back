"""The planning pipeline: location -> weather + places -> filters -> model -> response."""

from __future__ import annotations

import asyncio

import httpx

from .config import Settings
from .fallback import rank_fallback
from .filters import filter_places, stay_minutes
from .geo import geocode
from .llm import LLMError, ask_model, parse_picks
from .models import Pick, Place, SuggestionOut, SuggestRequest, SuggestResponse
from .places import fetch_places
from .prompt import SYSTEM_PROMPT, build_user_prompt
from .store import Store
from .weather import fetch_weather


class ServiceError(Exception):
    """An error that should be shown to the user with a specific HTTP status."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message


async def _resolve_location(
    client: httpx.AsyncClient, settings: Settings, req: SuggestRequest
) -> tuple[float, float, str]:
    # Typed place names win only when no coordinates were sent.
    if req.lat is not None and req.lon is not None:
        return req.lat, req.lon, "your location"
    try:
        return await geocode(client, settings.geocode_url, req.place or "")
    except LookupError as exc:
        raise ServiceError(404, str(exc)) from exc
    except httpx.HTTPError as exc:
        raise ServiceError(502, "Could not look up that place. Check your connection.") from exc


def _to_output(pick: Pick, place: Place) -> SuggestionOut:
    return SuggestionOut(
        place_id=place.id,
        place_name=place.name,
        category=place.category,
        lat=place.lat,
        lon=place.lon,
        walk_minutes=place.walk_minutes,
        distance_m=place.distance_m,
        osm_url=place.osm_url,
        activity=pick.activity,
        reason=pick.reason,
        duration_minutes=pick.duration_minutes,
        effort=pick.effort,
    )


async def suggest(
    client: httpx.AsyncClient, settings: Settings, store: Store, req: SuggestRequest
) -> SuggestResponse:
    lat, lon, label = await _resolve_location(client, settings, req)

    try:
        weather, places = await asyncio.gather(
            fetch_weather(client, settings.weather_url, lat, lon, settings.coord_decimals),
            fetch_places(
                client, settings.overpass_url, lat, lon, settings.search_radius_m,
                settings.coord_decimals,
            ),
        )
    except httpx.HTTPError as exc:
        raise ServiceError(
            502, "Could not reach the weather or places service. Check your connection."
        ) from exc

    result = filter_places(places, weather, req.minutes, req.energy, settings.allow_after_dark)
    if result.blocked_reason:
        return SuggestResponse(
            suggestions=[],
            weather=weather,
            location_label=label,
            engine="none",
            notes=[result.blocked_reason],
        )

    history = store.history()
    by_id = {p.id: p for p in result.candidates}
    allowed = {p.id: stay_minutes(p, req.minutes) for p in result.candidates}
    notes: list[str] = []
    engine = "llm"
    model: str | None = settings.ollama_model

    try:
        prompt = build_user_prompt(
            req.minutes, req.energy, req.interests, weather, result.candidates, history
        )
        raw = await ask_model(client, settings, SYSTEM_PROMPT, prompt)
        picks = parse_picks(raw, allowed)
    except LLMError as exc:
        notes.append(f"{exc} Showing a simple rule-based ranking instead.")
        picks = rank_fallback(
            result.candidates, req.minutes, req.energy, req.interests, history, weather
        )
        engine = "fallback"
        model = None

    return SuggestResponse(
        suggestions=[_to_output(p, by_id[p.place_id]) for p in picks],
        weather=weather,
        location_label=label,
        engine=engine,  # type: ignore[arg-type]
        model=model,
        notes=notes,
    )
