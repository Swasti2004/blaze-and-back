# Baseline Codebase Audit (Phase 0)

Audit date: 2026-10-25
Source repository: `Swasti2004/blaze-and-back`
Frozen commit: `eb2da3ebf1b2c8112070f3835e77b026f56292e6`
Tag: `pre-migration`

---

## 1. Test Verification
Ran full automated test suite on frozen baseline:
- Total tests: **47 passed, 0 failed**
- Duration: 2.48s
- Outside service mocking: All external services (Open-Meteo, Overpass, Nominatim, Ollama) cleanly intercepted via `httpx.MockTransport`. No internet or active Ollama server required during automated testing.

---

## 2. Secrets & License Check
- **History audit**: Searched full commit history for credentials, tokens, `.env` files, API keys, or personal identifiable data. None found.
- **License**: MIT License (Copyright (c) 2026 Swasti2004). Open-source, permissive.
- **Dependencies**: `fastapi`, `uvicorn`, `httpx`, `pydantic` (all standard permissive open-source licenses: BSD / MIT / Apache 2.0).

---

## 3. Module KEEP / ADAPT / DROP Matrix

| Module | What it does | Tests | Dependencies | Decision | Reason |
|---|---|---|---|---|---|
| `app/geo.py` | Haversine distance, coordinate coarsening (privacy), geocoding | `test_units.py` | `httpx` | **KEEP** | Essential geospatial utility and privacy preserving rounding for location lookups. |
| `app/weather.py` | Open-Meteo client, WMO code parsing, weather metrics extraction | `test_units.py` | `httpx`, `app.models` | **ADAPT** | Wrap behind clean `WeatherProvider` protocol / interface for modularity and offline simulation. |
| `app/places.py` | Overpass querying, Nominatim fallback, OSM tag extraction, deduplication, walking time | `test_units.py`, `test_api.py` | `httpx`, `app.models` | **ADAPT** | Wrap behind clean `PlacesProvider` / `EventsProvider` protocol. |
| `app/filters.py` | Rule-based filtering: weather thresholds, daylight, time limits, energy limits | `test_units.py` | `app.models` | **KEEP** | Core candidate generation filter ensuring physical and weather feasibility before ranking. |
| `app/cache.py` | Simple in-memory TTL cache for external lookups | `test_api.py` | Standard library | **KEEP** | Reusable in-memory cache to respect open-source public API rate limits. |
| `app/models.py` | Pydantic data models for requests, contexts, candidates, feedback | `test_units.py` | `pydantic` | **ADAPT** | Align with target synopsis schema (e.g. fatigue state, bandit reward signals, event models). |
| `app/store.py` | SQLite local store for accept/skip/done feedback and recent load history | `test_llm_and_store.py` | `sqlite3` | **ADAPT** | Expand to track user context features, fatigue tracking (`recent_load`), and bandit reward logs. |
| `app/llm.py` | Ollama client, JSON schema enforcement, validation against candidates | `test_llm_and_store.py` | `httpx`, `json` | **ADAPT** | Move behind the unified `Ranker` interface as `LLMRanker` baseline for comparative evaluation. |
| `app/prompt.py` | LLM system and user prompt builders | `test_units.py` | `json` | **ADAPT** | Retain for `LLMRanker` baseline comparison and natural-language explanation generation. |
| `app/fallback.py` | Deterministic heuristic ranking | `test_units.py` | `app.models` | **ADAPT** | Becomes one of the comparative baselines (`RuleBasedRanker` / `PopularityRanker`). |
| `app/service.py` | Planning orchestration pipeline | `test_api.py` | `asyncio`, app modules | **ADAPT** | Refactor to invoke the contextual bandit engine (`LinUCB` / `Thompson`), fatigue model, and modular providers. |
| `app/main.py` | FastAPI application endpoints and lifecycle | `test_api.py` | `fastapi` | **ADAPT** | Update endpoints to match the M.Tech target JSON API (`/suggest`, `/feedback`, `/history`, `/data`). |
| `app/config.py` | Runtime environment settings | — | `os`, dataclass | **ADAPT** | Add configuration for bandit algorithm selection, fatigue parameters, and provider switches. |
| `static/` (`app.js`, `index.html`, `style.css`) | Web SPA front end | `test_api.py` | Vanilla web | **DROP / REUSE** | Replaced by the mobile client (or temporary PWA/WebView test shell during transition). |
| `scripts/compare_models.py` | LLM latency and validation benchmark script | `test_compare.py` | `httpx` | **ADAPT** | Shift into `/eval` evaluation suite alongside contextual bandit simulation benchmarks. |
| `tests/` (`conftest.py`, `test_*.py`) | Mock transport and test suites | pytest | pytest, `httpx` | **KEEP & EXPAND** | Keep existing unit tests as characterisation tests; expand to cover bandit rankers and fatigue model. |
| Hackathon docs (`COPILOT_*.md`, `POST_DRAFT.md`) | Hackathon challenge materials | — | — | **DROP** | Specific to DEV challenge Week 1; archive in old repo. |

---

## 4. Summary & Readiness for Phase 1
- **Preserved core**: ~70% of backend plumbing (data fetching, sanitization, filtering, caching, local store, tests) is directly kept or cleanly adapted.
- **Key transformation**: Decoupling ranking from the local LLM to support Contextual Bandits (`LinUCB`) with fatigue awareness, making the LLM an optional baseline / explainer.
- **No secrets or licensing blockers detected**.
