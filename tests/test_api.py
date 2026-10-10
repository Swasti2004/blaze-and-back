"""End-to-end tests through the real FastAPI app with every outside service faked."""

from __future__ import annotations

import httpx

from tests.conftest import WEATHER_OK, llm_reply

BODY = {"lat": 51.5, "lon": -0.125, "minutes": 60, "energy": "medium", "interests": ["quiet"]}


def test_happy_path_uses_model(client, net):
    response = client.post("/api/suggest", json=BODY)
    assert response.status_code == 200
    data = response.json()
    assert data["engine"] == "llm" and data["model"] == "gemma4"
    assert data["suggestions"][0]["place_name"] == "Riverside Park"
    assert data["weather"]["summary"] == "partly cloudy"


def test_coordinates_are_rounded_before_leaving_the_machine(client, net):
    client.post("/api/suggest", json={**BODY, "lat": 51.5012345, "lon": -0.1254321})
    outside = [r for r in net.requests if r.url.host in {"api.open-meteo.com", "overpass-api.de"}]
    assert outside, "expected calls to the open data services"
    for request in outside:
        text = str(request.url) + request.content.decode()
        assert "51.5012345" not in text and "-0.1254321" not in text
    assert any("51.501" in str(r.url) for r in outside if r.url.host == "api.open-meteo.com")


def test_prompt_never_leaves_localhost(client, net):
    client.post("/api/suggest", json=BODY)
    chats = [r for r in net.requests if r.url.path == "/api/chat"]
    assert chats and all(r.url.host == "localhost" for r in chats)
    assert not any(r.url.host not in {"localhost", "api.open-meteo.com", "overpass-api.de"}
                   for r in net.requests)


def test_model_failure_falls_back(client, net):
    net.ollama_status = 500
    data = client.post("/api/suggest", json=BODY).json()
    assert data["engine"] == "fallback" and data["model"] is None
    assert data["suggestions"] and "rule-based" in data["notes"][0]


def test_invented_place_falls_back(client, net):
    net.ollama_reply = llm_reply([{"place_id": "way/9999", "activity": "Go", "reason": "Nice.",
                                   "duration_minutes": 20, "effort": "easy"}])
    assert client.post("/api/suggest", json=BODY).json()["engine"] == "fallback"


def test_bad_weather_pauses_suggestions(client, net):
    net.weather = {**WEATHER_OK, "hourly": {"precipitation_probability": [80, 90, 90]}}
    data = client.post("/api/suggest", json=BODY).json()
    assert data["engine"] == "none" and data["suggestions"] == []
    assert "Rain" in data["notes"][0]
    assert not any(r.url.path == "/api/chat" for r in net.requests)  # model not even called


def test_place_name_is_geocoded(client, net):
    data = client.post("/api/suggest", json={"place": "Testville", "minutes": 60}).json()
    assert data["location_label"] == "Testville, Testshire, Testland"


def test_validation_errors(client):
    assert client.post("/api/suggest", json={"minutes": 60}).status_code == 422
    assert client.post("/api/suggest", json={**BODY, "minutes": 5}).status_code == 422


def test_feedback_changes_next_prompt_history(client, net):
    first = client.post("/api/suggest", json=BODY).json()["suggestions"][0]
    fb = {"place_id": first["place_id"], "place_name": first["place_name"],
          "category": first["category"], "action": "done", "effort": "easy", "duration_minutes": 30}
    assert client.post("/api/feedback", json=fb).status_code == 204
    net.requests.clear()
    client.post("/api/suggest", json=BODY)
    prompt = next(r for r in net.requests if r.url.path == "/api/chat").content.decode()
    assert "way/11" in prompt and "completed_minutes_last_24h" in prompt and "30" in prompt


def test_feedback_validation(client):
    assert client.post("/api/feedback", json={"place_id": "x", "place_name": "x",
                                               "category": "park", "action": "nope"}).status_code == 422


def test_health_reports_model(client, net):
    assert client.get("/api/health").json() == {
        "ollama": True, "model": "gemma4", "model_available": True}
    net.ollama_models = ["llama3:8b"]
    assert client.get("/api/health").json()["model_available"] is False


def test_static_front_end_is_served(client):
    assert client.get("/").status_code == 200


def test_outside_lookups_are_cached_for_ten_minutes(client, net):
    # First call: outside requests are made
    res1 = client.post("/api/suggest", json=BODY)
    assert res1.status_code == 200
    outside_first = [r for r in net.requests if r.url.host in {"api.open-meteo.com", "overpass-api.de"}]
    assert len(outside_first) == 2

    # Second identical call: outside services must not be called again
    net.requests.clear()
    res2 = client.post("/api/suggest", json=BODY)
    assert res2.status_code == 200
    outside_second = [r for r in net.requests if r.url.host in {"api.open-meteo.com", "overpass-api.de"}]
    assert len(outside_second) == 0


def test_overpass_retries_politely_on_429(monkeypatch):
    import asyncio
    import app.places
    from tests.conftest import OVERPASS

    # Speed up sleep in tests
    sleep_calls = []
    async def fake_sleep(d):
        sleep_calls.append(d)
    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    attempts = 0
    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(429, json={"error": "rate limited"})
        return httpx.Response(200, json=OVERPASS)

    transport = httpx.MockTransport(handler)
    async def run():
        async with httpx.AsyncClient(transport=transport) as client:
            return await app.places.fetch_places(client, "http://overpass/api", 51.5, -0.125, 3000, 3)

    places = asyncio.run(run())
    assert len(places) > 0
    assert attempts == 2
    assert len(sleep_calls) == 1


def test_overpass_always_failing_gives_friendly_service_error(client, net):
    # Simulate Overpass failing permanently with 504 Gateway Timeout
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "overpass-api.de":
            return httpx.Response(504, json={"error": "gateway timeout"})
        return net(request)

    # Use a location not cached yet
    body = {**BODY, "lat": 48.8566, "lon": 2.3522}
    # Temporarily monkeypatch client transport
    old_transport = client.app.state.client._transport
    client.app.state.client._transport = httpx.MockTransport(handler)
    try:
        res = client.post("/api/suggest", json=body)
        assert res.status_code == 502
        assert "Could not reach the weather or places service" in res.json()["detail"]
    finally:
        client.app.state.client._transport = old_transport


def test_history_api_endpoints_and_clearing_removes_from_prompt(client, net):
    # Initially empty history
    assert client.get("/api/history").json() == {"events": []}

    # Add feedback
    fb = {"place_id": "way/11", "place_name": "Riverside Park", "category": "park", "action": "done",
          "effort": "easy", "duration_minutes": 25}
    client.post("/api/feedback", json=fb)

    hist = client.get("/api/history").json()["events"]
    assert len(hist) == 1
    assert hist[0]["place_name"] == "Riverside Park"

    # Make suggest request: prompt should include 25 in completed_minutes_last_24h
    net.requests.clear()
    if hasattr(client.app.state, "weather_cache") and client.app.state.weather_cache:
        client.app.state.weather_cache.clear()
    if hasattr(client.app.state, "places_cache") and client.app.state.places_cache:
        client.app.state.places_cache.clear()
    client.post("/api/suggest", json=BODY)
    prompt = next(r for r in net.requests if r.url.path == "/api/chat").content.decode()
    assert '"completed_minutes_last_24h": 25' in prompt or '\\"completed_minutes_last_24h\\": 25' in prompt

    # Clear history
    del_res = client.delete("/api/history")
    assert del_res.status_code == 204
    assert client.get("/api/history").json() == {"events": []}

    # Next suggest request should have 0 in completed_minutes_last_24h
    net.requests.clear()
    if hasattr(client.app.state, "weather_cache") and client.app.state.weather_cache:
        client.app.state.weather_cache.clear()
    if hasattr(client.app.state, "places_cache") and client.app.state.places_cache:
        client.app.state.places_cache.clear()
    client.post("/api/suggest", json=BODY)
    prompt_after = next(r for r in net.requests if r.url.path == "/api/chat").content.decode()
    assert '"completed_minutes_last_24h": 0' in prompt_after or '\\"completed_minutes_last_24h\\": 0' in prompt_after


