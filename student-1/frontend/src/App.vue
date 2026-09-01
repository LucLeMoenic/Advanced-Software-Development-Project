<script setup lang="ts">
import { nextTick, ref } from 'vue'
import {
  ApiRequestError,
  searchesApi,
  type SearchRequest,
  type SearchResponse,
} from './api'
import SearchForm from './components/SearchForm.vue'
import SearchHistory from './components/SearchHistory.vue'
import SearchResults from './components/SearchResults.vue'

const currentSearch = ref<SearchResponse | null>(null)
const pageError = ref('')
const serverErrors = ref<Record<string, string>>({})
const statusMessage = ref('Search history is loading.')
const submitting = ref(false)
const errorSummary = ref<HTMLElement | null>(null)
const searchForm = ref<InstanceType<typeof SearchForm> | null>(null)
const searchHistory = ref<InstanceType<typeof SearchHistory> | null>(null)
const searchResults = ref<InstanceType<typeof SearchResults> | null>(null)

async function submitSearch(search: SearchRequest) {
  if (submitting.value) {
    return
  }

  pageError.value = ''
  serverErrors.value = {}
  submitting.value = true
  statusMessage.value = 'Searching for accommodation.'

  try {
    const savedSearch = await searchesApi.create(search)
    currentSearch.value = savedSearch
    searchHistory.value?.addSearch(savedSearch)

    if (savedSearch.results.length === 0) {
      statusMessage.value = 'No matching accommodation was found.'
    } else if (savedSearch.rankingMode === 'fallback') {
      statusMessage.value = `${savedSearch.results.length} accommodations are ready using budget ranking because AI was unavailable.`
    } else if (savedSearch.rankingMode === 'programmatic') {
      statusMessage.value = `${savedSearch.results.length} budget-ranked accommodations are ready.`
    } else {
      statusMessage.value = `${savedSearch.results.length} AI-assisted accommodations are ready.`
    }

    await focusResults()
  } catch (error) {
    const requestError = error instanceof ApiRequestError ? error : null
    serverErrors.value = requestError?.fields ?? {}
    showError(getErrorMessage(error), 'The search could not be completed.')

    if (Object.keys(serverErrors.value).length > 0) {
      await searchForm.value?.focusFirstInvalid()
    } else {
      await focusError()
    }
  } finally {
    submitting.value = false
  }
}

function showSearch(search: SearchResponse) {
  pageError.value = ''
  currentSearch.value = search
  void focusResults()
}

function updateRenamedSearch(search: SearchResponse) {
  if (currentSearch.value?.id === search.id) {
    currentSearch.value = search
  }
}

function clearDeletedSearch(id: number) {
  if (currentSearch.value?.id === id) {
    currentSearch.value = null
  }
}

function showError(message: string, status = 'The action could not be completed.') {
  pageError.value = message
  statusMessage.value = status
  void focusError()
}

function getErrorMessage(error: unknown) {
  return error instanceof Error
    ? error.message
    : 'The accommodation service could not complete the request.'
}

async function focusResults() {
  await nextTick()
  await searchResults.value?.focusHeading()
}

async function focusError() {
  await nextTick()
  errorSummary.value?.focus()
}
</script>

<template>
  <header class="app-header">
    <div class="app-header-inner">
      <a class="product-name" href="/accommodation/">Accommodation Recommender</a>
      <nav class="page-navigation" aria-label="Application navigation">
        <a href="/">All features</a>
      </nav>
    </div>
  </header>

  <main class="page-shell">
    <header class="page-intro">
      <p class="page-kicker">Plan and compare</p>
      <h1>Find a stay that fits the trip</h1>
      <p class="hero-copy">
        Search by the details that matter, compare ranked options, and return to
        saved results without running the search again.
      </p>
    </header>

    <p class="sr-only" role="status" aria-live="polite">{{ statusMessage }}</p>

    <div
      v-if="pageError"
      ref="errorSummary"
      class="notice notice-error page-error"
      role="alert"
      tabindex="-1"
    >
      <strong>We could not complete that action.</strong>
      <span>{{ pageError }}</span>
    </div>

    <SearchForm
      ref="searchForm"
      :submitting="submitting"
      :server-errors="serverErrors"
      @submit="submitSearch"
      @invalid="statusMessage = 'Check the highlighted search fields.'"
    />

    <div class="workspace">
      <SearchResults
        v-if="currentSearch"
        ref="searchResults"
        :search="currentSearch"
      />
      <section v-else class="results-placeholder" aria-labelledby="results-placeholder-heading">
        <p class="section-label">Recommendations</p>
        <h2 id="results-placeholder-heading">Your matches will appear here</h2>
        <p>
          Complete the search above to compare eligible stays by price and fit.
        </p>
        <a class="text-link" href="#destination">Enter stay details</a>
      </section>

      <SearchHistory
        ref="searchHistory"
        @opened="showSearch"
        @renamed="updateRenamedSearch"
        @deleted="clearDeletedSearch"
        @error="showError"
        @status="statusMessage = $event"
      />
    </div>
  </main>
</template>
