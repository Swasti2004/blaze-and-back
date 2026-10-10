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

```
---
title: Touch Grass Planner: a local Gemma model that picks your next 30 minutes outside
published: false
tags: devchallenge, hf26challenge, opensource, ai
---

*This is a submission for the [Hacktoberfest Open-Source AI Challenge Week 1: Touch Grass](https://dev.to/challenges/hacktoberfest-week1-2026-10-05)*

## What I Built

[One or two sentences on the problem in your own words. For example: the hardest part of going outside is deciding where, and that decision is what sends people back to their phones.]

Touch Grass Planner takes three inputs: how many minutes you have, how much energy you have, and where you are. It looks up the weather and the parks, gardens, viewpoints and beaches nearby, and a local open-weight model picks the best fit and explains why in a sentence. You choose one, save a small outing card, and put the phone away.

It is for [who you built it for: students between classes, remote workers on a lunch break, ...].

## Demo

[Video or deployed link. Show the whole loop: set minutes and energy, get suggestions, pick one, save the card.]

## Code

[Embed the GitHub repo. Mention the repository was started on [date], inside the challenge window.]

## How I Built It

The model is [Gemma, tag/size] served locally by Ollama. The weather is from Open-Meteo and the places are from OpenStreetMap through the Overpass API. All three are open and need no API key. The server is FastAPI and the interface is a single page of plain HTML, CSS and JavaScript.

The design rule I cared about most: **rules decide what is possible, and the model decides what is good.** Thunderstorms, heavy rain, strong wind, extreme temperatures, darkness, and trips that do not fit the time or energy level are removed by ordinary, tested code before the model sees anything. The model only ranks places that can actually work, so a bad model reply cannot produce an unsafe suggestion.

The second rule: **never trust the model's output.** I ask Ollama for structured JSON, then check every suggestion against the list of places I sent. Invented places, malformed JSON and impossible durations are dropped. If nothing valid is left, the app falls back to a simple deterministic ranking and tells the person that it did. [Add what you saw: how often did a real model reply fail validation, and what did you change in the prompt?]

The app also remembers, locally, what you accepted, skipped and finished. If you have already done a lot that day, it leans toward easy options, and it avoids repeating places you visited in the last few days.

Testing: [N] automated tests cover the filters, the ranking, the output validation, the feedback store and the full API. They replace every outside service (weather, places, geocoding and the model) with a fake, so they run with no internet and no model. [Say what you checked by hand with the real services, and what you found.]

## Why Does Open Innovation Matter?

**Your location and your free time stay on your machine.** The model prompt, which includes your energy level, interests, recent outings and the places around you, is only ever sent to the Ollama server on your own computer. There is a test that checks the prompt goes nowhere else. The only things that leave are coordinates rounded to about 110 meters (for the weather and map lookups) and, if you type one, a town name. [If you checked this yourself, say how.]

**You can swap the model.** Changing one environment variable changes the model. I compared [models] on the same fixed scenarios and measured how often each returned a usable reply and how long it took on [your hardware]:

[Paste the table from scripts/compare_models.py.]

[One honest sentence on what the comparison showed.]

**It costs nothing per request.** [Your honest numbers: hardware, speed, any cost.]

**Where it was worse than a hosted model, honestly:** [Latency on your machine, quality of small-model replies, anything else you noticed.] And to be clear about the limits of "local": the weather and map lookups still need the internet, so this is local-first, not offline. The saved outing card is the part that works with no signal.

## Taking It Outside

[This section is where the bonus points are. Write what happened: where you went, how long it took, whether the suggestion was right, and whether the screen really was the shortest part of the experience.]

## My Agent Session

[Link or embed your sessions. Say which parts were built with which tool. The first commit, the scaffold, was generated with Claude outside Entire and Copilot. After that: ...]

## Prize Categories

- **Best Use of Gemma:** [How Gemma is used: runs locally through Ollama and does the ranking and explanation; mention the tag/size and your comparison.]
- **Best Use of Entire:** [How you captured and shared agent sessions, with links.]
- **Best Use of GitHub Copilot:** [Exactly how you used Copilot CLI, the coding agent, or Actions, and what it produced. Link the commits or pull requests.]
```
