"""Talking to the local model through Ollama, and validating what comes back.

Small local models sometimes return malformed or invented output, so nothing
from the model is trusted: every pick is checked against the candidate list.
"""

from __future__ import annotations

import json
import re

import httpx
from pydantic import ValidationError

from .config import Settings
from .models import Pick

MAX_PICKS = 3
MIN_DURATION = 5

# JSON schema passed to Ollama's structured-output `format` option.
SUGGESTION_SCHEMA = {
    "type": "object",
    "properties": {
        "suggestions": {
            "type": "array",
            "minItems": 1,
            "maxItems": MAX_PICKS,
            "items": {
                "type": "object",
                "properties": {
                    "place_id": {"type": "string"},
                    "activity": {"type": "string"},
                    "reason": {"type": "string"},
                    "duration_minutes": {"type": "integer"},
                    "effort": {"type": "string", "enum": ["easy", "moderate", "active"]},
                },
                "required": ["place_id", "activity", "reason", "duration_minutes", "effort"],
            },
        }
    },
    "required": ["suggestions"],
}


class LLMError(Exception):
    """The model could not be reached or did not return usable suggestions."""


async def ask_model(client: httpx.AsyncClient, settings: Settings, system: str, user: str) -> str:
    """Send one chat request to Ollama and return the raw text of the reply."""
    body = {
        "model": settings.ollama_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "format": SUGGESTION_SCHEMA,
        "options": {"temperature": 0.4},
    }
    try:
        response = await client.post(
            f"{settings.ollama_url}/api/chat", json=body, timeout=settings.ollama_timeout_s
        )
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPError as exc:
        raise LLMError(f"Could not reach the local model ({type(exc).__name__}).") from exc
    except ValueError as exc:
        raise LLMError("The local model returned a reply that is not JSON.") from exc

    content = (data.get("message") or {}).get("content")
    if not isinstance(content, str) or not content.strip():
        raise LLMError("The local model returned an empty reply.")
    return content


_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


def _load_json(raw: str) -> dict:
    text = _FENCE.sub("", raw.strip())
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise LLMError("The local model did not return JSON.") from None
        try:
            data = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            raise LLMError("The local model returned malformed JSON.") from None
    if not isinstance(data, dict):
        raise LLMError("The local model returned JSON in an unexpected shape.")
    return data


def parse_picks(raw: str, allowed: dict[str, int]) -> list[Pick]:
    """Validate the model's reply.

    `allowed` maps each candidate place id to the minutes available there.
    Picks with unknown ids, duplicates or broken fields are dropped. If nothing
    valid is left, LLMError is raised so the caller can fall back.
    """
    data = _load_json(raw)
    items = data.get("suggestions")
    if not isinstance(items, list):
        raise LLMError("The local model reply had no suggestions list.")

    picks: list[Pick] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        place_id = item.get("place_id")
        if not isinstance(place_id, str) or place_id not in allowed or place_id in seen:
            continue
        try:
            duration = int(item.get("duration_minutes"))
        except (TypeError, ValueError):
            continue
        duration = max(MIN_DURATION, min(duration, allowed[place_id]))
        try:
            pick = Pick(
                place_id=place_id,
                activity=" ".join(str(item.get("activity", "")).split())[:120],
                reason=" ".join(str(item.get("reason", "")).split())[:220],
                duration_minutes=duration,
                effort=item.get("effort"),
            )
        except ValidationError:
            continue
        if not pick.activity or not pick.reason:
            continue
        seen.add(place_id)
        picks.append(pick)
        if len(picks) >= MAX_PICKS:
            break

    if not picks:
        raise LLMError("The local model did not return any usable suggestions.")
    return picks
