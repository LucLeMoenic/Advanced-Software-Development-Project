const apiBase = "/itinerary-api";
const state = { trips: [], currentTrip: null };

const elements = {
  form: document.querySelector("#trip-form"), tripList: document.querySelector("#trip-list"),
  status: document.querySelector("#status"), empty: document.querySelector("#empty-state"),
  content: document.querySelector("#itinerary-content"), days: document.querySelector("#days"),
  dialog: document.querySelector("#stop-dialog"), stopForm: document.querySelector("#stop-form"),
};

async function api(path, options = {}) {
  const response = await fetch(`${apiBase}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  if (response.status === 204) return null;
  const body = await response.json();
  if (!response.ok) throw new Error(body.error?.message || "The request could not be completed.");
  return body;
}

function setStatus(message, isError = false) {
  elements.status.textContent = message;
  elements.status.style.background = isError ? "#f8e4de" : "";
}

async function loadTrips() {
  try {
    state.trips = await api("/trips");
    renderTripList();
  } catch (error) {
    elements.tripList.innerHTML = `<li class="muted">${escapeHtml(error.message)}</li>`;
  }
}

function renderTripList() {
  if (!state.trips.length) {
    elements.tripList.innerHTML = '<li class="muted">No saved trips yet.</li>';
    return;
  }
  elements.tripList.innerHTML = state.trips.map((trip) => `
    <li><button type="button" data-trip-id="${trip.id}">
      <strong>${escapeHtml(trip.destination)}</strong>
      <span>${escapeHtml(trip.startDate)} to ${escapeHtml(trip.endDate)}</span>
    </button></li>`).join("");
}

function renderTrip(trip) {
  state.currentTrip = trip;
  elements.empty.hidden = true;
  elements.content.hidden = false;
  document.querySelector("#trip-title").textContent = `${trip.destination} itinerary`;
  document.querySelector("#trip-dates").textContent = `${trip.startDate} to ${trip.endDate}`;
  document.querySelector("#trip-summary").textContent = `${trip.user} · AUD ${Number(trip.budget).toLocaleString()} · ${trip.interests || "Open interests"}`;
  const mode = trip.generationMode || "saved";
  document.querySelector("#generation-mode").textContent = mode === "fallback" ? "Reliable fallback" : mode;
  renderDays(trip.stops || []);
  const trace = trip.agentTrace || [];
  document.querySelector("#agent-trace").hidden = trace.length === 0;
  document.querySelector("#trace-list").innerHTML = trace.map((item) => `<li><strong>${escapeHtml(item.stage)}:</strong> ${escapeHtml(item.outcome)}</li>`).join("");
}

function renderDays(stops) {
  const grouped = stops.reduce((days, stop) => {
    (days[stop.day] ||= []).push(stop);
    return days;
  }, {});
  elements.days.innerHTML = Object.entries(grouped).sort(([a], [b]) => Number(a) - Number(b)).map(([day, items]) => `
    <section class="day" aria-labelledby="day-${day}">
      <h3 id="day-${day}">Day ${day}</h3>
      <div>${items.map((stop) => `
        <article class="stop">
          <h4>${escapeHtml(stop.activity)}</h4>
          <p>${escapeHtml(stop.notes || "No notes yet.")}</p>
          <div class="stop-actions">
            <button type="button" data-edit-stop="${stop.id}">Edit</button>
            <button type="button" data-regenerate-stop="${stop.id}">Regenerate</button>
            <button class="remove" type="button" data-remove-stop="${stop.id}">Remove</button>
          </div>
        </article>`).join("")}</div>
    </section>`).join("") || '<p class="muted">No stops yet. Add the first stop below.</p>';
}

function escapeHtml(value) {
  const span = document.createElement("span");
  span.textContent = String(value ?? "");
  return span.innerHTML;
}

elements.form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!elements.form.reportValidity()) return;
  const button = elements.form.querySelector("button[type=submit]");
  button.disabled = true;
  setStatus("Planning your itinerary...");
  try {
    const data = Object.fromEntries(new FormData(elements.form));
    data.budget = Number(data.budget);
    const trip = await api("/trips", { method: "POST", body: JSON.stringify(data) });
    renderTrip(trip);
    await loadTrips();
    setStatus(trip.generationMode === "fallback" ? "The AI was unavailable, so a reliable starter itinerary was created." : "Your itinerary is ready.");
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    button.disabled = false;
  }
});

elements.tripList.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-trip-id]");
  if (!button) return;
  try {
    renderTrip(await api(`/trips/${button.dataset.tripId}`));
    setStatus("Saved itinerary opened.");
  } catch (error) { setStatus(error.message, true); }
});

elements.days.addEventListener("click", async (event) => {
  const edit = event.target.closest("[data-edit-stop]");
  const regenerate = event.target.closest("[data-regenerate-stop]");
  const remove = event.target.closest("[data-remove-stop]");
  if (edit) {
    const stop = state.currentTrip.stops.find((item) => item.id === Number(edit.dataset.editStop));
    openStopDialog(stop);
  }
  if (regenerate) {
    try {
      setStatus("Regenerating this stop...");
      const result = await api(`/stops/${regenerate.dataset.regenerateStop}/regenerate`, { method: "POST" });
      await refreshCurrentTrip(result.generationMode === "fallback" ? "Stop regenerated with the reliable fallback." : "Stop regenerated.");
    } catch (error) { setStatus(error.message, true); }
  }
  if (remove && confirm("Remove this stop from the itinerary?")) {
    try {
      await api(`/stops/${remove.dataset.removeStop}`, { method: "DELETE" });
      await refreshCurrentTrip("Stop removed.");
    } catch (error) { setStatus(error.message, true); }
  }
});

function openStopDialog(stop = null) {
  document.querySelector("#stop-dialog-title").textContent = stop ? "Edit stop" : "Add a stop";
  document.querySelector("#stop-id").value = stop?.id || "";
  document.querySelector("#stop-day").value = stop?.day || 1;
  document.querySelector("#stop-activity").value = stop?.activity || "";
  document.querySelector("#stop-notes").value = stop?.notes || "";
  elements.dialog.showModal();
}

elements.stopForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!elements.stopForm.reportValidity()) return;
  const stopId = document.querySelector("#stop-id").value;
  const payload = {
    tripId: state.currentTrip.id,
    day: Number(document.querySelector("#stop-day").value),
    activity: document.querySelector("#stop-activity").value,
    notes: document.querySelector("#stop-notes").value,
    sortOrder: 99,
  };
  try {
    await api(stopId ? `/stops/${stopId}` : `/trips/${state.currentTrip.id}/stops`, { method: stopId ? "PUT" : "POST", body: JSON.stringify(payload) });
    elements.dialog.close();
    await refreshCurrentTrip(stopId ? "Stop updated." : "Stop added.");
  } catch (error) { setStatus(error.message, true); }
});

async function refreshCurrentTrip(message) {
  renderTrip(await api(`/trips/${state.currentTrip.id}`));
  setStatus(message);
}

document.querySelector("#add-stop").addEventListener("click", () => openStopDialog());
document.querySelector("#cancel-stop").addEventListener("click", () => elements.dialog.close());
document.querySelector("#refresh-trips").addEventListener("click", loadTrips);
document.querySelector("#regenerate-trip").addEventListener("click", async () => {
  if (!confirm("Replace all current stops with a new itinerary?")) return;
  try {
    setStatus("Regenerating the itinerary...");
    const result = await api(`/trips/${state.currentTrip.id}/regenerate`, { method: "POST" });
    state.currentTrip.stops = result.stops;
    state.currentTrip.generationMode = result.generationMode;
    renderTrip(state.currentTrip);
    setStatus("Itinerary regenerated.");
  } catch (error) { setStatus(error.message, true); }
});
document.querySelector("#delete-trip").addEventListener("click", async () => {
  if (!confirm("Delete this trip and every stop?")) return;
  try {
    await api(`/trips/${state.currentTrip.id}`, { method: "DELETE" });
    state.currentTrip = null;
    elements.content.hidden = true;
    elements.empty.hidden = false;
    await loadTrips();
    setStatus("Trip deleted.");
  } catch (error) { setStatus(error.message, true); }
});

window.addEventListener("load", loadTrips);