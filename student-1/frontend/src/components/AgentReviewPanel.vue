<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import {
  reviewsApi,
  type ReviewDecision,
  type ReviewDecisionChoice,
  type ReviewRecord,
  type ReviewStatus,
  type ReviewSummary,
  type SearchResponse,
} from '../api'

const props = defineProps<{
  search: SearchResponse
}>()

const emit = defineEmits<{
  status: [message: string]
}>()

// A local 3B model takes one to three minutes for the three agents, so the panel checks back regularly.
const POLL_INTERVAL_MS = 3000
const RUNNING: ReviewStatus[] = ['queued', 'planning', 'working', 'reviewing']

const STATUS_LABELS: Record<ReviewStatus, string> = {
  queued: 'Waiting to start',
  planning: 'Planner is making a plan',
  working: 'Worker is comparing the stays',
  reviewing: 'Reviewer is checking the work',
  awaiting_human_review: 'Waiting for your decision',
  approved: 'Approved',
  corrected: 'Corrected and accepted',
  partially_accepted: 'Partly accepted',
  rejected: 'Rejected',
  failed: 'Failed',
}

const reviews = ref<ReviewSummary[]>([])
const active = ref<ReviewRecord | null>(null)
const starting = ref(false)
const deciding = ref(false)
const errorMessage = ref('')
const decisionError = ref('')
const choice = ref<ReviewDecisionChoice>('approve')
const notes = ref('')
const acceptedIds = ref<string[]>([])
const correctedDetails = ref<Record<string, string>>({})
let pollTimer: ReturnType<typeof setTimeout> | undefined
// A request still in flight when the panel closes must not schedule another check.
let unmounted = false

const running = computed(() => active.value !== null && RUNNING.includes(active.value.status))
const awaitingDecision = computed(() => active.value?.status === 'awaiting_human_review')
const evidenceTitles = computed(() =>
  new Map((active.value?.evidence ?? []).map((entry) => [entry.id, entry.title])),
)

onMounted(loadReviews)
onBeforeUnmount(() => {
  unmounted = true
  stopPolling()
})

async function loadReviews() {
  try {
    reviews.value = await reviewsApi.list(props.search.id)
  } catch (error) {
    showError(error)
  }
}

async function startReview() {
  if (starting.value || running.value) {
    return
  }

  starting.value = true
  errorMessage.value = ''
  try {
    const started = await reviewsApi.start(props.search.id)
    emit('status', 'Agent review started.')
    await openReview(started.id)
    await loadReviews()
  } catch (error) {
    showError(error)
  } finally {
    starting.value = false
  }
}

async function openReview(id: string) {
  stopPolling()
  errorMessage.value = ''
  try {
    showRecord(await reviewsApi.get(id))
  } catch (error) {
    showError(error)
  }
}

function showRecord(record: ReviewRecord) {
  const previousStatus = active.value?.id === record.id ? active.value.status : null
  active.value = record
  if (record.status !== previousStatus) {
    emit('status', `Agent review: ${STATUS_LABELS[record.status]}.`)
    if (record.status === 'awaiting_human_review') {
      resetDecisionForm(record)
    }
  }

  reviews.value = reviews.value.map((summary) =>
    summary.id === record.id ? { ...summary, status: record.status } : summary,
  )
  if (RUNNING.includes(record.status) && !unmounted) {
    pollTimer = setTimeout(() => void openReview(record.id), POLL_INTERVAL_MS)
  }
}

function resetDecisionForm(record: ReviewRecord) {
  choice.value = 'approve'
  notes.value = ''
  decisionError.value = ''
  acceptedIds.value = record.work?.items.map((item) => item.id) ?? []
  correctedDetails.value = Object.fromEntries(
    (record.work?.items ?? []).map((item) => [item.id, item.detail]),
  )
}

async function submitDecision() {
  const record = active.value
  if (!record?.work || deciding.value) {
    return
  }

  const decision = buildDecision(record.work)
  if (typeof decision === 'string') {
    decisionError.value = decision
    emit('status', decision)
    return
  }

  decisionError.value = ''
  deciding.value = true
  try {
    showRecord(await reviewsApi.decide(record.id, decision))
  } catch (error) {
    decisionError.value = messageOf(error)
    emit('status', decisionError.value)
  } finally {
    deciding.value = false
  }
}

/** Returns the request body, or a message explaining what the traveller still needs to enter. */
function buildDecision(work: NonNullable<ReviewRecord['work']>): ReviewDecision | string {
  const trimmedNotes = notes.value.trim()
  if (choice.value === 'reject' && trimmedNotes.length === 0) {
    return 'Add a note explaining why you are rejecting the review.'
  }
  if (choice.value === 'partial') {
    if (acceptedIds.value.length === 0) {
      return 'Select at least one recommendation to keep.'
    }
    return { decision: 'partial', notes: trimmedNotes, acceptedItemIds: acceptedIds.value }
  }
  if (choice.value === 'correct') {
    const items = work.items.map((item) => ({ ...item, detail: correctedDetails.value[item.id]?.trim() ?? '' }))
    if (items.some((item) => item.detail.length === 0 || item.detail.length > 400)) {
      return 'Each corrected explanation needs 1 to 400 characters.'
    }
    return { decision: 'correct', notes: trimmedNotes, correctedOutput: { summary: work.summary, items } }
  }
  return { decision: choice.value, notes: trimmedNotes }
}

function stopPolling() {
  clearTimeout(pollTimer)
  pollTimer = undefined
}

function showError(error: unknown) {
  stopPolling()
  errorMessage.value = messageOf(error)
  emit('status', errorMessage.value)
}

function messageOf(error: unknown) {
  return error instanceof Error ? error.message : 'The agent review service could not complete the request.'
}

function citedTitles(ids: string[]) {
  return ids.map((id) => evidenceTitles.value.get(id) ?? id).join(', ')
}

function formatTime(value: string) {
  return new Date(value).toLocaleString('en-AU', { dateStyle: 'medium', timeStyle: 'short' })
}
</script>

<template>
  <section class="panel review-panel" aria-labelledby="review-heading">
    <div class="section-heading">
      <div>
        <p class="section-label">Agent review</p>
        <h2 id="review-heading">Check this shortlist with AI agents</h2>
        <p class="section-copy">
          A Planner, Worker and Reviewer recommend which saved stays suit this trip, using only the
          saved results. You make the final decision; your saved search is not changed.
        </p>
      </div>
      <button
        class="button button-primary review-start"
        type="button"
        :disabled="starting || running || search.results.length === 0"
        @click="startReview"
      >
        {{ starting ? 'Starting...' : 'Start agent review' }}
      </button>
    </div>

    <div class="review-body">
      <div v-if="errorMessage" class="notice notice-error" role="alert">
        <strong>The agent review could not continue.</strong>
        <span>{{ errorMessage }}</span>
      </div>

      <div v-if="reviews.length > 0" class="review-history">
        <h3>Previous reviews of this search</h3>
        <ul>
          <li v-for="summary in reviews" :key="summary.id">
            <span>{{ formatTime(summary.createdAt) }} · {{ STATUS_LABELS[summary.status] }}</span>
            <button class="button-link" type="button" @click="openReview(summary.id)">Open</button>
          </li>
        </ul>
      </div>

      <div v-if="active" class="review-record">
        <p class="review-status">
          <span v-if="running" class="spinner review-spinner" aria-hidden="true"></span>
          <strong>{{ STATUS_LABELS[active.status] }}</strong>
        </p>

        <div v-if="active.error" class="notice notice-error">
          <strong>The {{ active.error.stage ?? 'workflow' }} stage failed.</strong>
          <span>{{ active.error.message }} Start a new review to try again.</span>
        </div>

        <div v-if="active.plan" class="review-stage">
          <h3>Planner</h3>
          <p>{{ active.plan.objective }}</p>
          <ol>
            <li v-for="step in active.plan.steps" :key="step.id">{{ step.description }}</li>
          </ol>
        </div>

        <div v-if="active.work" class="review-stage">
          <h3>Worker</h3>
          <p>{{ active.work.summary }}</p>
          <ul class="review-items">
            <li v-for="item in active.work.items" :key="item.id">
              <strong>{{ item.subject }}</strong>
              <span>{{ item.detail }}</span>
              <small>Based on: {{ citedTitles(item.evidenceIds) }}</small>
            </li>
          </ul>
        </div>

        <div v-if="active.review" class="review-stage">
          <h3>Reviewer</h3>
          <p>
            Verdict: <strong :class="`verdict-${active.review.verdict}`">{{ active.review.verdict }}</strong>
          </p>
          <p v-if="active.review.degraded" class="notice notice-warning">
            The Reviewer agent did not respond, so only the automatic checks ran. Check each item yourself.
          </p>
          <ul v-if="active.review.findings.length > 0" class="review-findings">
            <li v-for="(finding, index) in active.review.findings" :key="index">
              <span :class="`finding-${finding.severity}`">{{ finding.severity }}</span>
              {{ finding.message }}
            </li>
          </ul>
          <ul v-if="active.review.recommendations.length > 0">
            <li v-for="(recommendation, index) in active.review.recommendations" :key="index">
              {{ recommendation }}
            </li>
          </ul>
        </div>

        <form v-if="awaitingDecision && active.work" class="review-decision" novalidate @submit.prevent="submitDecision">
          <fieldset>
            <legend>Your decision</legend>
            <label><input v-model="choice" type="radio" name="review-decision" value="approve"> Approve all</label>
            <label><input v-model="choice" type="radio" name="review-decision" value="partial"> Keep some</label>
            <label><input v-model="choice" type="radio" name="review-decision" value="correct"> Correct the explanations</label>
            <label><input v-model="choice" type="radio" name="review-decision" value="reject"> Reject</label>
          </fieldset>

          <fieldset v-if="choice === 'partial'">
            <legend>Recommendations to keep</legend>
            <label v-for="item in active.work.items" :key="item.id">
              <input v-model="acceptedIds" type="checkbox" :value="item.id"> {{ item.subject }}
            </label>
          </fieldset>

          <div v-if="choice === 'correct'" class="review-corrections">
            <div v-for="item in active.work.items" :key="item.id" class="field">
              <label :for="`correction-${item.id}`">{{ item.subject }}</label>
              <textarea
                :id="`correction-${item.id}`"
                v-model="correctedDetails[item.id]"
                rows="2"
                maxlength="400"
              />
            </div>
          </div>

          <div class="field">
            <label for="review-notes">Notes{{ choice === 'reject' ? ' (required)' : ' (optional)' }}</label>
            <textarea id="review-notes" v-model="notes" rows="2" maxlength="1000" />
          </div>

          <p v-if="decisionError" class="field-error" role="alert">{{ decisionError }}</p>
          <button class="button button-primary" type="submit" :disabled="deciding">
            {{ deciding ? 'Saving...' : 'Save decision' }}
          </button>
        </form>

        <div v-if="active.humanDecision" class="review-stage">
          <h3>Your decision</h3>
          <p>
            {{ STATUS_LABELS[active.status] }} on {{ formatTime(active.humanDecision.decidedAt) }}.
            <span v-if="active.humanDecision.notes">Notes: {{ active.humanDecision.notes }}</span>
          </p>
          <ul v-if="active.finalOutput" class="review-items">
            <li v-for="item in active.finalOutput.items" :key="item.id">
              <strong>{{ item.subject }}</strong>
              <span>{{ item.detail }}</span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  </section>
</template>
