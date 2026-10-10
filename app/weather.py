"""Current weather and short-term rain chance from Open-Meteo (open data, no API key)."""

from __future__ import annotations

import httpx

from .geo import coarsen
from .models import Weather

HORIZON_HOURS = 3

# WMO weather interpretation codes used by Open-Meteo.
_WMO = {
    0: "clear sky",
    1: "mostly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "freezing fog",
    51: "light drizzle",
    53: "drizzle",
    55: "heavy drizzle",
    56: "freezing drizzle",
    57: "heavy freezing drizzle",
    61: "light rain",
    63: "rain",
    65: "heavy rain",
    66: "freezing rain",
    67: "heavy freezing rain",
    71: "light snow",
    73: "snow",
    75: "heavy snow",
    77: "snow grains",
    80: "light rain showers",
    81: "rain showers",
    82: "heavy rain showers",
    85: "snow showers",
    86: "heavy snow showers",
    95: "thunderstorm",
    96: "thunderstorm with hail",
    99: "thunderstorm with heavy hail",
}
_THUNDER = {95, 96, 99}


def describe_code(code: int) -> str:
    return _WMO.get(code, "mixed conditions")


def parse_weather(payload: dict, horizon_hours: int = HORIZON_HOURS) -> Weather:
    """Turn an Open-Meteo response into the small Weather record the app uses."""
    current = payload["current"]
    probabilities = (payload.get("hourly") or {}).get("precipitation_probability") or []
    window = [p for p in probabilities[:horizon_hours] if p is not None]
    code = int(current.get("weather_code", -1))
    return Weather(
        temperature_c=float(current["temperature_2m"]),
        feels_like_c=float(current.get("apparent_temperature", current["temperature_2m"])),
        precipitation_mm=float(current.get("precipitation", 0.0)),
        rain_chance_pct=int(max(window)) if window else 0,
        wind_kmh=float(current.get("wind_speed_10m", 0.0)),
        is_day=bool(current.get("is_day", 1)),
        thunderstorm=code in _THUNDER,
        summary=describe_code(code),
    )


async def fetch_weather(
    client: httpx.AsyncClient, url: str, lat: float, lon: float, decimals: int
) -> Weather:
    lat_c, lon_c = coarsen(lat, lon, decimals)
    response = await client.get(
        url,
        params={
            "latitude": lat_c,
            "longitude": lon_c,
            "current": "temperature_2m,apparent_temperature,is_day,precipitation,"
            "weather_code,wind_speed_10m",
            "hourly": "precipitation_probability",
            "forecast_hours": HORIZON_HOURS,
            "timezone": "auto",
        },
    )
    response.raise_for_status()
    return parse_weather(response.json())
