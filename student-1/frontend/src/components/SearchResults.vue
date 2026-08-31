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

async function focusHeading() {
  await nextTick()
  heading.value?.focus()
}

defineExpose({ focusHeading })
</script>

<template>
  <section class="results-section" aria-labelledby="results-heading">
    <div class="results-heading-row">
      <div>
        <p class="eyebrow">Saved recommendation</p>
        <h2 id="results-heading" ref="heading" tabindex="-1">
          {{ search.title }}
        </h2>
        <p class="results-summary">
          {{ formatDate(search.checkIn) }} - {{ formatDate(search.checkOut) }}
          · {{ search.guests }} guest{{ search.guests === 1 ? '' : 's' }}
          · {{ currency.format(search.minimumPrice) }} to
          {{ currency.format(search.maximumPrice) }} nightly
        </p>
      </div>
      <span :class="['mode-badge', `mode-${search.rankingMode}`]">
        {{ search.rankingMode === 'ai' ? 'AI ranked' : 'Fallback ranked' }}
      </span>
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
      <span aria-hidden="true">0</span>
      <h3>No matching accommodation</h3>
      <p>Try a wider price range, another destination, or a different guest count.</p>
    </div>

    <ol v-else class="results-list">
      <li v-for="result in search.results" :key="result.accommodationId" class="result-card">
        <div class="rank" :aria-label="`Rank ${result.rank}`">{{ result.rank }}</div>
        <div class="result-main">
          <div class="result-title-row">
            <div>
              <h3>{{ result.name }}</h3>
              <p>{{ result.destination }} · Up to {{ result.maxGuests }} guests</p>
            </div>
            <strong>{{ currency.format(result.nightlyPrice) }}<span>/night</span></strong>
          </div>
          <p class="reason">{{ result.reason }}</p>
        </div>
      </li>
    </ol>
  </section>
</template>
