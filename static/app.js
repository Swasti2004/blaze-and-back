// Touch Grass Planner front end. No libraries, no build step.
// All text from the server is inserted with textContent, never innerHTML.

"use strict";

const $ = (id) => document.getElementById(id);

const state = {
  coords: null, // {lat, lon} once the browser location is granted
  current: null, // the suggestion the person picked
  busy: false,
};

const CATEGORY_LABEL = {
  park: "Park",
  garden: "Garden",
  nature: "Nature reserve",
  viewpoint: "Viewpoint",
  peak: "Peak",
  beach: "Beach",
};
const EFFORT_LABEL = { easy: "Easy", moderate: "Moderate", active: "Active" };

function el(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (key === "className") node.className = value;
    else if (key === "dataset") Object.assign(node.dataset, value);
    else node.setAttribute(key, value);
  }
  for (const child of children) {
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}

function showError(message) {
  const box = $("error");
  box.textContent = message;
  box.hidden = !message;
  if (message) {
    box.tabIndex = -1;
    box.focus();
    box.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
}

// ---------- model status ----------
async function checkHealth() {
  const status = $("engine-status");
  try {
    const res = await fetch("/api/health");
    const data = await res.json();
    if (data.ollama && data.model_available) {
      status.textContent = `Local model ready: ${data.model}.`;
      status.dataset.state = "ready";
    } else if (data.ollama) {
      status.textContent = `Model not found. Run: ollama pull ${data.model}`;
      status.dataset.state = "warn";
    } else {
      status.textContent = "Ollama is not running, so suggestions will use simple rules.";
      status.dataset.state = "warn";
    }
  } catch {
    status.textContent = "Cannot reach the app server.";
    status.dataset.state = "warn";
  }
}

// ---------- form controls ----------
$("minutes").addEventListener("input", (event) => {
  $("minutes-out").textContent = event.target.value;
});

$("place").addEventListener("input", () => {
  // Typing a place replaces a previously detected location.
  if ($("place").value.trim()) {
    state.coords = null;
    $("locate-status").textContent = "";
  }
});

$("locate").addEventListener("click", () => {
  const out = $("locate-status");
  if (!window.isSecureContext || !navigator.geolocation) {
    out.textContent = "Location needs https or localhost. Type a town or city instead.";
    return;
  }
  out.textContent = "Finding your location.";
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      state.coords = { lat: pos.coords.latitude, lon: pos.coords.longitude };
      $("place").value = "";
      out.textContent = "Location set.";
    },
    () => {
      state.coords = null;
      out.textContent = "Could not get your location. Type a town or city instead.";
    },
    { enableHighAccuracy: false, timeout: 10000, maximumAge: 300000 }
  );
});

function readForm() {
  const interests = [...document.querySelectorAll('input[name="interest"]:checked')].map((i) => i.value);
  const custom = $("custom-interests") ? $("custom-interests").value.trim() : "";
  if (custom) {
    for (const part of custom.split(",")) {
      const clean = part.trim().toLowerCase();
      if (clean && !interests.includes(clean)) {
        interests.push(clean);
      }
    }
  }

  const body = {
    minutes: Number($("minutes").value),
    energy: document.querySelector('input[name="energy"]:checked').value,
    interests: interests.slice(0, 8),
  };
  if (state.coords) {
    body.lat = state.coords.lat;
    body.lon = state.coords.lon;
  } else {
    body.place = $("place").value.trim();
  }
  return body;
}

function describeError(data) {
  const detail = data && data.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length) {
    return "Check the form: " + detail.map((d) => d.msg).join(" ");
  }
  return "Something went wrong. Try again.";
}

function setBusy(busy) {
  state.busy = busy;
  const button = $("go");
  const surprise = $("surprise");
  button.disabled = busy;
  if (surprise) surprise.disabled = busy;
  button.textContent = busy ? "Asking the local model. This can take up to a minute." : "Find somewhere outside";
}

async function requestSuggestions(overrideInterests = null) {
  if (state.busy) return;
  showError("");
  const body = readForm();
  if (overrideInterests) {
    body.interests = overrideInterests;
  }
  if (!state.coords && !body.place) {
    showError("Use your location or type a town or city first.");
    return;
  }
  setBusy(true);
  $("outing").hidden = true;
  try {
    const res = await fetch("/api/suggest", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json().catch(() => null);
    if (!res.ok) {
      showError(describeError(data));
      return;
    }
    renderResults(data);
  } catch {
    showError("Could not reach the app server. Is it still running?");
  } finally {
    setBusy(false);
  }
}

$("plan-form").addEventListener("submit", (event) => {
  event.preventDefault();
  requestSuggestions();
});

const SURPRISE_THEMES = [
  ["hidden gem", "surprise", "curiosity"],
  ["peaceful escape", "views", "nature"],
  ["micro-adventure", "explore", "scenic"],
  ["quiet corner", "greenery", "fresh air"],
  ["scenic stroll", "water", "views"],
];

const surpriseBtn = $("surprise");
if (surpriseBtn) {
  surpriseBtn.addEventListener("click", () => {
    const pick = SURPRISE_THEMES[Math.floor(Math.random() * SURPRISE_THEMES.length)];
    requestSuggestions(pick);
  });
}

// ---------- results ----------
function weatherLine(w) {
  if (!w) return "";
  const sentence = w.summary.charAt(0).toUpperCase() + w.summary.slice(1);
  return `${sentence}, ${Math.round(w.temperature_c)}°C (feels like ${Math.round(w.feels_like_c)}°C), ` +
    `${w.rain_chance_pct}% chance of rain in the next few hours.`;
}

function renderResults(data) {
  const section = $("results");
  section.hidden = false;
  $("weather-line").textContent = weatherLine(data.weather);

  const notes = $("notes");
  notes.replaceChildren();
  for (const note of data.notes) notes.append(el("li", {}, note));
  if (data.engine === "llm") {
    notes.append(el("li", {}, `Picked by ${data.model}, running on this machine.`));
  }

  const list = $("suggestions");
  list.replaceChildren();
  for (const s of data.suggestions) list.append(renderSuggestion(s));
  const heading = $("results-heading");
  if (heading) {
    heading.focus();
    heading.scrollIntoView({ behavior: "smooth", block: "start" });
  } else {
    section.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

function renderSuggestion(s) {
  const item = el("li", { className: "suggestion" });
  item.append(el("div", { className: "blaze", dataset: { effort: s.effort }, "aria-hidden": "true" }));

  const body = el("div");
  body.append(
    el("h3", {}, s.place_name),
    el("p", { className: "kind" }, CATEGORY_LABEL[s.category] || "Outdoor place"),
    el("p", {}, s.activity + "."),
    el("p", { className: "reason" }, s.reason)
  );
  body.append(
    el(
      "dl",
      { className: "facts" },
      el("div", {}, el("dt", {}, "Walk"), el("dd", {}, `${s.walk_minutes} min each way`)),
      el("div", {}, el("dt", {}, "Stay"), el("dd", {}, `${s.duration_minutes} min`)),
      el("div", {}, el("dt", {}, "Effort"), el("dd", {}, EFFORT_LABEL[s.effort]))
    )
  );

  const take = el("button", { type: "button", className: "primary" }, "Take this one");
  const skip = el("button", { type: "button", className: "secondary" }, "Skip");
  take.addEventListener("click", () => chooseSuggestion(s, item));
  skip.addEventListener("click", () => {
    sendFeedback(s, "skipped");
    item.remove();
  });
  body.append(el("div", { className: "actions" }, take, skip));
  item.append(body);
  return item;
}

// ---------- outing card ----------
function backByTime(s) {
  const minutes = 2 * s.walk_minutes + s.duration_minutes;
  return new Date(Date.now() + minutes * 60000).toLocaleTimeString([], {
    hour: "numeric",
    minute: "2-digit",
  });
}

function planText(s) {
  return (
    `Walk about ${s.walk_minutes} minutes to ${s.place_name}, stay about ${s.duration_minutes} minutes, ` +
    `then walk back. ${s.activity}. Be home by ${backByTime(s)}.`
  );
}

function chooseSuggestion(s, item) {
  state.current = s;
  for (const other of document.querySelectorAll(".suggestion.chosen")) other.classList.remove("chosen");
  item.classList.add("chosen");
  sendFeedback(s, "accepted");

  $("outing-plan").textContent = planText(s);
  $("outing-coords").textContent = `Coordinates: ${s.lat}, ${s.lon}`;
  $("open-map").href = s.osm_url;
  $("outing-status").textContent = "";
  $("mark-done").disabled = false;
  $("outing").hidden = false;
  $("outing").scrollIntoView({ behavior: "smooth", block: "start" });
}

function escapeHtml(text) {
  return String(text).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// A self-contained page with no scripts or network needs, so it opens with no signal.
function buildCardHtml(s) {
  return `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Outing: ${escapeHtml(s.place_name)}</title>
<style>
body{font-family:system-ui,Segoe UI,Arial,sans-serif;margin:0;padding:1.5rem;background:#edf2ee;color:#15262b;line-height:1.5;font-size:1.125rem}
main{max-width:30rem;margin:0 auto;border:2px solid #15262b;background:#fff;padding:1.25rem}
h1{margin:0 0 .5rem;font-size:1.5rem}
.blaze{display:inline-block;width:.75rem;height:1.75rem;border:2px solid #15262b;border-radius:2px;vertical-align:middle;margin-right:.5rem;background:${{ easy: "#2b6cde", moderate: "#e9b91e", active: "#cf3f2e" }[s.effort] || "#2b6cde"}}
small{color:#4a5f66}
</style></head><body><main>
<h1><span class="blaze"></span>${escapeHtml(s.place_name)}</h1>
<p>${escapeHtml(planText(s))}</p>
<p><small>Why: ${escapeHtml(s.reason)}</small></p>
<p><small>Coordinates: ${escapeHtml(s.lat)}, ${escapeHtml(s.lon)}<br>Map: ${escapeHtml(s.osm_url)}</small></p>
</main></body></html>`;
}

function slug(text) {
  return text.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 40) || "outing";
}

$("save-card").addEventListener("click", () => {
  const s = state.current;
  if (!s) return;
  const blob = new Blob([buildCardHtml(s)], { type: "text/html" });
  const url = URL.createObjectURL(blob);
  const link = el("a", { href: url, download: `outing-${slug(s.place_name)}.html` });
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  $("outing-status").textContent = "Card saved. Open it from your downloads with no signal.";
});

$("mark-done").addEventListener("click", () => {
  const s = state.current;
  if (!s) return;
  sendFeedback(s, "done");
  $("mark-done").disabled = true;
  $("outing-status").textContent = "Logged on this machine. Future suggestions will take it into account.";
});

// ---------- feedback ----------
function sendFeedback(s, action) {
  fetch("/api/feedback", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      place_id: s.place_id,
      place_name: s.place_name,
      category: s.category,
      action,
      effort: s.effort,
      duration_minutes: s.duration_minutes,
    }),
  }).catch(() => {
    /* Feedback is best effort; the app keeps working without it. */
  });
}

// ---------- history ----------
async function loadHistory() {
  const list = $("history-list");
  const empty = $("history-empty");
  try {
    const res = await fetch("/api/history");
    const data = await res.json();
    const events = data.events || [];
    list.replaceChildren();
    if (events.length === 0) {
      empty.hidden = false;
    } else {
      empty.hidden = true;
      for (const ev of events) {
        const item = el(
          "li",
          { className: "history-item" },
          el("strong", {}, ev.place_name),
          el("span", { className: "history-meta" }, ` - ${ev.action} (${ev.category || "place"}, ${ev.duration_minutes || 0}m)`)
        );
        list.append(item);
      }
    }
  } catch {
    /* History fetching is best effort. */
  }
}

$("clear-history").addEventListener("click", async () => {
  try {
    await fetch("/api/history", { method: "DELETE" });
    await loadHistory();
  } catch {
    /* Best effort */
  }
});

// Refresh history on done action
const origSendFeedback = sendFeedback;
sendFeedback = function(s, action) {
  origSendFeedback(s, action);
  setTimeout(loadHistory, 300);
};

checkHealth();
loadHistory();
