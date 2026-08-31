import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App.vue'

const savedSearch = {
  id: 1,
  title: 'Sydney',
  destination: 'Sydney',
  checkIn: '2026-09-10',
  checkOut: '2026-09-12',
  guests: 2,
  minimumPrice: 100,
  maximumPrice: 300,
  preferences: 'Near transport',
  rankingMode: 'ai',
  results: [
    {
      accommodationId: 7,
      name: 'Harbour Stay',
      destination: 'Sydney',
      nightlyPrice: 210,
      maxGuests: 4,
      rank: 1,
      reason: 'Matches the requested budget and transport preference.',
    },
  ],
  createdAt: '2026-08-31T10:00:00Z',
  updatedAt: '2026-08-31T10:00:00Z',
  notice: null,
} as const

const summary = {
  id: savedSearch.id,
  title: savedSearch.title,
  destination: savedSearch.destination,
  checkIn: savedSearch.checkIn,
  checkOut: savedSearch.checkOut,
  guests: savedSearch.guests,
  rankingMode: savedSearch.rankingMode,
  createdAt: savedSearch.createdAt,
  updatedAt: savedSearch.updatedAt,
}

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn())
  vi.stubGlobal('confirm', vi.fn(() => true))
})

afterEach(() => {
  document.body.innerHTML = ''
  vi.unstubAllGlobals()
})

describe('App', () => {
  it('shows field feedback and does not submit invalid input', async () => {
    mockFetch(jsonResponse([]))
    const wrapper = mount(App, { attachTo: document.body })
    await flushPromises()

    await wrapper.get('form').trigger('submit')

    expect(wrapper.text()).toContain('Use between 2 and 100 characters.')
    expect(wrapper.get('#destination').attributes('aria-invalid')).toBe('true')
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  it('prevents duplicate submission and renders AI results', async () => {
    let resolveSearch!: (response: Response) => void
    const searchResponse = new Promise<Response>((resolve) => {
      resolveSearch = resolve
    })
    mockFetch(jsonResponse([]), searchResponse)
    const wrapper = mount(App, { attachTo: document.body })
    await flushPromises()
    await fillValidForm(wrapper)

    await wrapper.get('form').trigger('submit')
    await wrapper.get('form').trigger('submit')

    expect(fetch).toHaveBeenCalledTimes(2)
    expect(wrapper.get('.submit-button').attributes('disabled')).toBeDefined()

    resolveSearch(jsonResponse(savedSearch, 201))
    await flushPromises()

    expect(wrapper.text()).toContain('Harbour Stay')
    expect(wrapper.text()).toContain('AI ranked')
  })

  it('keeps a newly completed search when the initial history request finishes later', async () => {
    let resolveHistory!: (response: Response) => void
    const historyResponse = new Promise<Response>((resolve) => {
      resolveHistory = resolve
    })
    mockFetch(historyResponse, jsonResponse(savedSearch, 201))
    const wrapper = mount(App)
    await fillValidForm(wrapper)

    await wrapper.get('.search-panel form').trigger('submit')
    await flushPromises()
    resolveHistory(jsonResponse([]))
    await flushPromises()

    expect(wrapper.text()).toContain('Sydney')
    expect(wrapper.findAll('.history-item')).toHaveLength(1)
  })

  it('renders fallback, empty, and dependency-error states', async () => {
    const fallback = {
      ...savedSearch,
      rankingMode: 'fallback',
      notice: 'AI ranking was unavailable, so deterministic fallback ranking was used.',
    }
    const empty = { ...savedSearch, id: 2, results: [], rankingMode: 'fallback' }
    const dependencyError = {
      error: {
        message: 'The database service is unavailable.',
        fields: {},
      },
    }
    mockFetch(
      jsonResponse([]),
      jsonResponse(fallback, 201),
      jsonResponse(empty),
      jsonResponse(dependencyError, 503),
    )
    const wrapper = mount(App)
    await flushPromises()
    await fillValidForm(wrapper)

    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(wrapper.text()).toContain('Reliable fallback used.')

    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(wrapper.text()).toContain('No matching accommodation')

    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(wrapper.text()).toContain('The database service is unavailable.')
  })

  it('reopens a saved search without creating a new ranking request', async () => {
    mockFetch(jsonResponse([summary]), jsonResponse(savedSearch))
    const wrapper = mount(App)
    await flushPromises()

    await wrapper.get('.history-actions .button-secondary').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Harbour Stay')
    expect(fetch).toHaveBeenNthCalledWith(2, '/api/searches/1', undefined)
  })

  it('renames the displayed search and confirms deletion of saved history', async () => {
    const renamed = { ...savedSearch, title: 'Anniversary trip' }
    mockFetch(
      jsonResponse([summary]),
      jsonResponse(savedSearch),
      jsonResponse(renamed),
      new Response(null, { status: 204 }),
    )
    const wrapper = mount(App, { attachTo: document.body })
    await flushPromises()

    await wrapper.get('.button-secondary').trigger('click')
    await flushPromises()
    const historyButtons = wrapper.findAll('.history-actions button')
    await historyButtons[1]!.trigger('click')
    expect(document.activeElement).toBe(wrapper.get('.rename-form input').element)

    await wrapper.get('.rename-form input').setValue('Anniversary trip')
    await wrapper.get('.rename-form').trigger('submit')
    await flushPromises()

    expect(wrapper.get('#results-heading').text()).toContain('Anniversary trip')
    expect(fetch).toHaveBeenNthCalledWith(3, '/api/searches/1', expect.objectContaining({
      method: 'PATCH',
    }))
    expect(document.activeElement).toBe(wrapper.get('[data-rename-id="1"]').element)

    await wrapper.get('.button-danger').trigger('click')
    await flushPromises()

    expect(confirm).toHaveBeenCalledOnce()
    expect(wrapper.text()).toContain('Completed searches will appear here.')
    expect(fetch).toHaveBeenNthCalledWith(4, '/api/searches/1', { method: 'DELETE' })
    expect(document.activeElement).toBe(wrapper.get('#history-heading').element)
  })

  it('focuses and announces invalid rename input', async () => {
    mockFetch(jsonResponse([summary]))
    const wrapper = mount(App, { attachTo: document.body })
    await flushPromises()

    await wrapper.get('[data-rename-id="1"]').trigger('click')
    await wrapper.get('.rename-form input').setValue('')
    await wrapper.get('.rename-form').trigger('submit')
    await flushPromises()

    expect(document.activeElement).toBe(wrapper.get('.rename-form input').element)
    expect(wrapper.get('[role="status"]').text()).toContain('1 and 80 characters')
  })
})

function mockFetch(...responses: Array<Response | Promise<Response>>) {
  const fetchMock = vi.mocked(fetch)
  for (const response of responses) {
    fetchMock.mockImplementationOnce(() => Promise.resolve(response))
  }
}

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

async function fillValidForm(wrapper: ReturnType<typeof mount>) {
  await wrapper.get('#destination').setValue('Sydney')
  await wrapper.get('#check-in').setValue('2026-09-10')
  await wrapper.get('#check-out').setValue('2026-09-12')
  await wrapper.get('#guests').setValue('2')
  await wrapper.get('#minimum-price').setValue('100')
  await wrapper.get('#maximum-price').setValue('300')
  await wrapper.get('#preferences').setValue('Near transport')
}
