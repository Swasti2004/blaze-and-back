---
title: Touch Grass Planner: A local Gemma model that picks your next 30 minutes outside
published: true
tags: devchallenge, hf26challenge, opensource, ai
---

*This is a submission for the [Hacktoberfest Open-Source AI Challenge Week 1: Touch Grass](https://dev.to/challenges/hacktoberfest-week1-2026-10-05)*

## What I Built

The hardest part of taking a break outdoors is often decision fatigue: you need to pick somewhere, check the weather, see if you have time, and you end up scrolling on your phone instead of heading outside.

The repository is called **blaze-and-back** after the blaze markers painted on hiking trails and the concept of an outing that comfortably fits a time budget. On DEV, it is published as **Touch Grass Planner**.

**Touch Grass Planner** is a local-first web app designed to minimize screen time to under 30 seconds: you give it three quick inputs, it suggests where to go, and you put the phone away.

1. **How many minutes you have free** (15 to 240 minutes)
2. **Your current energy level** (Low, Medium, High)
3. **Where you are** (geolocation button or typed town) — plus optional interest tags (quiet, water, views, greenery, exercise, photography) or your own custom typed mood.

If someone doesn't have anything specific in mind, there is a **"✨ Surprise me"** mode that injects exploratory themes (like micro-adventures or hidden gems) so the model finds an interesting novelty spot.

The app fetches current weather and precipitation forecasts from Open-Meteo, discovers nearby parks, gardens, nature reserves, viewpoints, and beaches from OpenStreetMap, filters out infeasible or unsafe trips in deterministic code, and prompts a local open-weight **Gemma** model running through Ollama to select and explain the best options. You choose one, download a self-contained offline "outing card" (a standalone HTML file), and leave.

## Demo

{% youtube DMELZJ57C5Y %}

- **Direct Video Link**: [Watch the walkthrough demo on YouTube](https://youtu.be/DMELZJ57C5Y)
- **GitHub Repository**: [https://github.com/Swasti2004/blaze-and-back](https://github.com/Swasti2004/blaze-and-back)
- Repository created and developed inside the challenge window (October 2026).

## How It Was Built

**Disclosure:** The initial project scaffold — backend, tests, interface, and documentation — was generated with Claude on 2026-10-07 (`53c3e4f`). Subsequent functional improvements and resilient production features were built iteratively using the Antigravity AI coding agent across clear, verified commits:

- `5aa15c7` — 10-minute in-memory cache for weather and places lookups (keyed by coarsened coordinates)
- `361c782` — Polite exponential retry with random jitter on Overpass API transient errors (`429`, `502`, `503`, `504`)
- `1011db0` — Local outing history API (`GET /api/history`, `DELETE /api/history`) and front-end management
- `c5aa8a0` — Accessibility pass: keyboard order and programmatic focus management for errors and suggestions
- `922e796` — Automatic OpenStreetMap Nominatim fallback when global Overpass servers are overloaded
- `94dc1ba` & `4a98bd0` — Custom typed mood/activity input and top-level "✨ Surprise me" mode

### The Stack
- **Backend**: FastAPI on Python 3.11+.
- **Frontend**: Vanilla HTML5, CSS3, and JavaScript — zero frameworks, no build step, pure CSS design with trail-blaze effort badges.
- **Local Model**: Tested with `gemma2:9b`. The code's default environment tag is `gemma4` (untested on this machine).
- **Open Data**: Open-Meteo for real-time weather and OpenStreetMap (Overpass + Nominatim fallback) for geographic features.
- **Local Persistence**: Local SQLite database storing accepted, skipped, and completed outings to prevent repeated destinations and adapt after high-effort days.

### Core Architecture Rules

1. **Rules decide what is possible; the model decides what is good.** Weather hazards (thunderstorms, rain probability ≥ 60% over the next 3 hours, winds ≥ 50 km/h, extreme temperatures), darkness, and trips exceeding walking-time or energy limits are filtered out in code before the model is called.
2. **Never trust the model's output.** Suggestions returned by Ollama are checked against the explicit candidate list provided in the prompt. Hallucinated place IDs, invalid JSON, or impossible durations are rejected. If nothing valid remains or Ollama is offline, the app falls back to a deterministic rule-based ranking and clearly notes it.

### Testing

47 automated unit and integration tests run via `pytest`. They cover weather code parsing, geographic coarsening, Overpass response sanitization, LLM JSON validation, SQLite history tracking, and cache TTL expiry. Every outside service is mocked with fake HTTP transports, so the suite executes with zero network and no running model required.

## Why Open Source and Local Inference

**Privacy.** Your prompt — time available, energy level, interests, recent outings, and candidate places — goes only to the local Ollama server on your own computer. The only data that leaves your device are coordinates rounded to about 110 m, sent to Open-Meteo and OpenStreetMap for weather and map queries.

**Swappable models.** Changing one environment variable (`OLLAMA_MODEL`) swaps the model. No vendor lock-in and zero per-request fees.

**Zero API cost, and a card that works without signal.** Running locally costs nothing per query. While weather and map lookups require an active internet connection (making it local-first, not fully offline), the generated outing card is a standalone HTML document that opens reliably in airplane mode with zero connectivity.

### Local Model Comparison

Benchmarked using `scripts/compare_models.py` with `--runs 1` across three fixed planning scenarios (totaling 3 calls per model):

| Model | Scenarios run | Valid replies | Median latency (s) |
|---|---|---|---|
| **gemma2:9b** | 3 | 3/3 (100%) | 28.2 |
| **llama3.2:latest** | 3 | 3/3 (100%) | 13.9 |

Both models achieved 100% schema compliance. On this machine, `llama3.2:latest` was roughly twice as fast, but `gemma2:9b` was selected as the primary engine for its reasoned explanations and adherence to the open-weight Gemma challenge requirements.

## Taking It Outside

[If you complete an outdoor test before publishing, replace this with your real experience:
> On [day] at [time] I had [N] minutes and [energy] energy. The app suggested [place] ([category]) and estimated [X] minutes each way. It actually took [Y]. The weather said [...], and it was [...]. It got [one thing] right and [one thing] wrong. [How the screen time felt.]

*If you do not test outdoors prior to publishing, delete this section or note: "I have not yet field-tested this outdoors prior to the deadline."*]

## Known Limits

- **Local Model Latency:** `gemma2:9b` takes approximately 28 seconds per planning request on this hardware.
- **OpenStreetMap Coverage:** OpenStreetMap density varies significantly by locality; sparse areas may yield fewer named natural features.
- **Walking Time Heuristics:** Walk durations are estimated using straight-line distance × 1.3 at 4.8 km/h. Actual terrain and street layout will vary.
- **Places Only:** Currently suggests physical outdoor spaces rather than live or ticketed events.

## Prize Categories

- **Best Use of Gemma:** `gemma2:9b` runs completely on-device through Ollama, acting as the decision-making engine that analyzes open-data candidates and synthesizes actionable outdoor suggestions without cloud APIs.
- **GitHub Actions CI:** The repository implements an automated test workflow (`.github/workflows/ci.yml`) that verifies all 47 unit and integration tests on push and pull requests with zero third-party credentials.
