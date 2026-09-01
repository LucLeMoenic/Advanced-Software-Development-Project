<script setup lang="ts">
import { nextTick, ref } from 'vue'
import type { SearchResponse } from '../api'

defineProps<{
  search: SearchResponse
}>()

const heading = ref<HTMLElement | null>(null)

const currency = new Intl.NumberFormat('en-AU', {
  style: 'currency',
  currency: 'AUD',
  maximumFractionDigits: 2,
})

const dateFormatter = new Intl.DateTimeFormat('en-AU', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
})

function formatDate(value: string) {
  return dateFormatter.format(new Date(`${value}T00:00:00`))
}

function rankingLabel(mode: SearchResponse['rankingMode']) {
  if (mode === 'ai') {
    return 'AI-assisted match'
  }
  if (mode === 'programmatic') {
    return 'Budget match'
  }
  return 'Budget match (AI unavailable)'
}

async function focusHeading() {
  await nextTick()
  heading.value?.focus()
}

defineExpose({ focusHeading })
</script>

<template>
  <section class="results-section" aria-labelledby="results-heading">
    <div class="results-header">
      <div>
        <p class="section-label">Recommendations</p>
        <h2 id="results-heading" ref="heading" tabindex="-1">
          {{ search.title }}
        </h2>
        <p class="results-summary">
          {{ formatDate(search.checkIn) }} to {{ formatDate(search.checkOut) }}
          · {{ search.guests }} guest{{ search.guests === 1 ? '' : 's' }}
          · {{ currency.format(search.minimumPrice) }} to
          {{ currency.format(search.maximumPrice) }} nightly
        </p>
      </div>
      <div class="results-meta">
        <strong>{{ search.results.length }}</strong>
        <span>{{ search.results.length === 1 ? 'match' : 'matches' }}</span>
        <span :class="['mode-label', `mode-${search.rankingMode}`]">
          {{ rankingLabel(search.rankingMode) }}
        </span>
      </div>
    </div>

    <div v-if="search.notice" class="notice notice-warning" role="status">
      <strong>Reliable fallback used.</strong>
      <span>{{ search.notice }}</span>
    </div>

    <div v-if="search.importedProviderData" class="notice notice-information" role="status">
      <strong>New LiteAPI accommodation data imported.</strong>
      <span>The validated rates were cached in the local catalogue before ranking.</span>
    </div>
    <div v-if="search.results.length === 0" class="empty-state">
      <h3>No matching accommodation</h3>
      <p>Try a wider price range, another destination, or a different guest count.</p>
      <a class="text-link" href="#destination">Adjust search details</a>
    </div>

    <ol v-else class="results-list">
      <li
        v-for="result in search.results"
        :key="result.accommodationId"
        :class="['result-card', { 'result-card-first': result.rank === 1 }]"
      >
        <div class="rank">
          <span class="sr-only">
            Rank {{ result.rank }}{{ result.rank === 1 ? ', best match' : '' }}
          </span>
          <span aria-hidden="true">{{ result.rank }}</span>
          <small v-if="result.rank === 1" aria-hidden="true">Best match</small>
        </div>
        <div class="result-main">
          <div class="result-title-row">
            <div>
              <h3>{{ result.name }}</h3>
              <p>{{ result.destination }} · Up to {{ result.maxGuests }} guests</p>
            </div>
            <strong>{{ currency.format(result.nightlyPrice) }}<span>/night</span></strong>
          </div>
          <p class="reason">
            <span>Why it matches</span>
            {{ result.reason }}
          </p>
        </div>
      </li>
    </ol>
  </section>
</template>
