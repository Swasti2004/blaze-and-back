"""The comparison script runs against a fake Ollama and reports sensible numbers."""

from __future__ import annotations

import asyncio
import importlib.util
import json
from pathlib import Path

import httpx

from app.config import Settings

spec = importlib.util.spec_from_file_location(
    "compare_models", Path(__file__).resolve().parent.parent / "scripts" / "compare_models.py"
)
compare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compare)


def fake_ollama(request: httpx.Request) -> httpx.Response:
    body = json.loads(request.content)
    if body["model"] == "good":
        content = json.dumps({"suggestions": [{
            "place_id": "way/3", "activity": "Stroll", "reason": "Close and quiet.",
            "duration_minutes": 15, "effort": "easy"}]})
    else:
        content = "I think you should go outside!"
    return httpx.Response(200, json={"message": {"content": content}})


def test_benchmark_reports_valid_rates():
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(fake_ollama)) as client:
            return await compare.run_benchmark(client, Settings(), ["good", "bad"], runs=2)

    rows = asyncio.run(run())
    good, bad = rows
    assert good["valid"] == good["runs"] == 6
    assert bad["valid"] == 0
    table = compare.to_markdown(rows)
    assert "| good | 6 | 6/6 |" in table and "| bad | 6 | 0/6 |" in table
