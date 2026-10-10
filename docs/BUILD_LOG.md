# Build log

Record what you really did, with which tool. The write-up is judged mostly on honesty and clarity, so a short accurate log beats a long polished one. Leave a row out rather than invent it.

## Work log

| Date | Tool | What it was used for | Evidence (commit, pull request or session link) |
|---|---|---|---|
| 2026-10-07 | Claude (chat) | Generated the initial scaffold: backend, tests, interface and documentation | First commit. No Entire session was captured for this. |
| | | | |
| | | | |
| | | | |

## First live run checklist

The tests use faked services, so none of this has been verified against the real ones yet. Tick each item as you check it, and note anything that surprised you.

- [ ] `ollama list` shows the model you intend to use, and `OLLAMA_MODEL` matches its tag.
- [ ] `http://localhost:8000/api/health` reports `"model_available": true`.
- [ ] A real request with a typed town returns `"engine": "llm"` (not `"fallback"`).
- [ ] The real Overpass response returns named places near you. If it returns few or none, note that OpenStreetMap coverage is thin there and try a bigger radius with `TG_SEARCH_RADIUS_M`.
- [ ] The model's real replies pass validation. If many fall back, look at `notes` in the response and adjust `app/prompt.py`.
- [ ] Run `python scripts/compare_models.py <model> <another-model> --runs 3` and save the table.
- [ ] Open the page on your phone (see the README) and confirm the typed-place path works.
- [ ] Save an outing card, switch the phone to airplane mode, and confirm the card still opens.
- [ ] Go outside with a suggestion and write down how it went (below).

## Notes from using it outside

Write this in your own words after you actually go: where you went, how long it took, what the suggestion got right or wrong, and what you would change.

## Model comparison

Paste the table from `scripts/compare_models.py` here, with the machine you ran it on.

## What I fixed or changed my mind about

Include the cases where a tool got something wrong and how you caught it. These are the most useful parts of the write-up.
