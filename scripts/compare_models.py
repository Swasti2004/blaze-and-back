"""Compare local models on the same fixed planning scenarios.

Usage:
    python scripts/compare_models.py gemma4 <another-model> --runs 3

Prints a Markdown table (valid-reply rate and median latency per model) that you
can paste into your write-up. Run it on your own machine: the numbers depend on
your hardware, and only numbers you measured should go in the post.

The scenarios use made-up places, so no network is needed except Ollama itself.
"""

from __future__ import annotations

import argparse
import asyncio
import statistics
import sys
import time
from dataclasses import replace
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import Settings  # noqa: E402
from app.filters import stay_minutes  # noqa: E402
from app.llm import LLMError, ask_model, parse_picks  # noqa: E402
from app.models import History, Place, Weather  # noqa: E402
from app.prompt import SYSTEM_PROMPT, build_user_prompt  # noqa: E402

PLACES = [
    Place(id="way/1", name="Riverside Park", category="park", lat=0, lon=0, distance_m=500, walk_minutes=8),
    Place(id="node/2", name="Hilltop Lookout", category="viewpoint", lat=0, lon=0, distance_m=900, walk_minutes=15),
    Place(id="way/3", name="Quiet Garden", category="garden", lat=0, lon=0, distance_m=300, walk_minutes=5),
    Place(id="node/4", name="Lakeside Beach", category="beach", lat=0, lon=0, distance_m=1300, walk_minutes=21),
]

MILD = Weather(temperature_c=18, feels_like_c=17, precipitation_mm=0, rain_chance_pct=5,
               wind_kmh=9, is_day=True, thunderstorm=False, summary="partly cloudy")
COOL = Weather(temperature_c=7, feels_like_c=3, precipitation_mm=0, rain_chance_pct=20,
               wind_kmh=22, is_day=True, thunderstorm=False, summary="overcast")

SCENARIOS = [
    ("quick break, low energy", 30, "low", ["quiet"], MILD, History()),
    ("lunch hour, medium energy", 60, "medium", ["greenery"], MILD, History()),
    ("long window, tired legs", 120, "high", ["views"], COOL, History(recent_load_minutes=120)),
]


async def run_benchmark(
    client: httpx.AsyncClient, settings: Settings, models: list[str], runs: int
) -> list[dict]:
    rows = []
    for model in models:
        cfg = replace(settings, ollama_model=model)
        latencies: list[float] = []
        valid = 0
        total = 0
        for _, minutes, energy, interests, weather, history in SCENARIOS:
            candidates = [p for p in PLACES if stay_minutes(p, minutes) >= 10]
            allowed = {p.id: stay_minutes(p, minutes) for p in candidates}
            prompt = build_user_prompt(minutes, energy, interests, weather, candidates, history)
            for _ in range(runs):
                total += 1
                started = time.perf_counter()
                try:
                    raw = await ask_model(client, cfg, SYSTEM_PROMPT, prompt)
                    latencies.append(time.perf_counter() - started)
                    parse_picks(raw, allowed)
                    valid += 1
                except LLMError:
                    latencies.append(time.perf_counter() - started)
        rows.append({
            "model": model,
            "runs": total,
            "valid": valid,
            "median_s": statistics.median(latencies) if latencies else float("nan"),
        })
    return rows


def to_markdown(rows: list[dict]) -> str:
    lines = ["| Model | Runs | Valid replies | Median latency (s) |", "|---|---|---|---|"]
    for r in rows:
        rate = f"{r['valid']}/{r['runs']}"
        lines.append(f"| {r['model']} | {r['runs']} | {rate} | {r['median_s']:.1f} |")
    return "\n".join(lines)


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("models", nargs="+", help="Ollama model names to compare")
    parser.add_argument("--runs", type=int, default=3, help="repeats per scenario (default 3)")
    parser.add_argument("--ollama-url", default=Settings().ollama_url)
    args = parser.parse_args()
    settings = replace(Settings.from_env(), ollama_url=args.ollama_url.rstrip("/"))
    async with httpx.AsyncClient() as client:
        rows = await run_benchmark(client, settings, args.models, args.runs)
    print(to_markdown(rows))


if __name__ == "__main__":
    asyncio.run(main())
