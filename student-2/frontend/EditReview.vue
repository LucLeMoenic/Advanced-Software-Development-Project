<script setup>
import { computed, nextTick, onUnmounted, ref, watch } from "vue";

const props = defineProps({
  trip: { type: Object, default: null }, enabled: Boolean, active: Boolean,
  workflowId: { type: String, required: true }, expired: Boolean,
});
const emit = defineEmits(["accepted"]);
const record = ref(null);
const busy = ref(false);
const message = ref("");
const selected = ref([]);
const notes = ref("");
const correction = ref(null);
const output = ref(null);
const running = computed(() => record.value && ["queued", "planning", "working", "reviewing"].includes(record.value.status));
const canDecide = computed(() => props.enabled && !props.expired && record.value?.status === "awaiting_human_review" && !record.value.stale && !busy.value);
let timer;
let controller;
let version = 0;
let deadline = 0;

function stopRequests() {
  version++;
  clearTimeout(timer);
  controller?.abort();
  busy.value = false;
}

watch(() => [props.trip?.id, props.workflowId, props.enabled], () => {
  stopRequests();
  emit("accepted", false);
  record.value = null;
  correction.value = null;
  selected.value = [];
  notes.value = "";
  message.value = "";
  deadline = Date.now() + 20 * 60 * 1000;
  if (props.enabled && props.trip && props.workflowId) poll();
}, { immediate: true });
watch(() => JSON.stringify(props.trip), (value, old) => {
  if (record.value && old !== value) {
    record.value.stale = true;
    emit("accepted", false);
  }
});
onUnmounted(stopRequests);

async function request(path, method = "GET", body) {
  const currentController = new AbortController();
  controller = currentController;
  const timeout = setTimeout(() => currentController.abort(), 10000);
  try {
    const response = await fetch(`/itinerary-api/trips/${props.trip.id}/multi-agent-workflows${path}`, {
      method, signal: currentController.signal, headers: { "Content-Type": "application/json" },
      ...(body ? { body: JSON.stringify(body) } : {}),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error?.message || "The edit assessment request failed.");
    return data;
  } finally {
    clearTimeout(timeout);
  }
}

function failure(error, mutation = false) {
  const detail = error.name === "AbortError" ? "The request timed out." : error.message;
  const recovery = mutation
      ? "The outcome may be uncertain. Check workflow status before submitting again; requests are not automatically retried."
      : "Use Check status to reconnect.";
  message.value = `${detail} ${recovery}`;
}

function receive(data) {
  if (data.id !== props.workflowId) throw new Error("The service returned a different workflow.");
  record.value = data;
  emit("accepted", !data.stale && ["approved", "corrected", "partially_accepted"].includes(data.status));
  if (data.status === "awaiting_human_review") {
    selected.value = [];
    correction.value = JSON.parse(JSON.stringify(data.work));
    if (props.active) nextTick(() => output.value?.focus());
  }
  if (data.status === "failed") message.value = data.error?.message || "The workflow failed. Start a new review.";
  if (running.value) {
    if (Date.now() >= deadline) {
      message.value = "Automatic polling stopped after 20 minutes. This does not cancel the server workflow. Keep the workflow ID and check status later.";
    } else {
      timer = setTimeout(poll, 2000);
    }
  }
}

async function poll() {
  if (busy.value || !props.enabled || !props.trip || !props.workflowId) return;
  clearTimeout(timer);
  emit("accepted", false);
  const token = version;
  busy.value = true;
  try {
    const data = await request(`/${encodeURIComponent(props.workflowId)}`);
    if (token === version) receive(data);
  } catch (error) {
    if (token === version) failure(error);
  } finally {
    if (token === version) busy.value = false;
  }
}

function reconnect() {
  if (busy.value || !props.enabled) return;
  stopRequests();
  message.value = "";
  deadline = Date.now() + 20 * 60 * 1000;
  return poll();
}

async function decide(decision) {
  if (!canDecide.value) return;
  if (decision === "reject" && !notes.value.trim()) {
    message.value = "Explain why you are rejecting these recommendations.";
    return;
  }
  if (decision === "partial" && !selected.value.length) {
    message.value = "Select at least one recommendation to accept.";
    return;
  }
  const token = version;
  emit("accepted", false);
  busy.value = true;
  message.value = "";
  const body = { decision, notes: notes.value };
  if (decision === "partial") body.accepted_item_ids = selected.value;
  if (decision === "correct") body.corrected_output = correction.value;
  try {
    const data = await request(`/${encodeURIComponent(record.value.id)}/decision`, "POST", body);
    if (token === version) receive(data);
  } catch (error) {
    if (token === version) {
      failure(error, true);
      // Require a fresh read before another decision after an uncertain response.
      record.value = null;
    }
  } finally {
    if (token === version) busy.value = false;
  }
}
</script>

<template>
  <div class="plan-review">
    <div class="integration-heading"><h3>Assess this edit</h3><span class="mode-badge">Multi-agent</span></div>
    <p>Assessment decisions do not change your saved itinerary. After accepting the assessment, separately confirm the exact changes above.</p>
    <p>Correction and partial acceptance apply to assessment text, not parts of the edit. To change the edit, cancel and request a new preview and assessment.</p>
    <p v-if="expired" role="alert">This preview expired. Request a new preview and assessment before deciding or saving.</p>
    <p>Workflow ID: <code id="workflow-id">{{ workflowId }}</code> (keep for terminal history)</p>
    <button id="check-plan-status" class="text-button" :disabled="!enabled || !trip || busy" @click="reconnect">Check status</button>
    <p role="status" aria-live="polite">{{ message }}</p>
    <div v-if="record" ref="output" tabindex="-1" aria-label="Edit assessment result">
      <p role="status"><strong>Status:</strong> {{ record.status.replaceAll("_", " ") }}</p>
      <p v-if="record.stale" role="alert">This review is historical: the saved itinerary changed or was deleted. Start a new review before deciding.</p>
      <section v-if="record.plan" aria-label="Planner">
        <h4>Planner</h4><p>{{ record.plan.objective }}</p>
        <ol><li v-for="step in record.plan.steps" :key="step.id">{{ step.description }}</li></ol>
        <ul><li v-for="criterion in record.plan.success_criteria" :key="criterion">{{ criterion }}</li></ul>
      </section>
      <section v-if="record.work" aria-label="Worker">
        <h4>Worker assessment</h4><p>{{ record.work.summary }}</p>
        <article v-for="item in record.work.items" :key="item.id" class="review-finding">
          <label><input v-model="selected" type="checkbox" :value="item.id" :disabled="!canDecide"> {{ item.subject }}</label>
          <p>{{ item.detail }}</p><small>Evidence: {{ item.evidence_ids.join(", ") }}</small>
        </article>
      </section>
      <section v-if="record.review" aria-label="Reviewer">
        <h4>Reviewer: {{ record.review.verdict }}</h4>
        <p v-if="record.review.degraded" role="alert">Reviewer model failed. These are automatic checks only, not a successful agent review.</p>
        <ul><li v-for="(finding, index) in record.review.findings" :key="index">{{ finding.severity }}: {{ finding.message }}</li></ul>
        <ul><li v-for="recommendation in record.review.recommendations" :key="recommendation">{{ recommendation }}</li></ul>
      </section>
      <details v-if="record.evidence"><summary>Supplied evidence and limits</summary>
        <article v-for="entry in record.evidence" :key="entry.id"><h4>{{ entry.title }} ({{ entry.id }})</h4><p>{{ entry.text }}</p></article>
      </details>
      <div v-if="record.status === 'awaiting_human_review'">
        <h4>Human decision</h4>
        <label for="plan-notes">Decision notes (required for rejection)</label>
        <textarea id="plan-notes" v-model="notes" maxlength="1000" :disabled="!canDecide"></textarea>
        <div class="edit-actions">
          <button class="primary-button" :disabled="!canDecide" @click="decide('approve')">Approve assessment</button>
          <button class="secondary-button" :disabled="!canDecide" @click="decide('partial')">Accept selected</button>
          <button class="text-button" :disabled="!canDecide" @click="decide('reject')">Reject assessment</button>
        </div>
        <details v-if="correction"><summary>Correct assessment</summary>
          <form @submit.prevent="decide('correct')">
            <label for="corrected-summary">Corrected summary</label>
            <textarea id="corrected-summary" v-model="correction.summary" minlength="1" maxlength="400" required :disabled="!canDecide"></textarea>
            <fieldset v-for="item in correction.items" :key="item.id" :disabled="!canDecide">
              <legend>{{ item.id }}</legend>
              <label :for="`subject-${item.id}`">Subject</label><input :id="`subject-${item.id}`" v-model="item.subject" maxlength="120" required>
              <label :for="`detail-${item.id}`">Recommendation</label><textarea :id="`detail-${item.id}`" v-model="item.detail" maxlength="400" required></textarea>
              <label :for="`evidence-${item.id}`">Evidence references (one to three)</label>
              <select :id="`evidence-${item.id}`" v-model="item.evidence_ids" multiple required>
                <option v-for="entry in record.evidence" :key="entry.id" :value="entry.id">{{ entry.title }}</option>
              </select>
            </fieldset>
            <button class="secondary-button" :disabled="!canDecide">Save corrected assessment</button>
          </form>
        </details>
      </div>
      <section v-if="record.human_decision" aria-label="Recorded human decision">
        <h4>Recorded decision: {{ record.human_decision.decision }}</h4><p>{{ record.human_decision.notes }}</p>
        <ul v-if="record.human_decision.correction_findings?.length">
          <li v-for="(finding, index) in record.human_decision.correction_findings" :key="index">{{ finding.severity }}: {{ finding.message }}</li>
        </ul>
        <template v-if="record.final_output"><p>{{ record.final_output.summary }}</p>
          <article v-for="item in record.final_output.items" :key="item.id"><h4>{{ item.subject }}</h4><p>{{ item.detail }}</p></article>
        </template>
      </section>
      <details v-if="record.history?.length"><summary>Workflow history</summary>
        <ol><li v-for="(entry, index) in record.history" :key="index">{{ entry.stage }}: {{ entry.ok ? 'completed' : 'failed' }} {{ entry.model || '' }} {{ entry.duration_ms != null ? `${entry.duration_ms} ms` : '' }}</li></ol>
      </details>
    </div>
  </div>
</template>

<style scoped>
.plan-review { overflow-wrap: anywhere; }
form, section, details { margin-block: 1rem; }
fieldset { min-width: 0; margin-block: 1rem; }
select { max-width: 100%; width: 100%; }
input[type="checkbox"] { width: auto; }
</style>
