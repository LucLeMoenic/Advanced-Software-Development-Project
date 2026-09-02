const apiBase = "/itinerary-api";
const state = { trips: [], currentTrip: null, editingTripId: null };

const elements = {
  form: document.querySelector("#trip-form"), tripList: document.querySelector("#trip-list"),
  tripFilter: document.querySelector("#trip-filter"), tripCount: document.querySelector("#trip-count"),
  status: document.querySelector("#status"), empty: document.querySelector("#empty-state"),
  content: document.querySelector("#itinerary-content"), days: document.querySelector("#days"),
  dialog: document.querySelector("#stop-dialog"), stopForm: document.querySelector("#stop-form"),
  feedbackDialog: document.querySelector("#feedback-dialog"),
  feedbackTitle: document.querySelector("#feedback-title"), feedbackMessage: document.querySelector("#feedback-message"),
  feedbackCancel: document.querySelector("#feedback-cancel"), feedbackConfirm: document.querySelector("#feedback-confirm"),
};

let resolveFeedback = null;
let feedbackFocusTarget = null;

function openFeedback({ kind, title, message, confirmLabel = "OK", cancelLabel = "" }, focusTarget = null) {
  if (resolveFeedback) closeFeedback(false);
  elements.feedbackDialog.dataset.kind = kind;
  elements.feedbackTitle.textContent = title;
  elements.feedbackMessage.textContent = message;
  elements.feedbackConfirm.textContent = confirmLabel;
  elements.feedbackCancel.textContent = cancelLabel;
  elements.feedbackCancel.hidden = !cancelLabel;
  feedbackFocusTarget = focusTarget;
  elements.feedbackDialog.showModal();
  elements.feedbackConfirm.focus();
  return new Promise((resolve) => { resolveFeedback = resolve; });
}

function closeFeedback(result) {
  elements.feedbackDialog.close();
  const resolve = resolveFeedback;
  const focusTarget = feedbackFocusTarget;
  resolveFeedback = null;
  feedbackFocusTarget = null;
  resolve?.(result);
  if (focusTarget) focusTarget.focus();
}

function showError(message) {
  setStatus("");
  return openFeedback({ kind: "error", title: "Something went wrong", message });
}

function confirmAction(title, message, confirmLabel) {
  return openFeedback({ kind: "confirm", title, message, confirmLabel, cancelLabel: "Cancel" });
}

function validateForm(form) {
  if (form.checkValidity()) return true;
  const field = [...form.elements].find((element) => element.willValidate && !element.validity.valid);
  const label = field?.labels?.[0]?.textContent || "This field";
  let message = `${label} needs a valid value.`;
  if (field?.validity.valueMissing) message = `${label} is required.`;
  else if (field?.validity.rangeUnderflow) message = `${label} must be at least ${field.min}.`;
  else if (field?.validity.rangeOverflow) message = `${label} must be no more than ${field.max}.`;
  openFeedback({ kind: "validation", title: "Check details", message }, field);
  return false;
}

async function api(path, options = {}) {
  const response = await fetch(`${apiBase}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  if (response.status === 204) return null;
  const body = await response.json();
  if (!response.ok) {
    const fieldMessage = Object.values(body.error?.fields || {})[0];
    throw new Error(fieldMessage || body.error?.message || "The request could not be completed.");
  }
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
    showError(error.message);
  }
}

function renderTripList() {
  const query = elements.tripFilter.value.trim().toLocaleLowerCase();
  const trips = state.trips.filter((trip) =>
    [trip.destination, trip.user].some((value) => String(value || "").toLocaleLowerCase().includes(query))
  );
  elements.tripCount.textContent = query
    ? `${trips.length} of ${state.trips.length} trips`
    : `${state.trips.length} saved ${state.trips.length === 1 ? "trip" : "trips"}`;
  if (!state.trips.length) {
    elements.tripList.innerHTML = '<li class="muted">No saved trips yet.</li>';
    return;
  }
  if (!trips.length) {
    elements.tripList.innerHTML = '<li class="muted">No trips match this filter.</li>';
    return;
  }
  elements.tripList.innerHTML = trips.map((trip) => `
    <li><button type="button" data-trip-id="${trip.id}">
      <span class="trip-name">${escapeHtml(trip.destination)}</span>
      <span class="trip-list-dates">${escapeHtml(trip.startDate)} to ${escapeHtml(trip.endDate)}</span>
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
  const stops = trip.stops || [];
  renderMetrics(trip, stops);
  renderDays(stops);
  const trace = trip.agentTrace || [];
  document.querySelector("#agent-trace").hidden = trace.length === 0;
  document.querySelector("#trace-list").innerHTML = trace.map((item) => `<li><span class="trace-stage">${escapeHtml(item.stage)}:</span> ${escapeHtml(item.outcome)}</li>`).join("");
}

function renderMetrics(trip, stops) {
  const dayCount = Math.round((new Date(trip.endDate) - new Date(trip.startDate)) / 86400000) + 1;
  const plannedDays = new Set(stops.map((stop) => stop.day)).size;
  document.querySelector("#metric-duration").textContent = `${dayCount} ${dayCount === 1 ? "day" : "days"}`;
  document.querySelector("#metric-stops").textContent = String(stops.length);
  document.querySelector("#metric-budget").textContent = `AUD ${(Number(trip.budget) / dayCount).toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
  document.querySelector("#metric-days").textContent = `${plannedDays} / ${dayCount}`;
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
          <div class="stop-heading">
            <h4>${escapeHtml(stop.activity)}</h4>
            <details class="action-menu stop-action-menu">
              <summary aria-label="Stop actions" title="Stop actions"><span aria-hidden="true">&#8230;</span></summary>
              <div class="action-menu-items">
                <button type="button" data-edit-stop="${stop.id}">Edit</button>
                <button type="button" data-duplicate-stop="${stop.id}">Duplicate</button>
                <button type="button" data-regenerate-stop="${stop.id}">Regenerate</button>
                <button class="danger-action" type="button" data-remove-stop="${stop.id}">Remove</button>
              </div>
            </details>
          </div>
          <p>${escapeHtml(stop.notes || "No notes yet.")}</p>
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
  if (!validateForm(elements.form)) return;
  const button = elements.form.querySelector("button[type=submit]");
  button.disabled = true;
  setStatus("Planning your itinerary...");
  try {
    const data = Object.fromEntries(new FormData(elements.form));
    data.budget = Number(data.budget);
    const editingTripId = state.editingTripId;
    let trip;
    if (editingTripId) {
      await api(`/trips/${editingTripId}`, { method: "PUT", body: JSON.stringify(data) });
      trip = await api(`/trips/${editingTripId}`);
      resetTripForm();
    } else {
      trip = await api("/trips", { method: "POST", body: JSON.stringify(data) });
    }
    renderTrip(trip);
    await loadTrips();
    setStatus(editingTripId
      ? "Trip details updated."
      : trip.generationMode === "fallback"
        ? "The AI was unavailable, so a reliable starter itinerary was created."
        : "Your itinerary is ready.");
  } catch (error) {
    showError(error.message);
  } finally {
    button.disabled = false;
  }
});

elements.tripList.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-trip-id]");
  if (!button) return;
  try {
    renderTrip(await api(`/trips/${button.dataset.tripId}`));
    resetTripForm();
    setStatus("Saved itinerary opened.");
  } catch (error) { showError(error.message); }
});

elements.days.addEventListener("click", async (event) => {
  const edit = event.target.closest("[data-edit-stop]");
  const duplicate = event.target.closest("[data-duplicate-stop]");
  const regenerate = event.target.closest("[data-regenerate-stop]");
  const remove = event.target.closest("[data-remove-stop]");
  if (edit) {
    const stop = state.currentTrip.stops.find((item) => item.id === Number(edit.dataset.editStop));
    openStopDialog(stop);
  }
  if (duplicate) {
    const stop = state.currentTrip.stops.find((item) => item.id === Number(duplicate.dataset.duplicateStop));
    try {
      await api(`/trips/${state.currentTrip.id}/stops`, {
        method: "POST",
        body: JSON.stringify({
          tripId: state.currentTrip.id,
          day: stop.day,
          activity: `${stop.activity} (copy)`.slice(0, 160),
          notes: stop.notes,
          sortOrder: Math.max(0, ...state.currentTrip.stops.filter((item) => item.day === stop.day).map((item) => item.sortOrder || 0)) + 1,
        }),
      });
      await refreshCurrentTrip("Stop duplicated.");
    } catch (error) { showError(error.message); }
  }
  if (regenerate) {
    try {
      setStatus("Regenerating this stop...");
      const result = await api(`/stops/${regenerate.dataset.regenerateStop}/regenerate`, { method: "POST" });
      await refreshCurrentTrip(result.generationMode === "fallback" ? "Stop regenerated with the reliable fallback." : "Stop regenerated.");
    } catch (error) { showError(error.message); }
  }
  if (remove && await confirmAction("Remove stop?", "This stop will be removed from the itinerary.", "Remove stop")) {
    try {
      await api(`/stops/${remove.dataset.removeStop}`, { method: "DELETE" });
      await refreshCurrentTrip("Stop removed.");
    } catch (error) { showError(error.message); }
  }
});

function openStopDialog(stop = null) {
  document.querySelector("#stop-dialog-title").textContent = stop ? "Edit stop" : "Add a stop";
  document.querySelector("#stop-id").value = stop?.id || "";
  const stopDay = document.querySelector("#stop-day");
  const dayCount = Math.round((new Date(state.currentTrip.endDate) - new Date(state.currentTrip.startDate)) / 86400000) + 1;
  stopDay.max = String(dayCount);
  stopDay.value = stop?.day || 1;
  document.querySelector("#stop-activity").value = stop?.activity || "";
  document.querySelector("#stop-notes").value = stop?.notes || "";
  elements.dialog.showModal();
}

elements.stopForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!validateForm(elements.stopForm)) return;
  const stopId = document.querySelector("#stop-id").value;
  const existingStop = state.currentTrip.stops.find((stop) => stop.id === Number(stopId));
  const day = Number(document.querySelector("#stop-day").value);
  const payload = {
    day,
    activity: document.querySelector("#stop-activity").value,
    notes: document.querySelector("#stop-notes").value,
    sortOrder: existingStop?.sortOrder
      ?? Math.max(-1, ...state.currentTrip.stops.filter((stop) => stop.day === day).map((stop) => stop.sortOrder)) + 1,
  };
  try {
    await api(stopId ? `/stops/${stopId}` : `/trips/${state.currentTrip.id}/stops`, { method: stopId ? "PUT" : "POST", body: JSON.stringify(payload) });
    elements.dialog.close();
    await refreshCurrentTrip(stopId ? "Stop updated." : "Stop added.");
  } catch (error) { showError(error.message); }
});

async function refreshCurrentTrip(message) {
  renderTrip(await api(`/trips/${state.currentTrip.id}`));
  setStatus(message);
}

function beginTripEdit() {
  const trip = state.currentTrip;
  if (!trip) return;
  document.querySelector("#trip-composer").open = true;
  state.editingTripId = trip.id;
  elements.form.elements.user.value = trip.user;
  elements.form.elements.destination.value = trip.destination;
  elements.form.elements.startDate.value = trip.startDate;
  elements.form.elements.endDate.value = trip.endDate;
  elements.form.elements.budget.value = trip.budget;
  elements.form.elements.interests.value = trip.interests || "";
  document.querySelector("#trip-form-kicker").textContent = "Revise journey";
  document.querySelector("#trip-form-title").textContent = "Edit trip details";
  document.querySelector("#trip-form-summary").textContent = `${trip.destination} · ${trip.startDate} to ${trip.endDate}`;
  document.querySelector("#trip-submit").textContent = "Save trip";
  document.querySelector("#cancel-trip-edit").hidden = false;
  elements.form.elements.user.focus();
}

function resetTripForm() {
  state.editingTripId = null;
  elements.form.reset();
  document.querySelector("#trip-form-kicker").textContent = "New journey";
  document.querySelector("#trip-form-title").textContent = "Trip details";
  document.querySelector("#trip-form-summary").textContent = "Set the destination, dates, budget, and interests.";
  document.querySelector("#trip-submit").textContent = "Generate itinerary";
  document.querySelector("#cancel-trip-edit").hidden = true;
}

document.querySelector("#add-stop").addEventListener("click", () => openStopDialog());
document.querySelector("#cancel-stop").addEventListener("click", () => elements.dialog.close());
document.querySelector("#edit-trip").addEventListener("click", beginTripEdit);
document.querySelector("#cancel-trip-edit").addEventListener("click", resetTripForm);
document.querySelector("#refresh-trips").addEventListener("click", loadTrips);
elements.tripFilter.addEventListener("input", renderTripList);
elements.feedbackConfirm.addEventListener("click", () => closeFeedback(true));
elements.feedbackCancel.addEventListener("click", () => closeFeedback(false));
elements.feedbackDialog.addEventListener("cancel", (event) => {
  event.preventDefault();
  closeFeedback(false);
});
document.addEventListener("click", (event) => {
  const selectedAction = event.target.closest(".action-menu-items button");
  if (selectedAction) selectedAction.closest(".action-menu").removeAttribute("open");
  document.querySelectorAll(".action-menu[open]").forEach((menu) => {
    if (!menu.contains(event.target)) menu.removeAttribute("open");
  });
});
document.querySelector("#print-trip").addEventListener("click", () => window.print());
document.querySelector("#regenerate-trip").addEventListener("click", async () => {
  if (!await confirmAction("Regenerate itinerary?", "Every current stop will be replaced with a newly generated itinerary.", "Regenerate")) return;
  try {
    setStatus("Regenerating the itinerary...");
    const result = await api(`/trips/${state.currentTrip.id}/regenerate`, { method: "POST" });
    state.currentTrip.stops = result.stops;
    state.currentTrip.generationMode = result.generationMode;
    renderTrip(state.currentTrip);
    setStatus("Itinerary regenerated.");
  } catch (error) { showError(error.message); }
});
document.querySelector("#delete-trip").addEventListener("click", async () => {
  if (!await confirmAction("Delete trip?", "This trip and every stop in it will be permanently deleted.", "Delete trip")) return;
  try {
    await api(`/trips/${state.currentTrip.id}`, { method: "DELETE" });
    if (state.editingTripId === state.currentTrip.id) resetTripForm();
    state.currentTrip = null;
    elements.content.hidden = true;
    elements.empty.hidden = false;
    await loadTrips();
    setStatus("Trip deleted.");
  } catch (error) { showError(error.message); }
});

window.addEventListener("load", loadTrips);