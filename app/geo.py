"""Small geography helpers: distance, coordinate coarsening, place-name lookup."""

from __future__ import annotations

import math

import httpx

EARTH_RADIUS_M = 6_371_000


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = p2 - p1
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def coarsen(lat: float, lon: float, decimals: int) -> tuple[float, float]:
    """Round coordinates before they are sent to any outside service."""
    return round(lat, decimals), round(lon, decimals)


async def geocode(client: httpx.AsyncClient, url: str, name: str) -> tuple[float, float, str]:
    """Turn a town or city name into coordinates using Open-Meteo's geocoder."""
    response = await client.get(
        url, params={"name": name, "count": 1, "language": "en", "format": "json"}
    )
    response.raise_for_status()
    results = response.json().get("results") or []
    if not results:
        raise LookupError(f"Could not find a place called '{name}'.")
    top = results[0]
    parts = [top.get("name"), top.get("admin1"), top.get("country")]
    label = ", ".join(p for p in parts if p)
    return float(top["latitude"]), float(top["longitude"]), label
