"""Data shapes shared across the app (request, context, response)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

Energy = Literal["low", "medium", "high"]
Effort = Literal["easy", "moderate", "active"]
Engine = Literal["llm", "fallback", "none"]
FeedbackAction = Literal["accepted", "skipped", "done"]


class SuggestRequest(BaseModel):
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    place: str | None = Field(default=None, max_length=120)
    minutes: int = Field(ge=15, le=240)
    energy: Energy = "medium"
    interests: list[str] = Field(default_factory=list, max_length=8)

    @field_validator("interests")
    @classmethod
    def _clean_interests(cls, value: list[str]) -> list[str]:
        cleaned = []
        for item in value:
            item = " ".join(item.split())[:30].lower()
            if item and item not in cleaned:
                cleaned.append(item)
        return cleaned

    @field_validator("place")
    @classmethod
    def _clean_place(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = " ".join(value.split())
        return value or None

    @model_validator(mode="after")
    def _need_location(self) -> "SuggestRequest":
        has_coords = self.lat is not None and self.lon is not None
        if not has_coords and not self.place:
            raise ValueError("Provide either lat and lon, or a place name.")
        return self


class Weather(BaseModel):
    temperature_c: float
    feels_like_c: float
    precipitation_mm: float
    rain_chance_pct: int  # highest chance over the next few hours
    wind_kmh: float
    is_day: bool
    thunderstorm: bool
    summary: str


class Place(BaseModel):
    id: str
    name: str
    category: str
    lat: float
    lon: float
    distance_m: int
    walk_minutes: int  # one way

    @property
    def osm_url(self) -> str:
        return (
            f"https://www.openstreetmap.org/?mlat={self.lat}&mlon={self.lon}"
            f"#map=17/{self.lat}/{self.lon}"
        )


class Pick(BaseModel):
    """One suggestion chosen by the model (or by the fallback ranking)."""

    place_id: str
    activity: str
    reason: str
    duration_minutes: int
    effort: Effort


class History(BaseModel):
    recent_place_ids: list[str] = Field(default_factory=list)
    recent_load_minutes: int = 0  # minutes of completed outings in the last 24 h
    done_last_7d: int = 0


class SuggestionOut(BaseModel):
    place_id: str
    place_name: str
    category: str
    lat: float
    lon: float
    walk_minutes: int
    distance_m: int
    osm_url: str
    activity: str
    reason: str
    duration_minutes: int
    effort: Effort


class SuggestResponse(BaseModel):
    suggestions: list[SuggestionOut]
    weather: Weather | None = None
    location_label: str
    engine: Engine
    model: str | None = None
    notes: list[str] = Field(default_factory=list)


class FeedbackIn(BaseModel):
    place_id: str = Field(max_length=64)
    place_name: str = Field(max_length=120)
    category: str = Field(max_length=32)
    action: FeedbackAction
    effort: Effort | None = None
    duration_minutes: int | None = Field(default=None, ge=0, le=600)
