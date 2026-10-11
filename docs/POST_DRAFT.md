# Post draft for DEV

> **BEFORE PUBLISHING — complete all [ACTION NEEDED] items below, then delete this block.**
>
> - [ACTION NEEDED] **"Taking It Outside"** — go on a real outing and replace the placeholder text with what actually happened. Include the place, actual time versus estimate, and what was off. If you can't go before the deadline, delete that section entirely (a missing section costs far less than a false one).
> - [ACTION NEEDED] **Demo** — record a 60–90 second screencast or add three screenshots (form, suggestions, outing card) and paste the link/image into the Demo section.
> - [ACTION NEEDED] **Published flag** — `published: true` will make this go live on save. Confirm that's what you want, and check the challenge rules on post edits after the deadline.

---

---
title: Touch Grass Planner: A local Gemma model that picks your next 30 minutes outside
published: false
tags: devchallenge, hf26challenge, opensource, ai
---

*This is a submission for the [Hacktoberfest Open-Source AI Challenge Week 1: Touch Grass](https://dev.to/challenges/hacktoberfest-week1-2026-10-05)*

## What I Built

The hardest part of taking a break outdoors is often decision fatigue: you need to pick somewhere, check the weather, see if you have time, and you end up scrolling instead of going. The app is called **blaze-and-back** after the blaze markers on hiking trails and the idea of a round-trip that fits a time budget. On DEV it's published as Touch Grass Planner.

**Touch Grass Planner** is a local-first web app built for a fast decision: you give it three numbers, it gives you a place to go, you put the phone away. Inputs:
1. How many minutes you have free (15 to 240)
2. Your energy level (Low, Medium, High)
3. Where you are (geolocation or typed town) — and optional mood interests (quiet, water, views, greenery, exercise, photography)

It fetches the current weather from Open-Meteo and nearby parks, gardens, nature reserves, beaches, viewpoints, and peaks from OpenStreetMap (Overpass API), removes options that won't work with ordinary code, and asks a local open-weight **Gemma** model running via Ollama to pick the best fit and explain why. You choose one, save a self-contained offline "outing card" (a standalone HTML file), and leave.

It is built for developers, students, and remote workers who need a frictionless reason to step outside.

## Demo

[ACTION NEEDED: paste a recording link or three screenshots here — form, suggestions card, outing card. A 60–90 second recording will help more than any text.]

- **Repository**: [https://github.com/Swasti2004/blaze-and-back](https://github.com/Swasti2004/blaze-and-back)
- Repository started on 2026-10-07, inside the challenge window (October 5–11, 2026).

## How It Was Built

**Disclosure:** The initial scaffold — backend, tests, interface and documentation — was generated with Claude on 2026-10-07 (commit `53c3e4f`). Four improvement tasks were then implemented using the Antigravity AI coding agent, with each task verified against the automated test suite and committed individually:

- `5aa15c7` — Task 1: 10-minute in-memory cache for weather and places lookups
- `361c782` — Task 2: polite retry with jitter on Overpass transient errors
- `1011db0` — Task 3: `GET /api/history` and `DELETE /api/history` endpoints plus UI
- `c5aa8a0` — Task 4: accessibility pass — focus management for errors and results

The stack:
- **FastAPI** backend, Python 3.11+.
- **Frontend**: vanilla HTML5, CSS3, and JavaScript — no framework, no build step, focus management for errors and results.
- **Local LLM**: Tested with `gemma2:9b`. The code's default tag is `gemma4`, which I haven't tested yet.
- **Open Data**: Open-Meteo for weather forecasts (no API key) and OpenStreetMap via Overpass API for geo features.
- **Local SQLite store**: keeps accepted, skipped, and completed outings locally.

### Two rules the model can't break

1. **Rules decide what is possible; the model decides what is good.** Thunderstorms, a rain chance of 60% or more over the next three hours, strong wind (≥50 km/h), extreme temperatures, darkness, and trips too long for the time or energy level are removed by ordinary code before the model is called. A bad model reply cannot produce a suggestion for genuinely bad conditions.
2. **The model's output is never trusted.** Every suggestion is checked against the candidate list that was sent in the prompt. Hallucinated place IDs, bad JSON, and impossible durations are dropped. If nothing valid is left, the app falls back to a simple deterministic ranking and says so.

### Caching and resilience

External lookups are cached in memory for 10 minutes, keyed by coordinates coarsened to about 110 m and the search radius. Overpass `429`, `502`, `503`, and `504` responses trigger up to two retries with exponential backoff and random jitter, to avoid hammering a public service during busy periods.

### Testing

47 automated unit and integration tests cover weather parsing, geo rounding, Overpass parsing and deduplication, LLM JSON validation and fallback, local SQLite history listing and clearing, and cache TTL. Every outside service (weather, places, geocoder, Ollama) is replaced with a fake transport, so the suite runs with no internet and no running model.

## Why Open Source and Local Inference

**Privacy.** Your prompt — time available, energy level, interests, recent outings, and the places around you — goes only to the Ollama server on your own computer. The only data that leaves is coordinates rounded to about 110 m, sent to Open-Meteo and Overpass for weather and map lookups.

**Swappable model.** Changing one environment variable (`OLLAMA_MODEL`) changes the model. It costs nothing to try a different one.

**Zero API cost, and a card that works without signal.** Running locally costs nothing per request. The app is local-first, not fully offline — weather and map lookups still need the internet. But the generated outing card is a standalone HTML file that opens in airplane mode with no dependencies.

### Model comparison

I ran `scripts/compare_models.py` with `--runs 1` across three fixed planning scenarios (the script runs each scenario once per model, totalling three calls per model). Both models passed all three validation checks. `llama3.2` was roughly twice as fast on my hardware. I chose `gemma2:9b` as the primary model because the challenge asks for Gemma, and both models produced valid structured output in every run.

| Model | Scenarios run | Valid replies | Median latency (s) |
|---|---|---|---|
| gemma2:9b | 3 | 3/3 | 28.2 |
| llama3.2:latest | 3 | 3/3 | 13.9 |

## Taking It Outside

[ACTION NEEDED: go on a real outing using the app and write what actually happened. Include the weather you saw, where you went, how long the walk really took versus the estimate, and whether the suggestion was right. If you cannot go before the deadline, delete this section.]

## Known Limits

- **Latency:** On my machine, `gemma2:9b` takes about 28 seconds to respond. `llama3.2` is faster (14 s) but is not a Gemma model.
- **OpenStreetMap coverage:** Some areas have few named parks or viewpoints. If you get very few suggestions, try increasing `TG_SEARCH_RADIUS_M`.
- **Walking times:** Estimated as straight-line distance × 1.3 at 4.8 km/h. Real walk times will differ.
- **No live events:** The app suggests places, not timed events.

## Prize Categories

- **Best Use of Gemma:** `gemma2:9b` runs locally via Ollama and handles ranking and explanation. It is the only component that needs to reason about suitability — everything else is rule-based code. The challenge uses Gemma because it is open-weight and runs without any cloud API.
- **GitHub Actions CI:** The repository includes `.github/workflows/ci.yml`, which runs the 47-test suite on every push and pull request without any secrets or API keys.
