<script setup>
import { computed, nextTick, onMounted, onUnmounted, reactive, ref } from "vue";

const trips = ref([]);
const currentTrip = ref(null);
const editingTripId = ref(null);
const tripFilter = ref("");
const tripsLoading = ref(true);
const tripsError = ref("");
const status = ref("");
const tripBusy = ref(false);
const stopBusy = ref(false);
const composer = ref(null);
const tripForm = ref(null);
const stopDialog = ref(null);
const feedbackDialog = ref(null);
const feedbackConfirm = ref(null);
const emptyTrip = () => ({ user: "", destination: "", startDate: "", endDate: "", budget: "", interests: "" });
const tripDraft = reactive(emptyTrip());
const stopDraft = reactive({ id: "", day: 1, activity: "", notes: "" });
const feedback = reactive({ kind: "", title: "", message: "", confirmLabel: "OK", cancelLabel: "" });
const integrations = reactive({ capabilities: {}, summaryVersion: 0, adviceVersion: 0, summaryBusy: false, adviceBusy: false });
const summary = ref(null);
const summaryStatus = ref("MCP is disabled.");
const advice = ref(null);
const adviceQuestion = ref("");
const adviceStatus = ref("RAG is disabled.");
const capabilitiesFailed = ref(false);
let resolveFeedback = null;
let feedbackFocusTarget = null;

const filteredTrips = computed(() => {
  const query = tripFilter.value.trim().toLocaleLowerCase();
  return trips.value.filter((trip) => [trip.destination, trip.user].some((value) => String(value || "").toLocaleLowerCase().includes(query)));
});
const tripCount = computed(() => tripFilter.value.trim()
  ? `${filteredTrips.value.length} of ${trips.value.length} trips`
  : `${trips.value.length} saved ${trips.value.length === 1 ? "trip" : "trips"}`);
const stops = computed(() => currentTrip.value?.stops || []);
const dayCount = computed(() => currentTrip.value
  ? Math.round((new Date(currentTrip.value.endDate) - new Date(currentTrip.value.startDate)) / 86400000) + 1 : 0);
const plannedDays = computed(() => new Set(stops.value.map((stop) => stop.day)).size);
const dailyBudget = computed(() => (Number(currentTrip.value?.budget) / dayCount.value).toLocaleString(undefined, { maximumFractionDigits: 2 }));
const days = computed(() => {
  const grouped = {};
  for (const stop of stops.value) (grouped[stop.day] ||= []).push(stop);
  return Object.entries(grouped).sort(([first], [second]) => Number(first) - Number(second));
});
const summaryMetrics = computed(() => summary.value ? [
  ["Stops", summary.value.stopCount],
  ["Planned days", `${summary.value.plannedDayCount} / ${summary.value.dayCount}`],
  ["Unplanned days", summary.value.unplannedDays.join(", ") || "None"],
  ["Daily allocation (AUD)", Number(summary.value.dailyBudgetAllocation).toFixed(2)],
] : []);

function openFeedback({ kind, title, message, confirmLabel = "OK", cancelLabel = "" }, focusTarget = null) {
  if (resolveFeedback) closeFeedback(false);
  Object.assign(feedback, { kind, title, message, confirmLabel, cancelLabel });
  feedbackFocusTarget = focusTarget || document.activeElement;
  feedbackDialog.value.showModal();
  nextTick(() => feedbackConfirm.value?.focus());
  return new Promise((resolve) => { resolveFeedback = resolve; });
}

function closeFeedback(result) {
  feedbackDialog.value?.close();
  const resolve = resolveFeedback;
  const focusTarget = feedbackFocusTarget;
  resolveFeedback = null;
  feedbackFocusTarget = null;
  resolve?.(result);
  focusTarget?.focus();
}

function showError(message) {
  status.value = "";
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
  const response = await fetch(`/itinerary-api${path}`, {
    ...options, headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  if (response.ok && ["POST", "PUT", "DELETE"].includes(options.method) && !path.endsWith("/mcp-summary") && path !== "/itinerary-advice") invalidateSummary();
  if (response.status === 204) return null;
  const body = await response.json();
  if (!response.ok) throw new Error(Object.values(body.error?.fields || {})[0] || body.error?.message || "The request could not be completed.");
  return body;
}

function invalidateSummary() {
  integrations.summaryVersion++;
  integrations.summaryBusy = false;
  summary.value = null;
  summaryStatus.value = integrations.capabilities.mcpEnabled ? "" : "MCP is disabled.";
}

async function loadCapabilities() {
  try {
    const capabilities = await api("/capabilities");
    if (!["aiEnabled", "mcpEnabled", "ragEnabled"].every((name) => typeof capabilities[name] === "boolean")) throw new Error("Could not read service availability.");
    integrations.capabilities = capabilities;
    summaryStatus.value = capabilities.mcpEnabled ? "" : "MCP is disabled.";
    adviceStatus.value = capabilities.ragEnabled ? "" : "RAG is disabled.";
    capabilitiesFailed.value = false;
  } catch {
    integrations.capabilities = {};
    adviceStatus.value = "Could not read service availability.";
    capabilitiesFailed.value = true;
  }
}

async function inspectTrip() {
  if (integrations.summaryBusy || !currentTrip.value || !integrations.capabilities.mcpEnabled) return;
  const tripId = currentTrip.value.id;
  const version = ++integrations.summaryVersion;
  integrations.summaryBusy = true;
  summary.value = null;
  summaryStatus.value = "Inspecting saved itinerary...";
  try {
    const result = await api(`/trips/${tripId}/mcp-summary`, { method: "POST", signal: AbortSignal.timeout(10000) });
    if (version !== integrations.summaryVersion || currentTrip.value?.id !== tripId) return;
    summary.value = result.summary;
    summaryStatus.value = "Saved itinerary inspected.";
  } catch (error) {
    if (version === integrations.summaryVersion) summaryStatus.value = error.name === "TimeoutError" ? "The summary request timed out." : error.message;
  } finally {
    if (version === integrations.summaryVersion) integrations.summaryBusy = false;
  }
}

async function askAdvice() {
  if (integrations.adviceBusy || !integrations.capabilities.ragEnabled) return;
  const question = adviceQuestion.value.trim();
  if (!question) return;
  const version = ++integrations.adviceVersion;
  integrations.adviceBusy = true;
  advice.value = null;
  adviceStatus.value = "Retrieving planning advice...";
  try {
    const result = await api("/itinerary-advice", { method: "POST", body: JSON.stringify({ question }), signal: AbortSignal.timeout(35000) });
    if (version !== integrations.adviceVersion) return;
    advice.value = result;
    adviceStatus.value = result.confidence === "insufficient" ? "Insufficient context." : "Planning advice received.";
  } catch (error) {
    if (version === integrations.adviceVersion) adviceStatus.value = error.name === "TimeoutError" ? "The advice request timed out." : error.message;
  } finally {
    if (version === integrations.adviceVersion) integrations.adviceBusy = false;
  }
}

async function loadTrips() {
  tripsLoading.value = true;
  tripsError.value = "";
  try { trips.value = await api("/trips"); }
  catch (error) { tripsError.value = error.message; showError(error.message); }
  finally { tripsLoading.value = false; }
}

function selectTrip(trip) {
  currentTrip.value = trip;
  invalidateSummary();
}

function resetTripForm() {
  editingTripId.value = null;
  Object.assign(tripDraft, emptyTrip());
}

async function submitTrip(event) {
  if (tripBusy.value || !validateForm(event.target)) return;
  tripBusy.value = true;
  status.value = "Planning your itinerary...";
  try {
    const data = { ...tripDraft, budget: Number(tripDraft.budget) };
    const tripId = editingTripId.value;
    let trip;
    if (tripId) {
      await api(`/trips/${tripId}`, { method: "PUT", body: JSON.stringify(data) });
      trip = await api(`/trips/${tripId}`);
      resetTripForm();
    } else trip = await api("/trips", { method: "POST", body: JSON.stringify(data) });
    selectTrip(trip);
    await loadTrips();
    status.value = tripId ? "Trip details updated." : trip.generationMode === "fallback"
      ? "The AI was unavailable, so a reliable starter itinerary was created." : "Your itinerary is ready.";
  } catch (error) { showError(error.message); }
  finally { tripBusy.value = false; }
}

async function openTrip(tripId) {
  invalidateSummary();
  try {
    selectTrip(await api(`/trips/${tripId}`));
    resetTripForm();
    status.value = "Saved itinerary opened.";
  } catch (error) { showError(error.message); }
}

async function refreshCurrentTrip(message) {
  selectTrip(await api(`/trips/${currentTrip.value.id}`));
  status.value = message;
}

function beginTripEdit() {
  const trip = currentTrip.value;
  if (!trip) return;
  composer.value.open = true;
  editingTripId.value = trip.id;
  for (const field of Object.keys(emptyTrip())) tripDraft[field] = trip[field] ?? "";
  nextTick(() => tripForm.value.elements.user.focus());
}

function openStopDialog(stop = null) {
  Object.assign(stopDraft, { id: stop?.id || "", day: stop?.day || 1, activity: stop?.activity || "", notes: stop?.notes || "" });
  stopDialog.value.showModal();
}

async function saveStop(event) {
  if (stopBusy.value || !validateForm(event.target)) return;
  stopBusy.value = true;
  const stopId = stopDraft.id;
  const existingStop = stops.value.find((stop) => stop.id === Number(stopId));
  const day = Number(stopDraft.day);
  const payload = {
    day, activity: stopDraft.activity, notes: stopDraft.notes,
    sortOrder: existingStop?.sortOrder ?? Math.max(-1, ...stops.value.filter((stop) => stop.day === day).map((stop) => stop.sortOrder)) + 1,
  };
  try {
    await api(stopId ? `/stops/${stopId}` : `/trips/${currentTrip.value.id}/stops`, { method: stopId ? "PUT" : "POST", body: JSON.stringify(payload) });
    stopDialog.value.close();
    await refreshCurrentTrip(stopId ? "Stop updated." : "Stop added.");
  } catch (error) { showError(error.message); }
  finally { stopBusy.value = false; }
}

async function duplicateStop(stop) {
  try {
    await api(`/trips/${currentTrip.value.id}/stops`, { method: "POST", body: JSON.stringify({
      tripId: currentTrip.value.id, day: stop.day, activity: `${stop.activity} (copy)`.slice(0, 160), notes: stop.notes,
      sortOrder: Math.max(0, ...stops.value.filter((item) => item.day === stop.day).map((item) => item.sortOrder || 0)) + 1,
    }) });
    await refreshCurrentTrip("Stop duplicated.");
  } catch (error) { showError(error.message); }
}

async function regenerateStop(stop) {
  try {
    status.value = "Regenerating this stop...";
    const result = await api(`/stops/${stop.id}/regenerate`, { method: "POST" });
    await refreshCurrentTrip(result.generationMode === "fallback" ? "Stop regenerated with the reliable fallback." : "Stop regenerated.");
  } catch (error) { showError(error.message); }
}

async function removeStop(stop) {
  if (!await confirmAction("Remove stop?", "This stop will be removed from the itinerary.", "Remove stop")) return;
  try {
    await api(`/stops/${stop.id}`, { method: "DELETE" });
    await refreshCurrentTrip("Stop removed.");
  } catch (error) { showError(error.message); }
}

async function regenerateTrip() {
  if (!await confirmAction("Regenerate itinerary?", "Every current stop will be replaced with a newly generated itinerary.", "Regenerate")) return;
  try {
    status.value = "Regenerating the itinerary...";
    const result = await api(`/trips/${currentTrip.value.id}/regenerate`, { method: "POST" });
    selectTrip({ ...currentTrip.value, stops: result.stops, generationMode: result.generationMode });
    status.value = "Itinerary regenerated.";
  } catch (error) { showError(error.message); }
}

async function deleteTrip() {
  if (!await confirmAction("Delete trip?", "This trip and every stop in it will be permanently deleted.", "Delete trip")) return;
  try {
    await api(`/trips/${currentTrip.value.id}`, { method: "DELETE" });
    if (editingTripId.value === currentTrip.value.id) resetTripForm();
    currentTrip.value = null;
    invalidateSummary();
    await loadTrips();
    status.value = "Trip deleted.";
  } catch (error) { showError(error.message); }
}

function closeActionMenus(event) {
  const selectedAction = event.target.closest(".action-menu-items button");
  if (selectedAction) selectedAction.closest(".action-menu").open = false;
  document.querySelectorAll(".action-menu[open]").forEach((menu) => {
    if (!menu.contains(event.target)) menu.open = false;
  });
}

function printTrip() { window.print(); }

onMounted(() => {
  loadTrips();
  loadCapabilities();
  document.addEventListener("click", closeActionMenus);
});
onUnmounted(() => {
  document.removeEventListener("click", closeActionMenus);
  integrations.summaryVersion++;
  integrations.adviceVersion++;
  resolveFeedback?.(false);
});
</script>

<template>
  <header class="app-header">
    <div class="app-header-inner">
      <a class="product-name" href="/itinerary/">Itinerary Planner</a>
      <nav class="page-navigation" aria-label="Application navigation"><a href="/">All features</a></nav>
    </div>
  </header>
  <main class="page-shell">
    <details id="trip-composer" ref="composer" class="trip-composer">
      <summary>
        <span>
          <span id="trip-form-kicker" class="step-label">{{ editingTripId ? "Revise journey" : "New journey" }}</span>
          <span id="trip-form-title" class="composer-title">{{ editingTripId ? "Edit trip details" : "Trip details" }}</span>
          <span id="trip-form-summary" class="composer-summary">{{ editingTripId ? `${currentTrip.destination} · ${currentTrip.startDate} to ${currentTrip.endDate}` : "Set the destination, dates, budget, and interests." }}</span>
        </span>
        <span class="composer-toggle" aria-hidden="true"></span>
      </summary>
      <form id="trip-form" ref="tripForm" novalidate @submit.prevent="submitTrip">
        <div class="composer-fields">
          <div class="field-group field-traveller"><label for="user">Traveller</label><input id="user" v-model="tripDraft.user" name="user" maxlength="80" autocomplete="name" required></div>
          <div class="field-group field-destination"><label for="destination">Destination</label><input id="destination" v-model="tripDraft.destination" name="destination" maxlength="100" autocomplete="off" placeholder="e.g. Kyoto" required></div>
          <div class="field-group field-interests"><label for="interests">Interests</label><input id="interests" v-model="tripDraft.interests" name="interests" maxlength="500" placeholder="Food, architecture, gardens"></div>
          <div class="field-group field-start-date"><label for="start-date">Start</label><input id="start-date" v-model="tripDraft.startDate" name="startDate" type="date" required></div>
          <div class="field-group field-end-date"><label for="end-date">End</label><input id="end-date" v-model="tripDraft.endDate" name="endDate" type="date" required></div>
          <div class="field-group field-budget"><label for="budget">Budget (AUD)</label><input id="budget" v-model="tripDraft.budget" name="budget" type="number" min="0" max="1000000" step="0.01" placeholder="2500" required></div>
        </div>
        <div class="trip-form-actions">
          <button id="trip-submit" class="primary-button" type="submit" :disabled="tripBusy">{{ editingTripId ? "Save trip" : "Generate itinerary" }}</button>
          <button id="cancel-trip-edit" class="text-button" type="button" :hidden="!editingTripId" @click="resetTripForm">Cancel edit</button>
        </div>
      </form>
    </details>
    <div class="planner-grid">
      <aside class="saved-trips" aria-labelledby="saved-heading">
        <div class="saved-heading-row"><h2 id="saved-heading">Saved trips</h2><button id="refresh-trips" class="text-button" type="button" @click="loadTrips">Refresh</button></div>
        <label class="visually-hidden" for="trip-filter">Filter saved trips</label>
        <input id="trip-filter" v-model="tripFilter" type="search" placeholder="Filter by destination or traveller" autocomplete="off">
        <p id="trip-count" class="list-count" aria-live="polite">{{ tripCount }}</p>
        <ul id="trip-list" class="trip-list">
          <li v-if="tripsLoading" class="muted">Loading trips...</li>
          <li v-else-if="tripsError" class="muted">{{ tripsError }}</li>
          <li v-else-if="!trips.length" class="muted">No saved trips yet.</li>
          <li v-else-if="!filteredTrips.length" class="muted">No trips match this filter.</li>
          <li v-for="trip in tripsLoading || tripsError ? [] : filteredTrips" :key="trip.id">
            <button type="button" :data-trip-id="trip.id" @click="openTrip(trip.id)"><span class="trip-name">{{ trip.destination }}</span><span class="trip-list-dates">{{ trip.startDate }} to {{ trip.endDate }}</span></button>
          </li>
        </ul>
      </aside>
      <section class="itinerary-panel" :aria-labelledby="currentTrip ? 'trip-title' : 'itinerary-heading'">
        <div id="status" class="status" role="status" aria-live="polite">{{ status }}</div>
        <div id="empty-state" class="empty-state" :hidden="!!currentTrip">
          <span class="empty-index">01 / 02 / 03</span>
          <h2 id="itinerary-heading">Your days will unfold here.</h2>
          <p>Complete the trip details to draft a practical itinerary you can shape stop by stop.</p>
        </div>
        <div id="itinerary-content" :hidden="!currentTrip">
          <header class="itinerary-header">
            <div>
              <p id="trip-dates" class="eyebrow">{{ currentTrip ? `${currentTrip.startDate} to ${currentTrip.endDate}` : "" }}</p>
              <div class="trip-title-row"><h2 id="trip-title">{{ currentTrip ? `${currentTrip.destination} itinerary` : "" }}</h2><span id="generation-mode" class="mode-badge">{{ currentTrip?.generationMode === "fallback" ? "Reliable fallback" : currentTrip?.generationMode || "saved" }}</span></div>
              <p id="trip-summary" class="trip-summary">{{ currentTrip ? `${currentTrip.user} · AUD ${Number(currentTrip.budget).toLocaleString()} · ${currentTrip.interests || "Open interests"}` : "" }}</p>
            </div>
            <div class="header-actions">
              <button id="edit-trip" class="secondary-button" type="button" @click="beginTripEdit">Edit trip</button>
              <details id="trip-actions-menu" class="action-menu">
                <summary aria-label="Trip actions" title="Trip actions"><span aria-hidden="true">&#8230;</span></summary>
                <div class="action-menu-items">
                  <button id="regenerate-trip" type="button" @click="regenerateTrip">Regenerate all</button>
                  <button id="print-trip" type="button" @click="printTrip">Print itinerary</button>
                  <button id="delete-trip" class="danger-action" type="button" @click="deleteTrip">Delete trip</button>
                </div>
              </details>
            </div>
          </header>
          <dl class="trip-metrics" aria-label="Itinerary summary">
            <div><dt>Duration</dt><dd id="metric-duration">{{ dayCount }} {{ dayCount === 1 ? "day" : "days" }}</dd></div>
            <div><dt>Stops</dt><dd id="metric-stops">{{ stops.length }}</dd></div>
            <div><dt>Daily budget</dt><dd id="metric-budget">AUD {{ dailyBudget }}</dd></div>
            <div><dt>Planned days</dt><dd id="metric-days">{{ plannedDays }} / {{ dayCount }}</dd></div>
          </dl>
          <section class="integration-section" aria-labelledby="summary-heading">
            <div class="integration-heading"><h3 id="summary-heading">Saved itinerary summary</h3><button id="mcp-summary" class="secondary-button" type="button" :disabled="!integrations.capabilities.mcpEnabled || !currentTrip || integrations.summaryBusy" @click="inspectTrip">Inspect itinerary</button></div>
            <p id="mcp-status" class="muted" role="status">{{ summaryStatus }}</p>
            <dl id="mcp-result" class="trip-metrics" :hidden="!summary"><div v-for="[label, value] in summaryMetrics" :key="label"><dt>{{ label }}</dt><dd>{{ value }}</dd></div></dl>
          </section>
          <div id="days" class="days">
            <section v-for="[day, items] in days" :key="day" class="day" :aria-labelledby="`day-${day}`">
              <h3 :id="`day-${day}`">Day {{ day }}</h3>
              <div><article v-for="stop in items" :key="stop.id" class="stop">
                <div class="stop-heading">
                  <h4>{{ stop.activity }}</h4>
                  <details class="action-menu stop-action-menu">
                    <summary aria-label="Stop actions" title="Stop actions"><span aria-hidden="true">&#8230;</span></summary>
                    <div class="action-menu-items">
                      <button type="button" :data-edit-stop="stop.id" @click="openStopDialog(stop)">Edit</button>
                      <button type="button" :data-duplicate-stop="stop.id" @click="duplicateStop(stop)">Duplicate</button>
                      <button type="button" :data-regenerate-stop="stop.id" @click="regenerateStop(stop)">Regenerate</button>
                      <button class="danger-action" type="button" :data-remove-stop="stop.id" @click="removeStop(stop)">Remove</button>
                    </div>
                  </details>
                </div>
                <p>{{ stop.notes || "No notes yet." }}</p>
              </article></div>
            </section>
            <p v-if="!stops.length" class="muted">No stops yet. Add the first stop below.</p>
          </div>
          <button id="add-stop" class="add-button" type="button" @click="openStopDialog()">+ Add a stop</button>
        </div>
        <section class="integration-section" aria-labelledby="advice-heading">
          <div class="integration-heading"><h3 id="advice-heading">Planning advice</h3><button id="reload-capabilities" class="text-button" type="button" :hidden="!capabilitiesFailed" @click="loadCapabilities">Retry connection</button></div>
          <form id="advice-form" @submit.prevent="askAdvice">
            <label for="advice-question">Planning question</label>
            <textarea id="advice-question" v-model="adviceQuestion" maxlength="1000" rows="2" required :disabled="!integrations.capabilities.ragEnabled || integrations.adviceBusy"></textarea>
            <button id="advice-submit" class="secondary-button" type="submit" :disabled="!integrations.capabilities.ragEnabled || integrations.adviceBusy">Ask question</button>
          </form>
          <p id="advice-status" class="muted" role="status">{{ adviceStatus }}</p>
          <div id="advice-result" :hidden="!advice">
            <p id="advice-confidence" class="mode-badge">{{ advice ? `Confidence: ${advice.confidence}` : "" }}</p>
            <p id="advice-answer" class="advice-answer">{{ advice?.answer }}</p>
            <div id="advice-citations"><details v-for="(citation, index) in advice?.citations || []" :key="`${citation.chunk_id}-${index}`"><summary>{{ citation.source }}</summary><p>{{ citation.chunk_id }}</p><p>{{ citation.snippet }}</p></details></div>
          </div>
        </section>
      </section>
    </div>
  </main>
  <dialog id="stop-dialog" ref="stopDialog" aria-labelledby="stop-dialog-title">
    <form id="stop-form" method="dialog" novalidate @submit.prevent="saveStop">
      <h2 id="stop-dialog-title">{{ stopDraft.id ? "Edit stop" : "Add a stop" }}</h2>
      <input id="stop-id" v-model="stopDraft.id" type="hidden">
      <label for="stop-day">Day</label><input id="stop-day" v-model="stopDraft.day" type="number" min="1" :max="dayCount || 31" required>
      <label for="stop-activity">Activity</label><input id="stop-activity" v-model="stopDraft.activity" maxlength="160" required>
      <label for="stop-notes">Notes</label><textarea id="stop-notes" v-model="stopDraft.notes" maxlength="1000" rows="4"></textarea>
      <div class="dialog-actions"><button id="cancel-stop" class="text-button" type="button" @click="stopDialog.close()">Cancel</button><button class="primary-button" type="submit" :disabled="stopBusy">Save stop</button></div>
    </form>
  </dialog>
  <dialog id="feedback-dialog" ref="feedbackDialog" class="feedback-dialog" :data-kind="feedback.kind" aria-labelledby="feedback-title" aria-describedby="feedback-message" @cancel.prevent="closeFeedback(false)">
    <div class="feedback-symbol" aria-hidden="true"></div>
    <h2 id="feedback-title">{{ feedback.title }}</h2><p id="feedback-message">{{ feedback.message }}</p>
    <div class="dialog-actions"><button id="feedback-cancel" class="text-button" type="button" :hidden="!feedback.cancelLabel" @click="closeFeedback(false)">{{ feedback.cancelLabel }}</button><button id="feedback-confirm" ref="feedbackConfirm" class="primary-button" type="button" @click="closeFeedback(true)">{{ feedback.confirmLabel }}</button></div>
  </dialog>
</template>