"""Nearby outdoor places from OpenStreetMap via the Overpass API (open data)."""

from __future__ import annotations

import asyncio
import random
import re

import httpx

from .geo import coarsen, haversine_m
from .models import Place

RETRY_STATUS_CODES = {429, 502, 503, 504}
MAX_RETRIES = 2

# Walking assumptions (documented in docs/ARCHITECTURE.md).
DETOUR_FACTOR = 1.3  # streets are longer than straight lines
WALK_M_PER_MIN = 80  # about 4.8 km/h
DEDUPE_RADIUS_M = 300
MAX_PLACES = 25

_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


def build_query(lat: float, lon: float, radius_m: int) -> str:
    around = f"(around:{radius_m},{lat},{lon})"
    return (
        "[out:json][timeout:25];\n"
        "(\n"
        f'  nwr["leisure"~"^(park|garden|nature_reserve)$"]["name"]{around};\n'
        f'  nwr["tourism"="viewpoint"]["name"]{around};\n'
        f'  nwr["natural"~"^(beach|peak)$"]["name"]{around};\n'
        ");\n"
        "out center 80;"
    )


def _category(tags: dict) -> str | None:
    leisure = tags.get("leisure")
    if leisure == "park":
        return "park"
    if leisure == "garden":
        return "garden"
    if leisure == "nature_reserve":
        return "nature"
    if tags.get("tourism") == "viewpoint":
        return "viewpoint"
    natural = tags.get("natural")
    if natural in {"beach", "peak"}:
        return natural
    return None


def _clean_name(name: str) -> str:
    """OSM names are user-contributed text. Treat them as untrusted data."""
    name = _CONTROL.sub(" ", name)
    return " ".join(name.split())[:80]


def walk_minutes(distance_m: float) -> int:
    return max(1, round(distance_m * DETOUR_FACTOR / WALK_M_PER_MIN))


def parse_overpass(payload: dict, lat: float, lon: float) -> list[Place]:
    """Turn an Overpass response into a de-duplicated list, nearest first."""
    found: list[Place] = []
    for element in payload.get("elements", []):
        tags = element.get("tags") or {}
        raw_name = tags.get("name")
        category = _category(tags)
        if not raw_name or not category:
            continue
        name = _clean_name(raw_name)
        if not name:
            continue
        if "lat" in element and "lon" in element:
            p_lat, p_lon = element["lat"], element["lon"]
        elif "center" in element:
            p_lat, p_lon = element["center"]["lat"], element["center"]["lon"]
        else:
            continue
        distance = haversine_m(lat, lon, p_lat, p_lon)
        found.append(
            Place(
                id=f"{element.get('type', 'node')}/{element.get('id', 0)}",
                name=name,
                category=category,
                lat=round(p_lat, 5),
                lon=round(p_lon, 5),
                distance_m=int(distance),
                walk_minutes=walk_minutes(distance),
            )
        )

    found.sort(key=lambda p: p.distance_m)
    kept: list[Place] = []
    for place in found:
        duplicate = any(
            k.name.lower() == place.name.lower()
            and k.category == place.category
            and haversine_m(k.lat, k.lon, place.lat, place.lon) < DEDUPE_RADIUS_M
            for k in kept
        )
        if not duplicate:
            kept.append(place)
        if len(kept) >= MAX_PLACES:
            break
    return kept


async def fetch_places_nominatim(
    client: httpx.AsyncClient, lat: float, lon: float, radius_m: int, decimals: int
) -> list[Place]:
    """Fallback to OpenStreetMap Nominatim when Overpass servers are overloaded."""
    lat_c, lon_c = coarsen(lat, lon, decimals)
    delta = (radius_m / 111_000) * 1.2
    viewbox = f"{lon_c - delta:.4f},{lat_c + delta:.4f},{lon_c + delta:.4f},{lat_c - delta:.4f}"

    queries = ["park", "garden", "nature reserve", "viewpoint", "beach"]
    found: list[Place] = []

    for q in queries:
        try:
            res = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={
                    "q": q,
                    "format": "jsonv2",
                    "limit": 10,
                    "viewbox": viewbox,
                    "bounded": 1,
                },
                headers={"User-Agent": "touch-grass-planner/0.1 (open-source hackathon project)"},
            )
            if res.status_code != 200:
                continue
            for item in res.json():
                raw_name = item.get("name") or (item.get("display_name", "").split(",")[0])
                name = _clean_name(raw_name)
                if not name:
                    continue
                p_lat, p_lon = float(item["lat"]), float(item["lon"])
                distance = haversine_m(lat, lon, p_lat, p_lon)
                cat = "viewpoint" if "view" in q else ("garden" if "garden" in q else ("beach" if "beach" in q else "park"))
                found.append(
                    Place(
                        id=f"node/{item.get('place_id', hash(name))}",
                        name=name,
                        category=cat,
                        lat=round(p_lat, 5),
                        lon=round(p_lon, 5),
                        distance_m=int(distance),
                        walk_minutes=walk_minutes(distance),
                    )
                )
        except Exception:
            continue

    found.sort(key=lambda p: p.distance_m)
    kept: list[Place] = []
    for place in found:
        duplicate = any(
            k.name.lower() == place.name.lower()
            and haversine_m(k.lat, k.lon, place.lat, place.lon) < DEDUPE_RADIUS_M
            for k in kept
        )
        if not duplicate:
            kept.append(place)
        if len(kept) >= MAX_PLACES:
            break
    return kept


async def fetch_places(
    client: httpx.AsyncClient, url: str, lat: float, lon: float, radius_m: int, decimals: int
) -> list[Place]:
    lat_c, lon_c = coarsen(lat, lon, decimals)
    query = build_query(lat_c, lon_c, radius_m)

    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            response = await client.post(url, data={"data": query})
            if response.status_code in RETRY_STATUS_CODES and attempt < MAX_RETRIES:
                delay = 0.5 * (2**attempt) + random.uniform(0.1, 0.3)
                await asyncio.sleep(delay)
                continue
            response.raise_for_status()
            return parse_overpass(response.json(), lat, lon)
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            last_error = exc
            if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code in RETRY_STATUS_CODES and attempt < MAX_RETRIES:
                delay = 0.5 * (2**attempt) + random.uniform(0.1, 0.3)
                await asyncio.sleep(delay)
                continue
            if attempt == MAX_RETRIES:
                # Fallback to OpenStreetMap Nominatim before failing
                try:
                    fallback_places = await fetch_places_nominatim(client, lat, lon, radius_m, decimals)
                    if fallback_places:
                        return fallback_places
                except Exception:
                    pass
                raise exc
            await asyncio.sleep(0.5)
    raise httpx.HTTPError("Max retries exceeded") from last_error
