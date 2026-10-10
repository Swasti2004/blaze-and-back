"""Shared fixtures: realistic sample payloads and a fake network for all outside services."""

from __future__ import annotations

import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

WEATHER_OK = {
    "current": {
        "temperature_2m": 18.4,
        "apparent_temperature": 17.0,
        "is_day": 1,
        "precipitation": 0.0,
        "weather_code": 2,
        "wind_speed_10m": 9.5,
    },
    "hourly": {"precipitation_probability": [5, 10, 15]},
}

OVERPASS = {
    "elements": [
        {"type": "way", "id": 11, "center": {"lat": 51.5010, "lon": -0.1250},
         "tags": {"leisure": "park", "name": "Riverside Park"}},
        {"type": "node", "id": 12, "lat": 51.5040, "lon": -0.1270,
         "tags": {"tourism": "viewpoint", "name": "Hilltop Lookout"}},
        {"type": "way", "id": 13, "center": {"lat": 51.5100, "lon": -0.1300},
         "tags": {"leisure": "garden", "name": "Quiet Garden"}},
        {"type": "node", "id": 14, "lat": 51.5300, "lon": -0.1500,
         "tags": {"natural": "peak", "name": "Far Peak"}},
        {"type": "node", "id": 15, "lat": 51.5011, "lon": -0.1251,
         "tags": {"leisure": "park"}},  # unnamed, must be skipped
    ]
}

GEOCODE = {"results": [{"name": "Testville", "admin1": "Testshire", "country": "Testland",
                        "latitude": 51.5, "longitude": -0.125}]}


def llm_reply(picks: list[dict]) -> dict:
    return {"message": {"role": "assistant", "content": json.dumps({"suggestions": picks})}}


class FakeNetwork:
    """Routes outgoing requests by host and records what was sent."""

    def __init__(self) -> None:
        self.weather = WEATHER_OK
        self.overpass = OVERPASS
        self.ollama_reply = llm_reply([
            {"place_id": "way/11", "activity": "Walk a loop by the river",
             "reason": "Mild weather and a short walk fit your 60 minutes.",
             "duration_minutes": 30, "effort": "easy"},
        ])
        self.ollama_status = 200
        self.ollama_models = ["gemma4:latest"]
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        host, path = request.url.host, request.url.path
        if host == "api.open-meteo.com":
            return httpx.Response(200, json=self.weather)
        if host == "geocoding-api.open-meteo.com":
            return httpx.Response(200, json=GEOCODE)
        if host == "overpass-api.de":
            return httpx.Response(200, json=self.overpass)
        if host == "localhost" and path == "/api/chat":
            if self.ollama_status != 200:
                return httpx.Response(self.ollama_status, json={"error": "boom"})
            return httpx.Response(200, json=self.ollama_reply)
        if host == "localhost" and path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": n} for n in self.ollama_models]})
        return httpx.Response(404, json={"error": f"unexpected {host}{path}"})


@pytest.fixture
def net() -> FakeNetwork:
    return FakeNetwork()


@pytest.fixture
def client(net, tmp_path):
    settings = Settings(db_path=str(tmp_path / "test.db"))
    app = create_app(settings, transport=httpx.MockTransport(net))
    with TestClient(app) as test_client:
        yield test_client
