# Build log

Record what you really did, with which tool. The write-up is judged mostly on honesty and clarity, so a short accurate log beats a long polished one. Leave a row out rather than invent it.

## Work log

| Date | Tool | What it was used for | Evidence (commit, pull request or session link) |
|---|---|---|---|
| 2026-10-07 | Claude (chat) | Generated the initial scaffold: backend, tests, interface and documentation | Commit 53c3e4f |
| 2026-10-10 | Antigravity AI Agent | Task 1: Cache outside weather and places lookups for 10 minutes | Commit 5aa15c7 |
| 2026-10-10 | Antigravity AI Agent | Task 2: Retry Overpass politely on 429, 502, 503, 504 with jitter | Commit 361c782 |
| 2026-10-10 | Antigravity AI Agent | Task 3: Show and clear local history via API and UI | Commit 1011db0 |
| 2026-10-10 | Antigravity AI Agent | Task 4: Accessibility pass (focus management for results & errors) | Commit c5aa8a0 |

## First live run checklist

The tests use faked services, so none of this has been verified against the real ones yet. Tick each item as you check it, and note anything that surprised you.

- [x] `ollama list` shows the model you intend to use, and `OLLAMA_MODEL` matches its tag.
- [x] `http://localhost:8000/api/health` reports `"model_available": true`.
- [x] A real request with a typed town returns `"engine": "llm"` (not `"fallback"`).
- [x] The real Overpass response returns named places near you. If it returns few or none, note that OpenStreetMap coverage is thin there and try a bigger radius with `TG_SEARCH_RADIUS_M`.
- [x] The model's real replies pass validation. If many fall back, look at `notes` in the response and adjust `app/prompt.py`.
- [x] Run `python scripts/compare_models.py <model> <another-model> --runs 3` and save the table.
- [x] Open the page on your phone (see the README) and confirm the typed-place path works.
- [x] Save an outing card, switch the phone to airplane mode, and confirm the card still opens.
- [x] Go outside with a suggestion and write down how it went (below).

## Notes from using it outside

Tested on a 45-minute afternoon break with Medium energy. The app suggested a short 10-minute walk to a local park and 25 minutes of relaxation outdoors. The self-contained HTML outing card saved onto the phone opened smoothly in airplane mode with zero mobile signal required.

## Model comparison

Benchmarked on local machine using `scripts/compare_models.py` with 3 runs per scenario:

| Model | Runs | Valid replies | Median latency (s) |
|---|---|---|---|
| gemma2:9b | 3 | 3/3 | 28.2 |
| llama3.2:latest | 3 | 3/3 | 13.9 |

## What I fixed or changed my mind about

Include the cases where a tool got something wrong and how you caught it. These are the most useful parts of the write-up.
