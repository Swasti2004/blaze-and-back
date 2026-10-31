"""Runtime settings, read from environment variables.

Everything has a sensible default so the app runs with no configuration
other than having Ollama running locally, or with cloud keys (Gemini, Groq, OpenAI),
or using the fast smart AI engine.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    # Local model (Ollama).
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "gemma4"
    ollama_timeout_s: float = 120.0

    # Fast Cloud AI Providers (Gemini, Groq, OpenAI)
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"

    # Open data sources.
    overpass_url: str = "https://overpass-api.de/api/interpreter"
    weather_url: str = "https://api.open-meteo.com/v1/forecast"
    geocode_url: str = "https://geocoding-api.open-meteo.com/v1/search"

    # Local storage for accept / skip / done feedback.
    db_path: str = "data/touchgrass.db"

    # Behaviour.
    search_radius_m: int = 3000
    coord_decimals: int = 3  # 3 decimals is roughly 110 m of precision
    allow_after_dark: bool = False

    user_agent: str = "touch-grass-planner/0.1 (open-source hackathon project)"

    @classmethod
    def from_env(cls) -> "Settings":
        d = cls()
        default_db = "/tmp/touchgrass.db" if os.getenv("VERCEL") else d.db_path
        return cls(
            ollama_url=os.getenv("OLLAMA_URL", d.ollama_url).rstrip("/"),
            ollama_model=os.getenv("OLLAMA_MODEL", d.ollama_model),
            ollama_timeout_s=float(os.getenv("OLLAMA_TIMEOUT_S", d.ollama_timeout_s)),
            gemini_api_key=os.getenv("GEMINI_API_KEY"),
            gemini_model=os.getenv("GEMINI_MODEL", d.gemini_model),
            groq_api_key=os.getenv("GROQ_API_KEY"),
            groq_model=os.getenv("GROQ_MODEL", d.groq_model),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_model=os.getenv("OPENAI_MODEL", d.openai_model),
            overpass_url=os.getenv("OVERPASS_URL", d.overpass_url),
            weather_url=os.getenv("WEATHER_URL", d.weather_url),
            geocode_url=os.getenv("GEOCODE_URL", d.geocode_url),
            db_path=os.getenv("TG_DB_PATH", default_db),
            search_radius_m=int(os.getenv("TG_SEARCH_RADIUS_M", d.search_radius_m)),
            coord_decimals=int(os.getenv("TG_COORD_DECIMALS", d.coord_decimals)),
            allow_after_dark=_env_bool("TG_ALLOW_AFTER_DARK", d.allow_after_dark),
        )
