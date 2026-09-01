<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'
import {
  ApiRequestError,
  searchesApi,
  type SearchResponse,
  type SearchSummary,
} from '../api'

const emit = defineEmits<{
  opened: [search: SearchResponse]
  renamed: [search: SearchResponse]
  deleted: [id: number]
  error: [message: string]
  status: [message: string]
}>()

const panel = ref<HTMLElement | null>(null)
const history = ref<SearchSummary[]>([])
const loading = ref(true)
const loadError = ref('')
const activeId = ref<number | null>(null)
const editingId = ref<number | null>(null)
const renameTitle = ref('')
const renameError = ref('')

const dateFormatter = new Intl.DateTimeFormat('en-AU', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
})

function rankingLabel(mode: SearchSummary['rankingMode']) {
  if (mode === 'ai') {
    return 'AI-assisted'
  }
  if (mode === 'programmatic') {
    return 'Budget match'
  }
  return 'AI unavailable'
}

onMounted(loadHistory)

async function loadHistory() {
  loading.value = true
  loadError.value = ''
  emit('status', 'Loading saved searches.')

  try {
    const loadedHistory = await searchesApi.list()
    history.value = mergeNewestFirst(loadedHistory, history.value)
    emit(
      'status',
      history.value.length === 0
        ? 'No saved searches yet.'
        : `${history.value.length} saved searches loaded.`,
    )
  } catch (error) {
    loadError.value = getErrorMessage(error)
    emit('status', 'Search history could not be loaded.')
  } finally {
    loading.value = false
  }
}

async function reopenSearch(id: number) {
  activeId.value = id
  emit('status', 'Opening saved search.')

  try {
    const search = await searchesApi.get(id)
    emit('opened', search)
    emit('status', `Opened ${search.title} without reranking.`)
  } catch (error) {
    emit('error', getErrorMessage(error))
    emit('status', 'The saved search could not be opened.')
  } finally {
    activeId.value = null
  }
}

async function startRename(search: SearchSummary) {
  editingId.value = search.id
  renameTitle.value = search.title
  renameError.value = ''
  await nextTick()
  panel.value?.querySelector<HTMLInputElement>(`#rename-${search.id}`)?.focus()
}

async function cancelRename() {
  const id = editingId.value
  editingId.value = null
  renameTitle.value = ''
  renameError.value = ''
  await focusRenameButton(id)
}

async function saveRename(id: number) {
  const title = renameTitle.value.trim()
  if (title.length < 1 || title.length > 80) {
    renameError.value = 'Use between 1 and 80 characters.'
    emit('status', 'Use between 1 and 80 characters to rename the saved search.')
    await nextTick()
    panel.value?.querySelector<HTMLInputElement>(`#rename-${id}`)?.focus()
    return
  }

  activeId.value = id
  renameError.value = ''

  try {
    const renamed = await searchesApi.rename(id, title)
    addSearch(renamed)
    emit('renamed', renamed)
    await cancelRename()
    emit('status', `Renamed saved search to ${renamed.title}.`)
  } catch (error) {
    const requestError = error instanceof ApiRequestError ? error : null
    renameError.value = requestError?.fields.title ?? getErrorMessage(error)
    emit('status', 'The saved search could not be renamed.')
  } finally {
    activeId.value = null
  }
}

async function deleteSearch(search: SearchSummary) {
  const confirmed = window.confirm(`Delete "${search.title}"? This cannot be undone.`)
  if (!confirmed) {
    return
  }

  activeId.value = search.id
  try {
    await searchesApi.delete(search.id)
    history.value = history.value.filter((item) => item.id !== search.id)
    emit('deleted', search.id)
    emit('status', `Deleted ${search.title}.`)
    await nextTick()
    panel.value?.querySelector<HTMLElement>('.history-actions button')?.focus()
      ?? panel.value?.querySelector<HTMLElement>('#history-heading')?.focus()
  } catch (error) {
    emit('error', getErrorMessage(error))
    emit('status', 'The saved search could not be deleted.')
  } finally {
    activeId.value = null
  }
}

function addSearch(search: SearchResponse) {
  const summary: SearchSummary = {
    id: search.id,
    title: search.title,
    destination: search.destination,
    checkIn: search.checkIn,
    checkOut: search.checkOut,
    guests: search.guests,
    rankingMode: search.rankingMode,
    createdAt: search.createdAt,
    updatedAt: search.updatedAt,
  }

  history.value = mergeNewestFirst([summary], history.value)
}

function mergeNewestFirst(
  primary: SearchSummary[],
  secondary: SearchSummary[],
) {
  const searches = new Map<number, SearchSummary>()
  for (const search of [...secondary, ...primary]) {
    searches.set(search.id, search)
  }

  return [...searches.values()]
    .sort((left, right) => right.createdAt.localeCompare(left.createdAt))
}

function formatDate(value: string) {
  return dateFormatter.format(new Date(`${value}T00:00:00`))
}

function getErrorMessage(error: unknown) {
  return error instanceof Error
    ? error.message
    : 'The accommodation service could not complete the request.'
}

async function focusRenameButton(id: number | null) {
  if (id === null) {
    return
  }

  await nextTick()
  panel.value
    ?.querySelector<HTMLButtonElement>(`[data-rename-id="${id}"]`)
    ?.focus()
}

defineExpose({ addSearch })
</script>

<template>
  <aside
    ref="panel"
    class="history-panel"
    aria-labelledby="history-heading"
    :aria-busy="loading"
  >
    <div class="section-heading">
      <div>
        <p class="section-label">Your activity</p>
        <h2 id="history-heading" tabindex="-1">Saved searches</h2>
        <p class="section-copy">Open a stored result without ranking it again.</p>
      </div>
      <span class="count-label">{{ history.length }}</span>
    </div>

    <div v-if="loading" class="history-loading" aria-hidden="true">
      <span></span>
      <span></span>
      <span></span>
    </div>
    <div v-else-if="loadError" class="notice notice-error" role="alert">
      <span>{{ loadError }}</span>
      <button class="button button-small button-secondary" type="button" @click="loadHistory">
        Try again
      </button>
    </div>
    <div v-else-if="history.length === 0" class="history-empty">
      <strong>No saved searches yet</strong>
      <p>Your completed trips will appear here.</p>
    </div>

    <ol v-else class="history-list">
      <li v-for="search in history" :key="search.id" class="history-item">
        <form
          v-if="editingId === search.id"
          class="rename-form"
          @submit.prevent="saveRename(search.id)"
        >
          <label :for="`rename-${search.id}`">Rename {{ search.title }}</label>
          <input
            :id="`rename-${search.id}`"
            v-model="renameTitle"
            maxlength="80"
            :aria-invalid="Boolean(renameError)"
            :aria-describedby="renameError ? `rename-error-${search.id}` : undefined"
          >
          <span v-if="renameError" :id="`rename-error-${search.id}`" class="field-error">
            {{ renameError }}
          </span>
          <div class="history-actions">
            <button class="button button-small button-primary" :disabled="activeId === search.id">
              Save
            </button>
            <button class="button button-small button-quiet" type="button" @click="cancelRename">
              Cancel
            </button>
          </div>
        </form>

        <template v-else>
          <div class="history-title-row">
            <strong>{{ search.title }}</strong>
            <span :class="['mode-label', `mode-${search.rankingMode}`]">
              {{ rankingLabel(search.rankingMode) }}
            </span>
          </div>
          <p>
            {{ search.destination }} · {{ formatDate(search.checkIn) }} to {{ formatDate(search.checkOut) }}
            · {{ search.guests }} guest{{ search.guests === 1 ? '' : 's' }}
          </p>
          <div class="history-actions">
            <button
              class="button button-small button-secondary"
              type="button"
              :disabled="activeId === search.id"
              @click="reopenSearch(search.id)"
            >
              Reopen
            </button>
            <button
              class="button-link"
              type="button"
              :data-rename-id="search.id"
              @click="startRename(search)"
            >
              Rename
            </button>
            <button
              class="button-link button-link-danger"
              type="button"
              :disabled="activeId === search.id"
              @click="deleteSearch(search)"
            >
              Delete
            </button>
          </div>
        </template>
      </li>
    </ol>
  </aside>
</template>
