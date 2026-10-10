# Project brief (read this first)

This file explains what the project is, why it exists, what state it is in, the rules that must not be broken, and what to work on next. It is written for AI coding agents (such as GitHub Copilot CLI) and for human collaborators. Read it fully before changing anything.

Written on 2026-10-10. The submission deadline is 2026-10-11 23:59 PDT (2026-10-12 06:59 UTC).

## 1. What this project is

**Touch Grass Planner** is a small local-first web app that helps a person spend a short block of free time outdoors.

The person says how many minutes they have (15 to 240), how much energy they have (low, medium, high), where they are, and optionally what they are in the mood for (quiet, water, views, greenery, exercise, photography). The app then:

1. looks up the current weather and short-term rain chance (Open-Meteo);
2. finds nearby named parks, gardens, nature reserves, viewpoints, beaches and peaks (OpenStreetMap through the Overpass API);
3. removes anything that cannot work, using plain rules (weather, daylight, time budget, energy);
4. asks a **local open-weight model** (Gemma, served by Ollama) to rank the remaining places and explain each pick in one sentence;
5. shows up to three suggestions with walk time, stay time and effort level;
6. lets the person take one and save a small self-contained "outing card" (an HTML file that opens with no signal);
7. stores accept / skip / done feedback locally and uses it to avoid repeats and to go easy after a busy day.

The point is that the screen should be the shortest part of the experience: a 30-second interaction, then the phone goes away.

## 2. Why it exists (context an agent needs)

- It is an entry in the **DEV Hacktoberfest Open-Source AI Challenge, Week 1: "Touch Grass"**. The theme: build something with open-weight models or open-source AI that gets people off the screen and into the world.
- Judging criteria, in order of weight: **writing quality of the DEV post** (heaviest), relevance to the theme (open-source AI must be at the core), creativity, technical execution (does it work, is it well built), and optional use of partner technology.
- Rules that matter here (verify on the official rules page): the project and its repository must be started and finished inside the challenge window (October 5 to 11, 2026); commits after the deadline must be noted in the README; teams are up to four people; participants must be 18 or older; the post is in English.
- The author is entering three optional partner categories, and only because they genuinely use them:
  - **Best Use of Gemma:** the local model that ranks and explains.
  - **Best Use of Entire:** agent sessions are captured with the Entire CLI and shared in the post.
  - **Best Use of GitHub Copilot:** the author builds improvements with Copilot CLI (or the coding agent) and automates tests with GitHub Actions.
- The "why open innovation matters" argument of the post is: the model prompt (time, energy, interests, recent outings, nearby places) never leaves the user's machine; the model can be swapped with one environment variable; there is no per-request fee. The honest limits are that weather and map lookups still need the internet (so it is local-first, not offline) and that small local models are slower and sometimes unreliable.

## 3. Current state (be honest about it)

**Built:** a complete working backend (FastAPI), a single-page front end (plain HTML, CSS, JavaScript, no build step), 42 automated tests, a model-comparison script, CI, and documentation.

**Verified:**
- The 42 tests pass. They replace every outside service (Open-Meteo, Overpass, the geocoder, Ollama) with fakes, using `httpx.MockTransport`.
- The front end was exercised in a simulated DOM (jsdom) against a live server with the same fakes: the form, the suggestions, the outing card and the feedback flow all worked.

**Not yet verified:**
- Behaviour against a real Gemma model through a real Ollama. Real replies may fail validation more often than the tests suggest.
- Real Overpass and Open-Meteo responses. The fake payloads are shaped from documentation and memory.
- Quality of OpenStreetMap data in the author's area.
- The page in a real browser and on a phone (layout, touch, geolocation).
- The "first live run" checklist in `docs/BUILD_LOG.md` tracks these.

The initial scaffold was generated with Claude (Anthropic) outside Entire and Copilot. That is recorded in `docs/BUILD_LOG.md`. Everything done after the first commit is meant to be attributable to the tool actually used.

## 4. How it is built

### Request flow (`POST /api/suggest`, implemented in `app/service.py`)

1. Resolve the location. Coordinates win over a typed place name; a typed name is geocoded with Open-Meteo's geocoder.
2. Fetch weather and places in parallel. Coordinates are rounded with `coarsen()` (3 decimals, about 110 m) before any outside request.
3. Apply the rules in `app/filters.py`. If the weather or daylight rules block outdoor suggestions, or nothing fits, return an explanation with `engine: "none"` and **do not call the model**.
4. Load history from SQLite: places visited in the last 3 days and minutes completed in the last 24 hours.
5. Build the prompt (`app/prompt.py`) and call Ollama (`app/llm.py`) with a JSON schema in the `format` option.
6. Validate with `parse_picks()`. Drop invented ids, duplicates and bad fields; clamp durations. If nothing valid is left, or Ollama is unreachable, use `rank_fallback()` and add a note.
7. Return up to three suggestions.

### File map

| Path | Job |
|---|---|
| `app/main.py` | `create_app(settings, transport)`, routes, static files |
| `app/service.py` | The pipeline above; `ServiceError` for user-facing failures |
| `app/models.py` | Pydantic models for requests, context and responses |
| `app/config.py` | `Settings` read from environment variables |
| `app/geo.py` | `haversine_m`, `coarsen`, `geocode` |
| `app/weather.py` | Open-Meteo client, `parse_weather` |
| `app/places.py` | Overpass query, `parse_overpass`, de-duplication, walking-time estimate |
| `app/filters.py` | Weather, daylight, time and energy rules and their constants |
| `app/prompt.py` | System prompt and user prompt |
| `app/llm.py` | Ollama client, JSON schema, `parse_picks` |
| `app/fallback.py` | Deterministic ranking when the model cannot be used |
| `app/store.py` | SQLite feedback store and `history()` |
| `static/` | `index.html`, `style.css`, `app.js` |
| `scripts/compare_models.py` | Benchmarks several Ollama models on fixed scenarios |
| `tests/` | `conftest.py` has `FakeNetwork`; unit, LLM/store, API and compare tests |

### HTTP API

- `GET /api/health` returns `{ollama: bool, model: str, model_available: bool}`.
- `POST /api/suggest` takes `{lat?, lon?, place?, minutes: 15..240, energy: low|medium|high, interests: string[]}` and returns `{suggestions[], weather, location_label, engine: "llm"|"fallback"|"none", model, notes[]}`. Each suggestion has `place_id, place_name, category, lat, lon, walk_minutes, distance_m, osm_url, activity, reason, duration_minutes, effort`.
- `POST /api/feedback` takes `{place_id, place_name, category, action: accepted|skipped|done, effort?, duration_minutes?}` and returns 204.

### Configuration (environment variables, all optional)

`OLLAMA_MODEL` (default `gemma4`), `OLLAMA_URL`, `OLLAMA_TIMEOUT_S`, `TG_SEARCH_RADIUS_M` (3000), `TG_COORD_DECIMALS` (3), `TG_ALLOW_AFTER_DARK` (false), `TG_DB_PATH`. See `.env.example`.

### Key assumptions (documented in `docs/ARCHITECTURE.md`)

Walking time is straight-line distance times 1.3 at 80 m per minute. A place needs at least 10 minutes of stay after the round trip. One-way walk limits by energy: low 15, medium 30, high 60 minutes; low energy excludes peaks. Suggestions pause for thunderstorms, rain chance of 60% or more, wind of 50 km/h or more, extreme cold or heat, and darkness. At most 12 candidates are sent to the model.

## 5. Rules that must not be broken

Each rule is enforced by a test where one exists. If a change touches a rule, change the test deliberately and explain why.

1. **Privacy.** Coordinates are rounded with `coarsen()` before any outside request. The model prompt goes only to the local Ollama URL. (Tests: `test_coordinates_are_rounded_before_leaving_the_machine`, `test_prompt_never_leaves_localhost`.)
2. **Rules before the model.** Weather, daylight, time and energy filtering happen in code before the model is called. Never move safety behaviour into the prompt. (Test: `test_bad_weather_pauses_suggestions`.)
3. **Never trust model output.** Every suggestion must come from the candidate list. Invented places fall back to the rule-based ranking. (Tests: `test_invented_place_falls_back`, the `parse_picks` tests.)
4. **Untrusted text.** OpenStreetMap names and model replies are untrusted. Names are sanitised in `places.py`; the front end inserts server text with `textContent`, never `innerHTML`. (Test: `test_names_are_sanitised`.)
5. **No outside services in tests.** Tests must run with no internet and no model, using `FakeNetwork` and `httpx.MockTransport`.
6. **Open by default.** Do not make a paid or closed service a requirement. An optional, clearly labelled integration is acceptable only if it is off by default.
7. **No new dependencies** without a clear reason stated in the pull request or commit message.
8. **Honest wording.** Do not write claims in the README, docs or UI that the code and tests do not support. The app is local-first, not offline. The weather rules are heuristics, not safety guarantees. This is not medical or mental health advice.

## 6. Working agreements for agents

- Read `.github/copilot-instructions.md`, this file, and the relevant task in `docs/COPILOT_TASKS.md` before editing.
- Work on **one task at a time** and keep each change small. Each task should end in its own commit, because Entire records one checkpoint per commit and the author will show these in the post.
- Run `python -m pytest -q` before finishing and fix failures. Add tests for every behaviour change.
- Match the existing style: Python 3.11+, type hints, small pure functions, comments that explain why rather than what.
- Explain what you changed and why in plain language when you finish, and say what you did **not** verify.
- Ask the author before making large structural changes, changing the safety thresholds in `app/filters.py`, or touching licence, CI or Entire configuration.
- **Do not edit the evidence in `docs/BUILD_LOG.md`.** The work-log rows, benchmark tables and outdoor-test notes are the author's own record. Never invent benchmark numbers, test results, user feedback or outdoor-test stories, anywhere.
- Never commit secrets, API keys or the contents of `data/` or `.env`.

## 7. The plan

### Timeline

Today is the working window. Deadline: 2026-10-12 06:59 UTC. The author aims to submit before the end of 2026-10-11 local time.

| Stage | What | Who |
|---|---|---|
| 1 | Push the repo, install Entire, enable it for Copilot CLI, install Copilot CLI, check CI is green | Author |
| 2 | First live run with real Ollama, Gemma, Overpass and Open-Meteo; fill the checklist in `docs/BUILD_LOG.md`; report failures | Author, with help from agents |
| 3 | Build 2 or 3 backlog tasks with Copilot, one commit each | Agent, reviewed by the author |
| 4 | Run `scripts/compare_models.py` on two models; use the app outside; record a 60 to 90 second demo | Author |
| 5 | Write and publish the DEV post from `docs/POST_DRAFT.md`, using only true statements | Author |

If time runs short, drop partner categories that were not genuinely used. A working app and an honest post matter more than extra integrations.

### Task backlog (full acceptance criteria are in `docs/COPILOT_TASKS.md`)

1. **Cache outside lookups for 10 minutes.** Key by rounded coordinates (and radius for places). A second identical request in the window makes no calls to `api.open-meteo.com` or `overpass-api.de`. Test with `FakeNetwork` counting requests. Likely files: `app/service.py` (or a new `app/cache.py`), `tests/test_api.py`.
2. **Retry Overpass politely.** Up to 2 retries on 429, 502, 503 and 504, with a short, growing, slightly random delay; no retries on other errors. Tests for "429 then 200" and "always fails" (which must still produce the existing friendly 502 message). File: `app/places.py`.
3. **Show and clear what the app remembers.** `GET /api/history` (last 10 events), `DELETE /api/history`, and a "Recent outings" list with a "Clear history" button in the page, built with `textContent`. Files: `app/store.py`, `app/main.py`, `static/`, tests.
4. **Accessibility pass.** Keyboard order, visible focus, contrast, labels, and announcements for results and errors. Fix what is found. File: `static/`.
5. **Stretch: pluggable event source.** An `EventSource` protocol and a source reading a hand-written `data/events.json`, with time-window logic. Keep any paid or closed event API out of the default setup.

### Out of scope (do not build)

Accounts or login, cloud hosting, mobile apps, translations, paid or closed APIs by default, a learned recommender or bandit (mentioned only as future work), medical or mental-health features.

## 8. Definition of done for any task

- The behaviour works as described and the acceptance criteria in `docs/COPILOT_TASKS.md` are met.
- `python -m pytest -q` passes, with new tests covering the change.
- The rules in section 5 still hold.
- README or `docs/ARCHITECTURE.md` is updated if behaviour or configuration changed.
- The final message states what was changed, what was tested, and what was not verified.

## 9. Known risks and open questions

- Real Gemma replies might often fail the JSON schema or be slow on a modest laptop. The fallback keeps the app working, but the prompt in `app/prompt.py` may need tuning after the first live run.
- Models that "think" (reasoning models) may behave differently with structured output. `scripts/compare_models.py` is how to find out.
- OpenStreetMap coverage varies. A thin area may return few or no places.
- Public Overpass servers are rate limited and sometimes busy, which is why caching and retries are on the backlog.
- Walking-time estimates are crude. The author's outdoor test should say how far off they were.
- Geolocation in the browser works only on https or localhost, so phones over plain http must use the typed-place path.

## 10. Glossary

- **Ollama:** a local program that runs open-weight models and serves them over HTTP on `localhost:11434`.
- **Gemma:** Google's family of open-weight models, used here as the default model.
- **Overpass API:** a read-only query service for OpenStreetMap data.
- **Open-Meteo:** a free weather API that needs no key.
- **Outing card:** a self-contained HTML page with the plan, coordinates and a map link, saved on the device.
- **Entire:** a CLI that captures agent coding sessions as checkpoints linked to Git commits, stored on the `entire/checkpoints/v1` branch.
- **Checkpoint:** one captured record of agent-assisted work, created when a commit is made.
