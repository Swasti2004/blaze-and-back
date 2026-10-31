"""Nearby outdoor places from OpenStreetMap via Overpass API and Nominatim (open data)."""

from __future__ import annotations

import asyncio
import re

import httpx

from .geo import coarsen, haversine_m
from .models import Place

# Walking assumptions (documented in docs/ARCHITECTURE.md).
DETOUR_FACTOR = 1.3  # streets are longer than straight lines
WALK_M_PER_MIN = 80  # about 4.8 km/h
DEDUPE_RADIUS_M = 300
MAX_PLACES = 40

_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


def build_query(lat: float, lon: float, radius_m: int) -> str:
    around = f"(around:{radius_m},{lat},{lon})"
    return (
        "[out:json][timeout:5];\n"
        "(\n"
        f'  nwr["leisure"~"^(park|garden|nature_reserve|recreation_ground|common|pitch)$"]["name"]{around};\n'
        f'  nwr["tourism"~"^(viewpoint|attraction)$"]["name"]{around};\n'
        f'  nwr["natural"~"^(beach|peak|wood|water)$"]["name"]{around};\n'
        f'  nwr["landuse"~"^(village_green|forest|meadow)$"]["name"]{around};\n'
        ");\n"
        "out center 80;"
    )


def _category(tags: dict) -> str | None:
    leisure = tags.get("leisure")
    if leisure in {"park", "recreation_ground", "common", "pitch"}:
        return "park"
    if leisure == "garden":
        return "garden"
    if leisure == "nature_reserve":
        return "nature"

    landuse = tags.get("landuse")
    if landuse in {"village_green", "grass", "recreation_ground"}:
        return "park"
    if landuse in {"forest", "meadow"}:
        return "nature"

    natural = tags.get("natural")
    if natural in {"beach", "peak"}:
        return natural
    if natural in {"wood", "scrub"}:
        return "nature"
    if natural == "water":
        return "beach"

    tourism = tags.get("tourism")
    if tourism == "viewpoint":
        return "viewpoint"
    if tourism == "attraction":
        return "park"

    boundary = tags.get("boundary")
    if boundary in {"national_park", "protected_area"}:
        return "nature"

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
    """Fast concurrent fallback to OpenStreetMap Nominatim."""
    lat_c, lon_c = coarsen(lat, lon, decimals)
    delta = (radius_m / 111_000) * 1.3
    viewbox = f"{lon_c - delta:.4f},{lat_c + delta:.4f},{lon_c + delta:.4f},{lat_c - delta:.4f}"

    categories_to_query = [
        ("park", "park"),
        ("garden", "garden"),
        ("nature reserve", "nature"),
        ("viewpoint", "viewpoint"),
        ("beach", "beach"),
        ("forest", "nature"),
        ("lake", "beach"),
        ("recreation ground", "park"),
    ]

    async def search_query(query_str: str, cat: str):
        try:
            res = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={
                    "q": query_str,
                    "format": "jsonv2",
                    "limit": 10,
                    "viewbox": viewbox,
                    "bounded": 1,
                },
                headers={"User-Agent": "touch-grass-planner/0.1 (open-source PWA)"},
                timeout=3.5,
            )
            if res.status_code == 200:
                return res.json(), cat
        except Exception:
            pass
        return [], cat

    tasks = [search_query(q, cat) for q, cat in categories_to_query]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    found: list[Place] = []
    for res_item in results:
        if isinstance(res_item, tuple):
            items, cat = res_item
            for item in items:
                raw_name = item.get("name") or (item.get("display_name", "").split(",")[0])
                name = _clean_name(raw_name)
                if not name:
                    continue
                try:
                    p_lat, p_lon = float(item["lat"]), float(item["lon"])
                except (KeyError, ValueError):
                    continue
                distance = haversine_m(lat, lon, p_lat, p_lon)
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

    async def try_overpass():
        try:
            response = await client.post(url, data={"data": query}, timeout=3.5)
            if response.status_code in {429, 502, 503, 504}:
                await asyncio.sleep(0.3)
                response = await client.post(url, data={"data": query}, timeout=3.5)
            response.raise_for_status()
            places = parse_overpass(response.json(), lat, lon)
            if places:
                return places
        except Exception:
            pass
        return None

    async def try_nominatim():
        try:
            places = await fetch_places_nominatim(client, lat, lon, radius_m, decimals)
            if places:
                return places
        except Exception:
            pass
        return None

    # Race Overpass and Nominatim concurrently to ensure lightning response
    t_overpass = asyncio.create_task(try_overpass())
    t_nominatim = asyncio.create_task(try_nominatim())

    done, pending = await asyncio.wait([t_overpass, t_nominatim], return_when=asyncio.FIRST_COMPLETED)

    for task in done:
        res = task.result()
        if res:
            for p in pending:
                p.cancel()
            return res

    # Wait for the pending one if the first failed
    for task in pending:
        try:
            res = await task
            if res:
                return res
        except Exception:
            pass

    return []
