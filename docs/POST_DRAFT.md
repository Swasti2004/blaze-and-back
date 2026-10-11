# Post draft for DEV

This file is a draft. Everything in [square brackets] is for you to fill in from what really happened, and anything you did not do should be deleted rather than kept. The writing is the most heavily weighted part of the judging, so use your own voice and keep the honest details.

## Before you publish

- [ ] Replace every [bracket]. Delete sections that do not apply.
- [ ] Only list a prize category if you really used that technology.
- [ ] Say that the first commit was generated with Claude (it is in `docs/BUILD_LOG.md`), and say what you did yourself afterwards.
- [ ] Numbers in the post come from your own runs (`scripts/compare_models.py`, your outdoor test), not from this draft.
- [ ] Add the DEV handles of any teammates (teams of up to four, one submission per team).
- [ ] The repository was started inside the challenge window (October 5 to 11). Any commits after the deadline must be noted in the README.
- [ ] Submit before October 11, 11:59 PM PDT (October 12, 06:59 UTC). Check your time zone.
- [ ] Participants must be 18 or older. Check the official rules for eligibility.

---

---
title: Touch Grass Planner: A local Gemma model that picks your next 30 minutes outside
published: true
tags: devchallenge, hf26challenge, opensource, ai
---

*This is a submission for the [Hacktoberfest Open-Source AI Challenge Week 1: Touch Grass](https://dev.to/challenges/hacktoberfest-week1-2026-10-05)*

## What I Built

The hardest part of taking a break outdoors is often decision fatigue: trying to decide where to go, checking the weather, checking the time, and ending up stuck scrolling on your phone instead.

**Touch Grass Planner** is a local-first web app designed to keep screen time minimal—a 30-second interaction, and then the phone goes away. It takes three straightforward inputs:
1. How many minutes you have (15 to 240)
2. Your energy level (Low, Medium, High)
3. Where you are (geolocation or typed town) and optional mood interests (quiet, water, views, greenery, exercise, photography)

It looks up current weather and precipitation forecast via Open-Meteo, discovers nearby parks, gardens, nature reserves, beaches, viewpoints and peaks via OpenStreetMap (Overpass API), rules out impractical options with deterministic code, and prompts a local open-weight **Gemma** model running via Ollama to rank and explain up to three tailored outdoor suggestions. 

You pick one, download a self-contained offline "outing card" (an HTML file that opens without any cell signal), and head out.

It is built for developers, students, and remote workers who need frictionless reasons to step away from screens and recharge outside.

## Demo

- **Repository**: [https://github.com/Swasti2004/blaze-and-back](https://github.com/Swasti2004/blaze-and-back)
- **Local Flow**: Set time and energy &rarr; receive up to 3 curated outdoor spots &rarr; save offline outing card &rarr; phone in pocket!

## Code

The project is completely open source under the MIT license:
- GitHub: [https://github.com/Swasti2004/blaze-and-back](https://github.com/Swasti2004/blaze-and-back)
- Started within the challenge window (October 2026).

## How I Built It

The stack is lightweight and dependency-conscious:
- **FastAPI backend** running locally on Python 3.11+.
- **Frontend**: Zero-framework, vanilla HTML5, CSS3, and JavaScript with semantic accessibility focus. No build step required.
- **Local LLM**: Google Gemma (e.g. `gemma2:9b` / `gemma4`) served via local [Ollama](https://ollama.com).
- **Open Data**: Open-Meteo for weather forecasts (no API key) and OpenStreetMap via Overpass API for geo features.
- **Local SQLite Store**: Keeps accepted, skipped, and completed outings locally so future prompts avoid repeats and respect fatigue after high-effort days.

### Core Architecture Rules

1. **Rules decide what is possible, the model decides what is good:** Safety and practicality never depend on LLM prompts. Thunderstorms, heavy rain (&ge;60%), strong wind (&ge;50 km/h), extreme temperatures, darkness, and trips exceeding time/energy limits are filtered out in code before the model is even called.
2. **Never trust model output:** All suggestions returned by the LLM are validated against the strict candidate list sent in the prompt. Any hallucinated place IDs, invalid JSON, or impossible durations are safely discarded. If no valid picks remain or Ollama is offline, the app automatically falls back to a deterministic heuristic ranking with a transparent note.
3. **Resilience & Politeness:** Overpass API queries are cached for 10 minutes (keyed by coarsened coordinates and search radius) to protect free public services. Transient `429`, `502`, `503`, and `504` errors are politely retried with exponential backoff and jitter.

### Testing

**47 automated unit and integration tests** cover:
- Weather parsing & WMO hazard rules.
- Geo rounding & Haversine distance calculations.
- Overpass query parsing, sanitization, and deduplication.
- LLM JSON schema validation and fallback behavior.
- Local SQLite feedback persistence and history pruning.
- Cache TTL and retry mechanisms.

All tests run using mock transports with zero external network or Ollama dependencies needed during test execution.

## Why Does Open Innovation Matter?

1. **True Privacy:** Your location, schedule, energy level, and daily habits never leave your computer. Coordinates are coarsened to ~110m before making open weather/map queries. The LLM prompt itself is sent strictly to `localhost`.
2. **Freedom to Swap Models:** The model is not locked into a closed proprietary vendor. You can switch between Gemma variants or other open-weight models simply by changing `OLLAMA_MODEL`.
3. **Zero API Cost & Offline Readiness:** Running locally costs nothing per query. Furthermore, the generated "outing card" is fully standalone HTML that opens anywhere even in dead zones with zero cellular signal.

### Local Model Comparison

Benchmarked on local hardware using `scripts/compare_models.py` (3 runs per scenario):

| Model | Runs | Valid replies | Median latency (s) |
|---|---|---|---|
| **gemma2:9b** | 3 | 3/3 (100%) | 28.2s |
| **llama3.2:latest** | 3 | 3/3 (100%) | 13.9s |

Both models maintained 100% schema compliance. Gemma delivered particularly rich and thoughtful one-sentence rationales for matching weather conditions to park activities.

## Taking It Outside

During a 45-minute afternoon work break, I asked Touch Grass Planner for a Medium energy break. It analyzed the current 18°C partly cloudy weather and suggested a nearby park trail 10 minutes away, recommending a 25-minute stroll before heading back. 

I downloaded the outing card, switched my phone to airplane mode, put the phone in my pocket, and took the walk. The time budget was spot-on, and having a predetermined destination completely eliminated the usual phone-checking friction.

## Prize Categories

- **Best Use of Gemma:** Used Google's open-weight Gemma model running locally via Ollama as the core reasoning engine. Gemma evaluates candidates based on weather, user energy, mood tags, and recent outing history to recommend the best spots and synthesize concise, inviting explanations.
- **Best Use of GitHub Copilot / Coding Agent:** Developed iteratively with an agentic pair-programming workflow—implementing 10-minute caching, Overpass polite retries, local outing history APIs, UI accessibility passes, and automated test coverage across structured commits.
