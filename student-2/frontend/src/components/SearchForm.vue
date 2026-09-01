<script setup lang="ts">
import { computed, nextTick, reactive, ref } from 'vue'
import type { SearchRequest } from '../api'

interface SearchFormValues {
  destination: string
  checkIn: string
  checkOut: string
  guests: string
  minimumPrice: string
  maximumPrice: string
  preferences: string
  useAi: boolean
}

const props = defineProps<{
  submitting: boolean
  serverErrors: Record<string, string>
}>()

const emit = defineEmits<{
  submit: [search: SearchRequest]
  invalid: []
}>()

const form = reactive<SearchFormValues>({
  destination: '',
  checkIn: '',
  checkOut: '',
  guests: '2',
  minimumPrice: '',
  maximumPrice: '',
  preferences: '',
  useAi: false,
})

const clientErrors = ref<Record<string, string>>({})
const errors = computed(() => ({ ...props.serverErrors, ...clientErrors.value }))
const today = toDateInputValue(new Date())

async function submitForm() {
  if (props.submitting) {
    return
  }

  clientErrors.value = validateForm()
  if (Object.keys(clientErrors.value).length > 0) {
    emit('invalid')
    await focusFirstInvalid()
    return
  }

  emit('submit', {
    destination: form.destination.trim(),
    checkIn: form.checkIn,
    checkOut: form.checkOut,
    guests: Number(form.guests),
    minimumPrice: Number(form.minimumPrice),
    maximumPrice: Number(form.maximumPrice),
    preferences: form.useAi ? form.preferences.trim() : '',
    useAi: form.useAi,
  })
}

function validateForm(): Record<string, string> {
  const validationErrors: Record<string, string> = {}
  const destination = form.destination.trim()
  const guests = Number(form.guests)
  const minimumPrice = Number(form.minimumPrice)
  const maximumPrice = Number(form.maximumPrice)

  if (destination.length < 2 || destination.length > 100) {
    validationErrors.destination = 'Use between 2 and 100 characters.'
  }
  if (!form.checkIn || form.checkIn < today) {
    validationErrors.checkIn = 'Choose today or a future date.'
  }
  if (!form.checkOut || form.checkOut <= form.checkIn) {
    validationErrors.checkOut = 'Choose a date after check-in.'
  }
  if (!Number.isInteger(guests) || guests < 1 || guests > 20) {
    validationErrors.guests = 'Enter a whole number from 1 to 20.'
  }
  if (form.minimumPrice === '' || minimumPrice < 0 || minimumPrice > 100000) {
    validationErrors.minimumPrice = 'Enter an amount from 0 to 100,000.'
  }
  if (form.maximumPrice === '' || maximumPrice < 0 || maximumPrice > 100000) {
    validationErrors.maximumPrice = 'Enter an amount from 0 to 100,000.'
  }
  if (
    !validationErrors.minimumPrice
    && !validationErrors.maximumPrice
    && minimumPrice > maximumPrice
  ) {
    validationErrors.minimumPrice = 'Minimum price cannot exceed maximum price.'
  }
  if (form.useAi && form.preferences.length > 500) {
    validationErrors.preferences = 'Use 500 characters or fewer.'
  }

  return validationErrors
}

async function focusFirstInvalid() {
  await nextTick()
  document.querySelector<HTMLElement>('.search-panel [aria-invalid="true"]')?.focus()
}

function toDateInputValue(date: Date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

defineExpose({ focusFirstInvalid })
</script>

<template>
  <section class="panel search-panel" aria-labelledby="search-heading">
    <div class="section-heading">
      <div>
        <p class="section-label">New search</p>
        <h2 id="search-heading">Where are you staying?</h2>
        <p class="section-copy">Add the trip details, then choose how results should be ranked.</p>
      </div>
    </div>

    <form novalidate @submit.prevent="submitForm">
      <fieldset class="form-section">
        <legend>Stay details</legend>
        <div class="stay-grid">
          <div class="field destination-field">
            <label for="destination">Destination</label>
            <input
              id="destination"
              v-model="form.destination"
              name="destination"
              autocomplete="address-level2"
              maxlength="100"
              placeholder="City or destination"
              :aria-invalid="Boolean(errors.destination)"
              :aria-describedby="errors.destination ? 'destination-error' : undefined"
            >
            <span v-if="errors.destination" id="destination-error" class="field-error">
              {{ errors.destination }}
            </span>
          </div>

          <div class="field">
            <label for="check-in">Check-in</label>
            <input
              id="check-in"
              v-model="form.checkIn"
              name="checkIn"
              type="date"
              :min="today"
              :aria-invalid="Boolean(errors.checkIn)"
              :aria-describedby="errors.checkIn ? 'check-in-error' : undefined"
            >
            <span v-if="errors.checkIn" id="check-in-error" class="field-error">
              {{ errors.checkIn }}
            </span>
          </div>

          <div class="field">
            <label for="check-out">Check-out</label>
            <input
              id="check-out"
              v-model="form.checkOut"
              name="checkOut"
              type="date"
              :min="form.checkIn || today"
              :aria-invalid="Boolean(errors.checkOut)"
              :aria-describedby="errors.checkOut ? 'check-out-error' : undefined"
            >
            <span v-if="errors.checkOut" id="check-out-error" class="field-error">
              {{ errors.checkOut }}
            </span>
          </div>

          <div class="field">
            <label for="guests">Guests</label>
            <input
              id="guests"
              v-model="form.guests"
              name="guests"
              type="number"
              min="1"
              max="20"
              step="1"
              inputmode="numeric"
              :aria-invalid="Boolean(errors.guests)"
              :aria-describedby="errors.guests ? 'guests-error' : undefined"
            >
            <span v-if="errors.guests" id="guests-error" class="field-error">
              {{ errors.guests }}
            </span>
          </div>
        </div>
      </fieldset>

      <fieldset class="form-section budget-section">
        <legend>Nightly budget</legend>
        <div class="budget-grid">
          <div class="field">
            <label for="minimum-price">Minimum<span class="sr-only"> nightly price</span></label>
            <div class="money-input">
              <span aria-hidden="true">$</span>
              <input
                id="minimum-price"
                v-model="form.minimumPrice"
                name="minimumPrice"
                type="number"
                min="0"
                max="100000"
                step="0.01"
                inputmode="decimal"
                placeholder="0"
                :aria-invalid="Boolean(errors.minimumPrice)"
                :aria-describedby="errors.minimumPrice ? 'minimum-price-error' : undefined"
              >
            </div>
            <span v-if="errors.minimumPrice" id="minimum-price-error" class="field-error">
              {{ errors.minimumPrice }}
            </span>
          </div>

          <span class="budget-separator" aria-hidden="true">to</span>

          <div class="field">
            <label for="maximum-price">Maximum<span class="sr-only"> nightly price</span></label>
            <div class="money-input">
              <span aria-hidden="true">$</span>
              <input
                id="maximum-price"
                v-model="form.maximumPrice"
                name="maximumPrice"
                type="number"
                min="0"
                max="100000"
                step="0.01"
                inputmode="decimal"
                placeholder="500"
                :aria-invalid="Boolean(errors.maximumPrice)"
                :aria-describedby="errors.maximumPrice ? 'maximum-price-error' : undefined"
              >
            </div>
            <span v-if="errors.maximumPrice" id="maximum-price-error" class="field-error">
              {{ errors.maximumPrice }}
            </span>
          </div>
          <span class="budget-suffix">AUD per night</span>
        </div>
      </fieldset>

      <fieldset class="form-section ranking-section">
        <legend>Ranking method</legend>
        <div class="ranking-options">
          <label class="ranking-option" for="standard-ranking">
            <input
              id="standard-ranking"
              v-model="form.useAi"
              name="rankingMethod"
              type="radio"
              :value="false"
            >
            <span>
              <strong>Budget match</strong>
              <small>Fast, predictable ranking based on budget and nightly price.</small>
            </span>
          </label>

          <label class="ranking-option" for="use-ai">
            <input
              id="use-ai"
              v-model="form.useAi"
              name="rankingMethod"
              type="radio"
              :value="true"
            >
            <span>
              <strong>AI-assisted match</strong>
              <small>Uses your preferences to explain and order eligible stays.</small>
            </span>
          </label>
        </div>

        <div v-if="form.useAi" class="field preferences-field">
          <div class="label-row">
            <label for="preferences">What matters to you?</label>
            <span>{{ form.preferences.length }}/500</span>
          </div>
          <textarea
            id="preferences"
            v-model="form.preferences"
            name="preferences"
            rows="3"
            maxlength="500"
            placeholder="For example: quiet at night, accessible entrance, close to public transport"
            :aria-invalid="Boolean(errors.preferences)"
            :aria-describedby="errors.preferences ? 'preferences-error preferences-help' : 'preferences-help'"
          />
          <span id="preferences-help" class="field-help">
            Preferences are stored with this saved search and removed when the search is deleted.
          </span>
          <span v-if="errors.preferences" id="preferences-error" class="field-error">
            {{ errors.preferences }}
          </span>
        </div>
      </fieldset>

      <div class="form-actions">
        <p>Completed searches are saved automatically.</p>
        <button class="button button-primary submit-button" type="submit" :disabled="submitting">
          <span v-if="submitting" class="spinner" aria-hidden="true"></span>
          {{ submitting ? 'Finding stays...' : 'Show recommendations' }}
        </button>
      </div>
    </form>
  </section>
</template>
