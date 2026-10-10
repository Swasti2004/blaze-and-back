# Instructions for GitHub Copilot

**Start by reading `docs/PROJECT_BRIEF.md`.** It explains what this project is, the challenge it is
entered in, its current state, the rules that must not be broken, and the task backlog
(`docs/COPILOT_TASKS.md`). Work on one task at a time and commit after each one.

This is Touch Grass Planner: a local-first app that suggests short outdoor outings using a
local open-weight model (through Ollama), open weather data (Open-Meteo) and open map data
(OpenStreetMap via Overpass).

## Rules that must not be broken
- Privacy: coordinates must be rounded with `app.geo.coarsen` before any outside request.
  The model prompt must only ever be sent to the local Ollama URL.
- Treat model output and OpenStreetMap text as untrusted. Validate model output with
  `app.llm.parse_picks`; never show a place the candidate list did not contain.
- Weather and daylight filters live in `app/filters.py` and run before the model is called.
  Do not move safety behaviour into the prompt.
- In the front end, insert server text with `textContent`, never `innerHTML`.

## Conventions
- Python 3.11+, type hints, small pure functions where possible.
- Every change needs tests. Run `python -m pytest -q` before finishing.
- Tests fake all outside services with `httpx.MockTransport` (see `tests/conftest.py`).
  Do not add tests that need the internet or a running model.
- No new dependencies unless there is a clear reason; explain it in the pull request.
