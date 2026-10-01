<script setup>
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import { Check, ClipboardCheck, Cloud, CloudFog, CloudLightning, CloudRain, CloudSnow, LoaderCircle, PanelRightClose, PanelRightOpen, Sun, Undo2, X } from "@lucide/vue";

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
const review = ref(null);
const assistantTab = ref("edit");
const assistantCollapsed = ref(false);
const savedChanges = reactive({ stopIds: [], days: [], dates: false });
let highlightTimeout = null;
const reviewQuestion = ref("Swap days 1 and 2");
const editSaving = ref(false);
const weather = ref(null);
const overviewResult = ref(null);
const summaryStatus = ref("Itinerary editing is disabled.");
const reviewEnabled = computed(() => integrations.capabilities.mcpEnabled && integrations.capabilities.aiEnabled);
let reviewController = null;
let adviceController = null;
const advice = ref(null);
const adviceQuestion = ref("");
const adviceStatus = ref("RAG is disabled.");
const adviceParts = computed(() => (advice.value?.answer || "").split(/(\[[^\]\r\n]+\])/g).map((text) => {
  const source = (advice.value?.citations || []).findIndex((citation) => text === `[${citation.chunk_id}]`);
  return { text, source };
}));
const previewSummary = computed(() => {
  const counts = {};
  for (const change of review.value?.changes || []) {
    const label = { add_stop: "to add", remove_stop: "to remove", update_stop: "to update", shift_dates: "date shift" }[change.kind] || "to move";
    counts[label] = (counts[label] || 0) + 1;
  }
  return Object.entries(counts).map(([label, count]) => label === "date shift" ? `${count} date shift` : `${count} ${count === 1 ? 'activity' : 'activities'} ${label}`).join(" · ");
});
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
const editPositions = computed(() => {
  const positions = (proposed) => {
    let planned = stops.value.map((stop) => ({ ...stop }));
    if (proposed) for (const change of review.value?.changes || []) {
      if (change.kind === "add_stop") planned.push(change.after);
      else if (change.kind === "remove_stop") planned = planned.filter((stop) => stop.id !== change.id);
      else if (change.kind === "update_stop") planned = planned.map((stop) => stop.id === change.id ? change.after : stop);
      else if (!change.kind) planned = planned.map((stop) => stop.id === change.id ? { ...stop, day: change.toDay, sortOrder: change.toOrder } : stop);
    }
    const ordered = planned.sort((first, second) => first.day - second.day || (first.sortOrder ?? 0) - (second.sortOrder ?? 0) || first.id - second.id);
    const counts = {};
    return Object.fromEntries(ordered.map((stop) => [stop.id, counts[stop.day] = (counts[stop.day] || 0) + 1]));
  };
  return { current: positions(false), proposed: positions(true) };
});
const dayCount = computed(() => currentTrip.value
  ? Math.round((new Date(currentTrip.value.endDate) - new Date(currentTrip.value.startDate)) / 86400000) + 1 : 0);
const plannedDays = computed(() => new Set(stops.value.map((stop) => stop.day)).size);
const dailyBudget = computed(() => (Number(currentTrip.value?.budget) / dayCount.value).toLocaleString(undefined, { maximumFractionDigits: 2 }));
const days = computed(() => {
  const grouped = {};
  for (const stop of stops.value) (grouped[stop.day] ||= []).push(stop);
  return Object.entries(grouped).sort(([first], [second]) => Number(first) - Number(second));
});
const weatherMessage = computed(() => ({
  not_found: "No matching weather location found. Check the saved destination.",
  unavailable: "Weather is currently unavailable. Your saved-trip details are still available.",
  outside_window: "Trip dates are outside the current forecast window (up to 16 days ahead).",
  partial: "Forecast available for part of this trip. Other dates are listed below.",
  available: "Forecast available for all trip dates.",
}[weather.value?.status] || ""));

function locationLabel(location) {
  return [...new Set([location.name, location.admin1, location.country].filter(Boolean))].join(", ");
}

function weatherCondition(code) {
  if (code === 0) return { label: "Clear sky", icon: Sun };
  if ([1, 2, 3].includes(code)) return { label: ["", "Mainly clear", "Partly cloudy", "Overcast"][code], icon: Cloud };
  if ([45, 48].includes(code)) return { label: "Fog", icon: CloudFog };
  if ([51, 53, 55, 56, 57].includes(code)) return { label: "Drizzle", icon: CloudRain };
  if ([61, 63, 65, 66, 67, 80, 81, 82].includes(code)) return { label: "Rain", icon: CloudRain };
  if ([71, 73, 75, 77, 85, 86].includes(code)) return { label: "Snow", icon: CloudSnow };
  if ([95, 96, 97, 99].includes(code)) return { label: "Thunderstorm", icon: CloudLightning };
  return { label: "Conditions unavailable", icon: Cloud };
}

function formatWeatherValue(value, unit) {
  return value == null ? "Not available" : `${value}${unit}`;
}

function selectAssistantTab(tab) {
  assistantTab.value = tab;
  nextTick(() => document.querySelector(`#${tab}-tab`)?.focus());
}

function dayDate(day) {
  const date = new Date(`${currentTrip.value.startDate}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() + Number(day) - 1);
  return date.toISOString().slice(0, 10);
}

function readableDate(value) {
  return new Intl.DateTimeFormat("en-AU", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" }).format(new Date(`${value}T00:00:00Z`));
}

function clearSavedHighlights() {
  clearTimeout(highlightTimeout);
  Object.assign(savedChanges, { stopIds: [], days: [], dates: false });
}

function savedMessage(changes) {
  if (changes.length !== 1) return `${changes.length} itinerary changes saved.`;
  const change = changes[0];
  if (change.kind === "shift_dates") return `Trip dates shifted to ${readableDate(change.toStartDate)} - ${readableDate(change.toEndDate)}.`;
  if (change.kind === "add_stop") return `Added "${change.after.activity}" to Day ${change.after.day}.`;
  if (change.kind === "remove_stop") return `Removed "${change.before.activity}" from Day ${change.before.day}.`;
  if (change.kind === "update_stop") return `Updated ${change.before.activity !== change.after.activity ? "activity" : "notes"} for "${change.after.activity}".`;
  return `Moved "${change.activity}" to Day ${change.toDay}.`;
}

function cancelAdvice() {
  adviceController?.abort();
  integrations.adviceVersion++;
  integrations.adviceBusy = false;
  adviceStatus.value = "Advice request cancelled.";
}

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
  if (response.ok && ["POST", "PUT", "DELETE"].includes(options.method) && !path.endsWith("/mcp-summary") && !path.endsWith("/mcp-overview") && !path.endsWith("/review") && !path.endsWith("/edit-preview") && !path.endsWith("/edit-operation-preview") && !path.endsWith("/edit-confirm") && path !== "/itinerary-advice") invalidateSummary();
  if (response.status === 204) return null;
  const body = await response.json();
  if (!response.ok) throw new Error(Object.values(body.error?.fields || {})[0] || body.error?.message || "The request could not be completed.");
  return body;
}

function cancelPreview() {
  reviewController?.abort();
  integrations.summaryVersion++;
  integrations.summaryBusy = false;
  review.value = null;
  summaryStatus.value = reviewEnabled.value ? "" : "Itinerary editing is disabled.";
}

watch(reviewQuestion, cancelPreview, { flush: "sync" });

function invalidateSummary() {
  clearSavedHighlights();
  cancelPreview();
  adviceController?.abort();
  integrations.adviceVersion++;
  integrations.adviceBusy = false;
  advice.value = null;
  weather.value = null;
  adviceStatus.value = integrations.capabilities.ragEnabled ? "" : "RAG is disabled.";
}

async function loadCapabilities() {
  try {
    const capabilities = await api("/capabilities");
    if (!["aiEnabled", "mcpEnabled", "ragEnabled"].every((name) => typeof capabilities[name] === "boolean")) throw new Error("Could not read service availability.");
    integrations.capabilities = capabilities;
    summaryStatus.value = reviewEnabled.value ? "" : "Itinerary editing is disabled.";
    adviceStatus.value = capabilities.ragEnabled ? "" : "RAG is disabled.";
    capabilitiesFailed.value = false;
  } catch {
    integrations.capabilities = {};
    adviceStatus.value = "Could not read service availability.";
    capabilitiesFailed.value = true;
  }
}

function inspectTrip() {
  const question = reviewQuestion.value.trim();
  if (!question || question.length > 1000) return;
  return requestEditPreview("edit-preview", { question });
}

async function requestEditPreview(endpoint, payload) {
  if (integrations.summaryBusy || editSaving.value || !currentTrip.value || !reviewEnabled.value) return;
  const tripId = currentTrip.value.id;
  const version = ++integrations.summaryVersion;
  integrations.summaryBusy = true;
  review.value = null;
  summaryStatus.value = "Preparing edit preview...";
  reviewController = new AbortController();
  const controller = reviewController;
  const timeout = setTimeout(() => controller.abort("timeout"), 35000);
  try {
    const result = await api(`/trips/${tripId}/${endpoint}`, { method: "POST", body: JSON.stringify(payload), signal: controller.signal });
    if (version !== integrations.summaryVersion || currentTrip.value?.id !== tripId) return;
    review.value = result.preview;
    summaryStatus.value = result.clarification || "Preview ready. No changes saved. Expires in 10 minutes.";
    integrations.summaryBusy = false;
    await nextTick();
    if (version === integrations.summaryVersion && !assistantCollapsed.value && assistantTab.value === "edit") overviewResult.value?.focus();
  } catch (error) {
    if (version === integrations.summaryVersion) summaryStatus.value = controller.signal.reason === "timeout" ? "The edit preview timed out." : error.message;
  } finally {
    clearTimeout(timeout);
    if (version === integrations.summaryVersion) integrations.summaryBusy = false;
  }
}

function previewUndo() {
  return requestEditPreview("edit-operation-preview", { operation: {
    action: "undo", sourceDay: 1, targetDay: 1, stopId: 0, targetStopId: 0,
  } });
}

async function confirmEdit() {
  if (editSaving.value || !review.value || !currentTrip.value || !reviewEnabled.value) return;
  const tripId = currentTrip.value.id;
  const token = review.value.token;
  const changes = review.value.changes;
  const previousIds = new Set(stops.value.map((stop) => stop.id));
  const version = integrations.summaryVersion;
  editSaving.value = true;
  summaryStatus.value = "Saving confirmed changes...";
  try {
    await api(`/trips/${tripId}/edit-confirm`, { method: "POST", body: JSON.stringify({ token }), signal: AbortSignal.timeout(10000) });
    if (currentTrip.value?.id !== tripId || version !== integrations.summaryVersion) return;
    invalidateSummary();
    const refreshVersion = integrations.summaryVersion;
    const updated = await api(`/trips/${tripId}`);
    if (currentTrip.value?.id !== tripId || refreshVersion !== integrations.summaryVersion) return;
    selectTrip(updated);
    trips.value = trips.value.map((trip) => trip.id === tripId ? updated : trip);
    summaryStatus.value = savedMessage(changes);
    status.value = summaryStatus.value;
    savedChanges.stopIds = [...changes.map((change) => change.id), ...updated.stops.filter((stop) => !previousIds.has(stop.id)).map((stop) => stop.id)];
    savedChanges.days = changes.flatMap((change) => [change.before?.day, change.after?.day, change.fromDay, change.toDay]).filter(Boolean);
    savedChanges.dates = changes.some((change) => change.kind === "shift_dates");
    highlightTimeout = setTimeout(clearSavedHighlights, 8000);
    await nextTick();
    document.querySelector(assistantCollapsed.value ? "#toggle-assistant" : assistantTab.value === "edit" ? "#mcp-summary" : "#advice-tab")?.focus();
  } catch (error) {
    if (currentTrip.value?.id === tripId) {
      cancelPreview();
      summaryStatus.value = `${error.message} Refresh the saved trip before requesting another preview; a save may already have completed.`;
    }
  } finally {
    editSaving.value = false;
  }
}

async function askAdvice() {
  if (integrations.adviceBusy || !integrations.capabilities.ragEnabled) return;
  const question = adviceQuestion.value.trim();
  if (!question) return;
  const version = ++integrations.adviceVersion;
  integrations.adviceBusy = true;
  advice.value = null;
  weather.value = null;
  adviceStatus.value = "Retrieving planning advice...";
  const tripId = currentTrip.value?.id;
  adviceController = new AbortController();
  const controller = adviceController;
  const timeout = setTimeout(() => controller.abort("timeout"), 55000);
  try {
    const result = await api("/itinerary-advice", { method: "POST", body: JSON.stringify({ question, ...(tripId ? { tripId } : {}) }), signal: controller.signal });
    if (version !== integrations.adviceVersion) return;
    advice.value = result;
    weather.value = result.weather || null;
    adviceStatus.value = result.confidence === "insufficient" ? "Insufficient context." : "Planning advice received.";
  } catch (error) {
    if (version === integrations.adviceVersion) adviceStatus.value = controller.signal.reason === "timeout" ? "The advice request timed out." : error.message;
  } finally {
    clearTimeout(timeout);
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
  clearSavedHighlights();
  document.removeEventListener("click", closeActionMenus);
  reviewController?.abort();
  adviceController?.abort();
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
    <div class="planner-grid" :class="{ 'assistant-collapsed': assistantCollapsed }">
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
            <button type="button" :data-trip-id="trip.id" :aria-current="currentTrip?.id === trip.id ? 'true' : undefined" @click="openTrip(trip.id)"><span class="trip-name">{{ trip.destination }}</span><span class="trip-list-dates">{{ trip.startDate }} to {{ trip.endDate }}</span></button>
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
              <p id="trip-dates" class="eyebrow" :class="{ 'saved-highlight': savedChanges.dates }">{{ currentTrip ? `${readableDate(currentTrip.startDate)} - ${readableDate(currentTrip.endDate)}` : "" }}</p>
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
          <div id="days" class="days">
            <section v-for="[day, items] in days" :key="day" class="day" :class="{ 'saved-highlight': savedChanges.days.includes(Number(day)) || savedChanges.dates }" :aria-labelledby="`day-${day}`">
              <h3 :id="`day-${day}`">Day {{ day }}<time class="day-date" :datetime="dayDate(day)">{{ readableDate(dayDate(day)) }}</time></h3>
              <div><article v-for="stop in items" :key="stop.id" class="stop" :data-stop-id="stop.id" :class="{ 'saved-highlight': savedChanges.stopIds.includes(stop.id) }">
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
      </section>
      <aside class="assistant-panel" aria-labelledby="assistant-heading">
        <div class="assistant-navigation">
        <header class="assistant-header">
          <button id="toggle-assistant" class="assistant-toggle" type="button" :aria-expanded="!assistantCollapsed" aria-controls="assistant-tabs assistant-content" :aria-label="assistantCollapsed ? 'Expand trip assistant' : 'Minimise trip assistant'" :title="assistantCollapsed ? 'Expand trip assistant' : 'Minimise trip assistant'" @click="assistantCollapsed = !assistantCollapsed"><PanelRightOpen v-if="assistantCollapsed" :size="20" aria-hidden="true" /><PanelRightClose v-else :size="20" aria-hidden="true" /></button>
          <h2 id="assistant-heading">Trip assistant</h2>
          <p class="muted">{{ currentTrip ? currentTrip.destination : "No trip selected" }}</p>
        </header>
        <div id="assistant-tabs" class="assistant-tabs" role="tablist" aria-label="Trip assistant" :hidden="assistantCollapsed"
          @keydown.right.prevent="selectAssistantTab(assistantTab === 'edit' ? 'advice' : 'edit')"
          @keydown.left.prevent="selectAssistantTab(assistantTab === 'edit' ? 'advice' : 'edit')"
          @keydown.home.prevent="selectAssistantTab('edit')" @keydown.end.prevent="selectAssistantTab('advice')">
          <button id="edit-tab" role="tab" aria-controls="edit-panel" :aria-selected="assistantTab === 'edit'" :tabindex="assistantTab === 'edit' ? 0 : -1" @click="assistantTab = 'edit'">Edit</button>
          <button id="advice-tab" role="tab" aria-controls="advice-panel" :aria-selected="assistantTab === 'advice'" :tabindex="assistantTab === 'advice' ? 0 : -1" @click="assistantTab = 'advice'">Advice</button>
        </div>
        </div>
        <div id="assistant-content" class="assistant-content" :hidden="assistantCollapsed">
          <section id="edit-panel" class="integration-section" role="tabpanel" aria-labelledby="edit-tab" :hidden="assistantTab !== 'edit'" tabindex="0">
            <div class="integration-heading"><h3 id="summary-heading">Edit my itinerary</h3><span class="mode-badge">MCP</span></div>
            <p v-if="!currentTrip" class="muted">Select a saved trip to edit.</p>
            <form id="review-form" @submit.prevent="inspectTrip">
              <label for="review-question">Requested change</label>
              <textarea id="review-question" v-model="reviewQuestion" rows="2" maxlength="1000" required :disabled="!reviewEnabled || !currentTrip || integrations.summaryBusy || editSaving" placeholder="Add a lunch break to day 2"></textarea>
              <div class="edit-actions">
                <button id="mcp-summary" class="secondary-button overview-refresh" type="submit" :disabled="!reviewEnabled || !currentTrip || integrations.summaryBusy || editSaving || !reviewQuestion.trim()"><LoaderCircle v-if="integrations.summaryBusy" class="loading-spinner" :size="16" aria-hidden="true" /><ClipboardCheck v-else :size="16" aria-hidden="true" />{{ integrations.summaryBusy ? "Preparing..." : "Preview changes" }}</button>
                <button id="undo-edit" class="text-button overview-refresh" type="button" title="Preview undo of the last confirmed itinerary edit" :disabled="!reviewEnabled || !currentTrip || integrations.summaryBusy || editSaving" @click="previewUndo"><Undo2 :size="16" aria-hidden="true" />Undo last edit</button>
              </div>
            </form>
            <p id="mcp-status" class="muted" role="status">{{ summaryStatus }}</p>
            <div id="mcp-result" ref="overviewResult" tabindex="-1" aria-label="Itinerary edit preview" :hidden="!review">
              <template v-if="review">
                <div class="preview-heading"><h3>Review changes</h3><span class="mode-badge">Not saved</span></div>
                <p class="preview-count">{{ previewSummary }}</p>
                <article v-for="(change, index) in review.changes" :key="change.kind === 'shift_dates' ? 'dates' : change.id" class="review-finding" :data-change-kind="change.kind || 'move'">
                  <span class="change-number">Change {{ index + 1 }}</span>
                  <template v-if="change.kind === 'shift_dates'">
                    <h4>Shift trip dates</h4>
                    <div class="edit-detail-states">
                      <div><p class="muted">Current dates</p><p>{{ change.fromStartDate }} to {{ change.fromEndDate }}</p></div>
                      <div><p class="muted">Proposed dates</p><p>{{ change.toStartDate }} to {{ change.toEndDate }}</p></div>
                    </div>
                  </template>
                  <template v-else-if="change.kind">
                    <h4>{{ { add_stop: 'Add activity', remove_stop: 'Remove activity', update_stop: 'Update activity' }[change.kind] }}</h4>
                    <div class="edit-detail-states">
                      <div><p class="muted">Current</p><template v-if="change.before"><p><strong>{{ change.before.activity }}</strong></p><p>Day {{ change.before.day }}, stop {{ editPositions.current[change.id] }}</p><p>{{ change.before.notes || 'No notes' }}</p></template><p v-else>Not scheduled</p></div>
                      <div><p class="muted">Proposed</p><template v-if="change.after"><p :class="{ 'changed-value': change.before?.activity !== change.after.activity }"><strong>{{ change.after.activity }}</strong></p><p>Day {{ change.after.day }}, stop {{ editPositions.proposed[change.id] }}</p><p :class="{ 'changed-value': change.before?.notes !== change.after.notes }">{{ change.after.notes || 'No notes' }}</p></template><p v-else>Removed from itinerary</p></div>
                    </div>
                  </template>
                  <template v-else>
                    <h4>{{ change.activity }}</h4>
                    <div class="edit-detail-states"><div><p class="muted">Current</p><p>Day {{ change.fromDay }}</p><small>Stop {{ editPositions.current[change.id] || "?" }} (current)</small></div><div><p class="muted">Proposed</p><p>Day {{ change.toDay }}</p><small>Stop {{ editPositions.proposed[change.id] || "?" }} (proposed)</small></div></div>
                    <p v-if="change.notes">{{ change.notes }}</p>
                  </template>
                </article>
                <div class="edit-actions preview-actions">
                  <button id="confirm-edit" class="primary-button overview-refresh" type="button" :disabled="editSaving" @click="confirmEdit"><Check :size="16" aria-hidden="true" />{{ editSaving ? "Saving..." : `Confirm ${review.changes.length} ${review.changes.length === 1 ? 'change' : 'changes'}` }}</button>
                  <button id="cancel-edit" class="text-button overview-refresh" type="button" :disabled="editSaving" @click="cancelPreview"><X :size="16" aria-hidden="true" />Cancel</button>
                </div>
              </template>
            </div>
          </section>
        <section id="advice-panel" class="integration-section" role="tabpanel" aria-labelledby="advice-tab" :hidden="assistantTab !== 'advice'" tabindex="0">
          <div class="integration-heading"><h3 id="advice-heading">Planning advice</h3><span class="mode-badge">RAG</span><button id="reload-capabilities" class="text-button" type="button" :hidden="!capabilitiesFailed" @click="loadCapabilities">Retry connection</button></div>
          <form id="advice-form" @submit.prevent="askAdvice">
            <label for="advice-question">Planning question</label>
            <textarea id="advice-question" v-model="adviceQuestion" maxlength="1000" rows="2" required :disabled="!integrations.capabilities.ragEnabled || integrations.adviceBusy"></textarea>
            <div class="edit-actions">
              <button id="advice-submit" class="secondary-button overview-refresh" type="submit" :disabled="!integrations.capabilities.ragEnabled || integrations.adviceBusy"><LoaderCircle v-if="integrations.adviceBusy" class="loading-spinner" :size="16" aria-hidden="true" />{{ integrations.adviceBusy ? "Getting advice..." : "Ask question" }}</button>
              <button v-if="integrations.adviceBusy" id="cancel-advice" class="text-button overview-refresh" type="button" @click="cancelAdvice"><X :size="16" aria-hidden="true" />Cancel</button>
            </div>
          </form>
          <p id="advice-status" class="muted" role="status">{{ adviceStatus }}</p>
          <div id="advice-result" :hidden="!advice">
            <p id="advice-confidence" class="mode-badge" title="Retrieval relevance, not factual certainty">{{ advice ? `Source relevance: ${advice.confidence}` : "" }}</p>
            <p id="advice-answer" class="advice-answer"><template v-for="(part, index) in adviceParts" :key="index">{{ part.source >= 0 ? `[${part.source + 1}]` : part.text }}</template></p>
            <div id="advice-citations"><details v-for="(citation, index) in advice?.citations || []" :id="`advice-source-${index}`" :key="`${citation.chunk_id}-${index}`"><summary>[{{ index + 1 }}] {{ citation.source }}</summary><p>{{ citation.snippet }}</p></details></div>
            <p v-if="advice?.contextNotice" class="muted">{{ advice.contextNotice }}</p>
            <p v-if="advice?.weatherNotice" class="muted">{{ advice.weatherNotice }}</p>
            <section v-if="weather" id="overview-weather" class="overview-weather" aria-labelledby="weather-heading">
              <h4 id="weather-heading">Destination weather</h4>
              <p id="weather-status" class="muted" role="status">{{ weatherMessage }}</p>
              <p v-if="weather.location" class="weather-place">Forecast location (top match): {{ locationLabel(weather.location) }}</p>
              <ul v-if="weather.days.length" class="weather-days" aria-label="Daily forecast">
                <li v-for="forecast in weather.days" :key="forecast.date" class="weather-day">
                  <time :datetime="forecast.date">{{ forecast.date }}</time>
                  <span class="weather-condition"><component :is="weatherCondition(forecast.weatherCode).icon" :size="20" aria-hidden="true" />{{ weatherCondition(forecast.weatherCode).label }}</span>
                  <span><span class="weather-label">Low / High</span>{{ formatWeatherValue(forecast.minTemperature, ' C') }} / {{ formatWeatherValue(forecast.maxTemperature, ' C') }}</span>
                  <span><span class="weather-label">Precipitation chance</span>{{ formatWeatherValue(forecast.precipitationProbability, '%') }}</span>
                </li>
              </ul>
              <p v-if="['partial', 'outside_window'].includes(weather.status)" class="muted weather-missing">No forecast: {{ weather.unavailableDates.join(', ') }}</p>
              <p v-if="weather.retrievedAt" class="muted">Retrieved {{ new Date(weather.retrievedAt).toLocaleString() }}. Forecasts may change.</p>
              <p class="muted weather-attribution">Weather: <a href="https://open-meteo.com/" target="_blank" rel="noopener noreferrer">Open-Meteo</a> (<a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noopener noreferrer">CC BY 4.0</a>). Locations: <a href="https://www.geonames.org/" target="_blank" rel="noopener noreferrer">GeoNames</a>.</p>
            </section>
          </div>
        </section>
        </div>
      </aside>
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