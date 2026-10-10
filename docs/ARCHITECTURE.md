# Architecture

## Request flow

`POST /api/suggest` runs this pipeline (see `app/service.py`):

1. **Resolve location.** Coordinates from the browser win. Otherwise the typed place name is geocoded with Open-Meteo's geocoder.
2. **Fetch context in parallel.** Weather from Open-Meteo, places from OpenStreetMap through Overpass. Coordinates are rounded with `coarsen()` before either request.
3. **Filter with rules** (`app/filters.py`). If the weather or daylight rules block outdoor suggestions, or nothing fits, the response explains why and the model is never called.
4. **Load history** (`app/store.py`): places visited in the last 3 days and minutes completed in the last 24 hours.
5. **Ask the local model** (`app/llm.py`) using a JSON schema in Ollama's `format` option.
6. **Validate** the reply with `parse_picks()`. If the model is unreachable, replies with bad JSON, or invents places, switch to `rank_fallback()` and say so in `notes`.
7. **Return** up to three suggestions with the walk time, stay time, effort level and a reason.

## Modules

| File | Job |
|---|---|
| `app/main.py` | FastAPI app, `/api/health`, `/api/suggest`, `/api/feedback`, static files |
| `app/service.py` | The pipeline above |
| `app/models.py` | Pydantic shapes for requests, context and responses |
| `app/geo.py` | Distance, coordinate rounding, place-name lookup |
| `app/weather.py` | Open-Meteo client and parsing |
| `app/places.py` | Overpass query, parsing, de-duplication, walking-time estimate |
| `app/filters.py` | Weather, daylight, time and energy rules |
| `app/prompt.py` | System prompt and user prompt for the model |
| `app/llm.py` | Ollama client and strict validation of model output |
| `app/fallback.py` | Deterministic ranking used when the model cannot be used |
| `app/store.py` | SQLite feedback store and the history summary |
| `static/` | The whole front end: HTML, CSS, vanilla JavaScript, no build step |
| `scripts/compare_models.py` | Benchmark several local models on fixed scenarios |

## Assumptions to know about

- **Walking time** is straight-line distance times 1.3 (streets are longer than straight lines), at 80 m per minute (about 4.8 km/h). It is an estimate.
- **Time budget.** A place fits only if the round trip leaves at least 10 minutes there (`MIN_STAY_MIN`).
- **Energy limits** on the one-way walk: low 15 minutes, medium 30, high 60. Low energy also excludes peaks.
- **Weather rules** pause suggestions for thunderstorms, a 60% or higher rain chance over the next 3 hours (or measurable rain now), wind of 50 km/h or more, a "feels like" temperature at or below -10 C or at or above 38 C, and darkness (unless `TG_ALLOW_AFTER_DARK` is set). These are heuristics, not safety guarantees.
- **Candidates sent to the model** are capped at the 12 nearest feasible places, so small local models get a short prompt.

## Why rules first, model second

Putting safety and feasibility in code keeps them predictable and testable, and keeps the prompt small enough for small local models. It also means the model's mistakes cannot cause an unsafe suggestion: it can only rank places that already passed the rules, and every pick is checked against that list.

## Fatigue-aware behaviour

The store keeps what the person accepted, skipped and completed. Two summaries feed both the prompt and the fallback ranking:

- places visited recently get a penalty, so suggestions vary;
- if completed outings in the last 24 hours add up to 90 minutes or more, easy options are favoured and active ones are penalised.

This is a simple, transparent rule, not a learned model.

## Extension points

- **Events:** add a source that returns `Place`-like items with a start time, and extend `filter_places` to check them against the free window.
- **Learning:** `Store.history()` is the seam where a bandit or other learner would plug in. The `events` table already has the data it needs.
- **Models:** change `OLLAMA_MODEL`. Use `scripts/compare_models.py` to check a new model returns valid replies before relying on it.
