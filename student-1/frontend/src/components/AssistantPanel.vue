<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import {
  ApiRequestError,
  assistantApi,
  type AssistantMode,
  type LookupResponse,
} from '../api'

const emit = defineEmits<{
  status: [message: string]
}>()

const currency = new Intl.NumberFormat('en-AU', {
  style: 'currency',
  currency: 'AUD',
  maximumFractionDigits: 2,
})

const mode = ref<AssistantMode>('lookup')
const question = ref('')
const loading = ref(false)
const inputError = ref('')
const failure = ref<{ kind: 'rephrase' | 'disabled' | 'error'; message: string } | null>(null)
const lookup = ref<LookupResponse | null>(null)
const outcome = ref<HTMLElement | null>(null)

const rawResult = computed(() => (lookup.value ? JSON.stringify(lookup.value.result, null, 2) : ''))
const argumentEntries = computed(() => Object.entries(lookup.value?.arguments ?? {}))

async function ask() {
  if (loading.value) {
    return
  }

  const text = question.value.trim()
  if (text.length < 1 || text.length > 1000) {
    inputError.value = 'Enter a question of 1 to 1000 characters.'
    emit('status', 'Check the assistant question.')
    return
  }

  inputError.value = ''
  failure.value = null
  lookup.value = null
  loading.value = true
  emit('status', 'Looking up the catalogue.')

  try {
    lookup.value = await assistantApi.ask(mode.value, text)
    emit('status', lookupStatus(lookup.value))
  } catch (error) {
    failure.value = describeFailure(error)
    emit('status', failure.value.message)
  } finally {
    loading.value = false
    await nextTick()
    outcome.value?.focus()
  }
}

function lookupStatus(response: LookupResponse) {
  if (response.tool === 'accommodation.get_search') {
    return `Saved search ${response.result.search.id} is shown.`
  }
  return `${response.result.count} catalogue ${response.result.count === 1 ? 'stay' : 'stays'} found.`
}

function describeFailure(error: unknown) {
  const code = error instanceof ApiRequestError ? error.code : undefined
  const message = error instanceof Error ? error.message : 'The assistant could not answer.'
  if (code === 'lookup_not_understood') {
    return { kind: 'rephrase' as const, message }
  }
  if (code === 'mode_disabled') {
    return { kind: 'disabled' as const, message: 'Catalogue lookup is turned off in this environment.' }
  }
  return { kind: 'error' as const, message }
}

function formatPrice(value: number) {
  return currency.format(value)
}

function formatArgument(name: string, value: string | number) {
  return name === 'max_nightly_price' && typeof value === 'number' ? formatPrice(value) : String(value)
}
</script>

<template>
  <section class="panel assistant-panel" aria-labelledby="assistant-heading">
    <div class="section-heading">
      <div>
        <p class="section-label">Trip assistant</p>
        <h2 id="assistant-heading">Ask one question</h2>
        <p class="section-copy">
          Single question, no memory: each answer stands alone and nothing is saved.
        </p>
      </div>
    </div>

    <div class="assistant-body">
      <fieldset class="assistant-modes">
        <legend>Assistant mode</legend>
        <label class="mode-chip">
          <input v-model="mode" type="radio" name="assistant-mode" value="lookup">
          <span>
            <strong>Catalogue lookup</strong>
            <small>Find stays or open a saved search</small>
          </span>
        </label>
        <label class="mode-chip mode-chip-disabled">
          <input type="radio" name="assistant-mode" value="guide" disabled>
          <span>
            <strong>Destination guide</strong>
            <small>Coming soon</small>
          </span>
        </label>
      </fieldset>

      <div class="field assistant-question">
        <label for="assistant-question">Your question</label>
        <textarea
          id="assistant-question"
          v-model="question"
          rows="2"
          maxlength="1000"
          placeholder="e.g. Find stays in Tokyo for 2 guests under $200, or show saved search 11"
          :aria-invalid="Boolean(inputError)"
          :aria-describedby="inputError ? 'assistant-question-error' : undefined"
        />
        <span v-if="inputError" id="assistant-question-error" class="field-error">{{ inputError }}</span>
      </div>

      <div class="assistant-actions">
        <button
          class="button button-primary assistant-submit"
          type="button"
          :disabled="loading"
          :aria-busy="loading"
          @click="ask"
        >
          <span v-if="loading" class="spinner" aria-hidden="true" />
          {{ loading ? 'Asking…' : 'Ask' }}
        </button>
      </div>

      <div ref="outcome" class="assistant-outcome" tabindex="-1">
        <div
          v-if="failure"
          class="notice"
          :class="{
            'notice-warning': failure.kind === 'rephrase',
            'notice-information': failure.kind === 'disabled',
            'notice-error': failure.kind === 'error',
          }"
          role="alert"
        >
          <strong>{{ failure.kind === 'rephrase' ? 'Try asking another way.' : 'The assistant could not answer.' }}</strong>
          <span>{{ failure.message }}</span>
        </div>

        <div v-if="lookup" class="lookup-result">
          <dl class="lookup-call">
            <div>
              <dt>Tool</dt>
              <dd><code>{{ lookup.tool }}</code></dd>
            </div>
            <div v-for="[name, value] in argumentEntries" :key="name">
              <dt>{{ name }}</dt>
              <dd>{{ formatArgument(name, value) }}</dd>
            </div>
          </dl>

          <template v-if="lookup.tool === 'accommodation.find'">
            <p v-if="lookup.result.count === 0" class="notice notice-information">
              No active catalogue stays matched those details.
            </p>
            <div v-else class="table-scroll">
              <table class="lookup-table">
                <caption>{{ lookup.result.count }} catalogue {{ lookup.result.count === 1 ? 'stay' : 'stays' }}, cheapest first</caption>
                <thead>
                  <tr>
                    <th scope="col">Name</th>
                    <th scope="col">Destination</th>
                    <th scope="col">Nightly price</th>
                    <th scope="col">Max guests</th>
                    <th scope="col">Amenities</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="stay in lookup.result.accommodations" :key="stay.id">
                    <th scope="row">{{ stay.name }}</th>
                    <td>{{ stay.destination }}</td>
                    <td>{{ formatPrice(stay.nightlyPrice) }}</td>
                    <td>{{ stay.maxGuests }}</td>
                    <td>{{ stay.amenities.join(', ') }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </template>

          <template v-else>
            <h3 class="lookup-title">{{ lookup.result.search.title }}</h3>
            <p class="section-copy">
              {{ lookup.result.search.criteria.destination }} ·
              {{ lookup.result.search.criteria.checkIn }} to {{ lookup.result.search.criteria.checkOut }} ·
              {{ lookup.result.search.criteria.guests }} guests ·
              {{ formatPrice(lookup.result.search.criteria.minimumPrice) }}–{{ formatPrice(lookup.result.search.criteria.maximumPrice) }} ·
              {{ lookup.result.search.rankingMode }} ranking
            </p>
            <div class="table-scroll">
              <table class="lookup-table">
                <caption>Saved results in rank order</caption>
                <thead>
                  <tr>
                    <th scope="col">Rank</th>
                    <th scope="col">Name</th>
                    <th scope="col">Nightly price</th>
                    <th scope="col">Reason</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="item in lookup.result.search.results" :key="item.rank">
                    <td>{{ item.rank }}</td>
                    <th scope="row">{{ item.name }}</th>
                    <td>{{ formatPrice(item.nightlyPrice) }}</td>
                    <td>{{ item.reason }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </template>

          <details class="raw-result">
            <summary>Raw tool result</summary>
            <pre>{{ rawResult }}</pre>
          </details>
        </div>
      </div>
    </div>
  </section>
</template>
