"""Talking to models (Gemini Flash, Groq, OpenAI, Ollama), and validating what comes back.

Nothing from the model is trusted: every pick is checked against the candidate list.
"""

from __future__ import annotations

import json
import re

import httpx
from pydantic import ValidationError

from .config import Settings
from .models import Pick

MAX_PICKS = 6
MIN_DURATION = 5

# JSON schema passed to model structured-output format option.
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
    """Send one chat request to configured model (Gemini, Groq, OpenAI, or Ollama) and return raw text."""

    # 1. Google Gemini Flash (Fast, free tier)
    if settings.gemini_api_key:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.gemini_model}:generateContent?key={settings.gemini_api_key}"
        )
        combined_prompt = (
            f"{system}\n\n"
            f"You MUST output valid JSON matching this schema:\n{json.dumps(SUGGESTION_SCHEMA)}\n\n"
            f"User input:\n{user}"
        )
        body = {
            "contents": [{"parts": [{"text": combined_prompt}]}],
            "generationConfig": {
                "temperature": 0.4,
                "responseMimeType": "application/json",
            },
        }
        try:
            response = await client.post(url, json=body, timeout=20.0)
            response.raise_for_status()
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as exc:
            raise LLMError(f"Gemini API error: {exc}") from exc

    # 2. Groq (Ultra-fast cloud inference)
    if settings.groq_api_key:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {settings.groq_api_key}"}
        body = {
            "model": settings.groq_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.4,
            "response_format": {"type": "json_object"},
        }
        try:
            response = await client.post(url, json=body, headers=headers, timeout=15.0)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as exc:
            raise LLMError(f"Groq API error: {exc}") from exc

    # 3. OpenAI (gpt-4o-mini)
    if settings.openai_api_key:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
        body = {
            "model": settings.openai_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.4,
            "response_format": {"type": "json_object"},
        }
        try:
            response = await client.post(url, json=body, headers=headers, timeout=20.0)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as exc:
            raise LLMError(f"OpenAI API error: {exc}") from exc

    # 4. Local Ollama model (skipped on Vercel/cloud where localhost doesn't exist)
    import os
    if os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME") or os.getenv("RENDER"):
        raise LLMError("Fast Cloud Mode: rule-based ranking activated for instant response.")

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
            f"{settings.ollama_url}/api/chat", json=body, timeout=min(settings.ollama_timeout_s, 2.5)
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
            raise LLMError("The model did not return JSON.") from None
        try:
            data = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            raise LLMError("The model returned malformed JSON.") from None
    if not isinstance(data, dict):
        raise LLMError("The model returned JSON in an unexpected shape.")
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
        raise LLMError("The model reply had no suggestions list.")

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
        raise LLMError("The model did not return any usable suggestions.")
    return picks
