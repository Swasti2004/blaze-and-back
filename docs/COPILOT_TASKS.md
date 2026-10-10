# Tasks to build with GitHub Copilot

Each task is a real improvement with a clear way to check it. Run `python -m pytest -q` after each one, and commit after each so Entire records one checkpoint per task.

## 1. Cache outside lookups for a few minutes

**Why:** Open-Meteo and Overpass are free public services. Asking them again for the same area within minutes is wasteful.

**Do:** Add a small in-memory cache with a 10-minute lifetime for weather and for places, keyed by the rounded coordinates (and radius for places).

**Done when:** a second identical `/api/suggest` request within the lifetime makes no calls to `api.open-meteo.com` or `overpass-api.de`. Add a test using `FakeNetwork` in `tests/conftest.py` that counts requests.

## 2. Retry Overpass politely

**Why:** Public Overpass servers sometimes answer 429 (too busy) or 504 (timeout).

**Do:** In `app/places.py`, retry up to 2 times on 429, 502, 503 and 504 with a short, growing, slightly random delay. Do not retry other errors.

**Done when:** a test where the fake server answers 429 once and then 200 passes, and a test where it always fails still ends in the existing "Could not reach the weather or places service" message.

## 3. Show and clear what the app remembers

**Why:** The app stores accepted, skipped and completed outings locally. People should be able to see and delete that.

**Do:** Add `GET /api/history` (last 10 events) and `DELETE /api/history` (clears all events). Add a small "Recent outings" list with a "Clear history" button to the page. Insert text with `textContent` only.

**Done when:** API tests cover both endpoints, and clearing history makes the next prompt show no recent places.

## 4. Accessibility pass on the interface

**Why:** The page should work with a keyboard and a screen reader.

**Do:** Check keyboard order, visible focus, colour contrast, labels, and what is announced when results appear. Fix anything you find. Write down what you checked and what you changed in `docs/BUILD_LOG.md`.

**Done when:** every control is reachable and usable by keyboard alone, and the results and errors are announced.

## 5. Stretch: a pluggable event source

**Why:** The first idea included local events. The structure is already there to add them.

**Do:** Define a small `EventSource` protocol (given coordinates and a time window, return events with a name, place, start and end). Add a source that reads a hand-written `data/events.json` so it works offline. Extend filtering so an event only qualifies if it starts inside the free window and its location is reachable in time.

**Done when:** unit tests cover the time-window logic, and events appear as suggestions alongside places. Keep any paid or closed event API out of the default setup.
