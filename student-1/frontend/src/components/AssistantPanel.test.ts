import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import AssistantPanel from './AssistantPanel.vue'

const findResponse = {
  mode: 'lookup',
  tool: 'accommodation.find',
  arguments: { destination: 'Tokyo', guests: 2, max_nightly_price: 200 },
  result: {
    ok: true,
    count: 1,
    accommodations: [
      {
        id: 55,
        name: '<img src=x onerror=alert(1)> Lodge',
        destination: 'Tokyo',
        nightlyPrice: 145,
        maxGuests: 4,
        amenities: ['Near metro', 'Free WiFi'],
      },
    ],
  },
}

const searchResponse = {
  mode: 'lookup',
  tool: 'accommodation.get_search',
  arguments: { search_id: 11 },
  result: {
    ok: true,
    search: {
      id: 11,
      title: 'Tokyo Culture and Food',
      criteria: {
        destination: 'Tokyo',
        checkIn: '2026-09-15',
        checkOut: '2026-09-20',
        guests: 2,
        minimumPrice: 140,
        maximumPrice: 260,
      },
      rankingMode: 'ai',
      results: [
        { rank: 1, accommodationId: 51, name: 'Asakusa Lantern Hotel', nightlyPrice: 168, reason: 'Best overall match.' },
      ],
    },
  },
}

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn())
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('AssistantPanel', () => {
  it('labels the panel as single-question with lookup active and guide coming soon', () => {
    const wrapper = mount(AssistantPanel)

    expect(wrapper.text()).toContain('Single question, no memory')
    expect(wrapper.get<HTMLInputElement>('input[value="lookup"]').element.checked).toBe(true)
    expect(wrapper.get('input[value="guide"]').attributes('disabled')).toBeDefined()
    expect(wrapper.text()).toContain('Coming soon')
  })

  it('sends one lookup question and renders the tool, arguments and results as text', async () => {
    respond(findResponse)
    const wrapper = mount(AssistantPanel)

    await wrapper.get('#assistant-question').setValue('  Stays in Tokyo for 2 under $200  ')
    await wrapper.get('.assistant-submit').trigger('click')
    await flushPromises()

    const [path, init] = vi.mocked(fetch).mock.calls[0]!
    expect(path).toBe('/api/assistant')
    expect(JSON.parse(init?.body as string)).toEqual({ mode: 'lookup', question: 'Stays in Tokyo for 2 under $200' })
    expect(wrapper.text()).toContain('accommodation.find')
    expect(wrapper.text()).toContain('max_nightly_price')
    expect(wrapper.text()).toContain('$200.00')
    expect(wrapper.text()).toContain('$145.00')
    expect(wrapper.text()).toContain('Near metro, Free WiFi')
    expect(wrapper.find('img').exists()).toBe(false)
    expect(wrapper.get('.lookup-table').text()).toContain('<img src=x onerror=alert(1)> Lodge')
    expect(wrapper.emitted('status')!.at(-1)).toEqual(['1 catalogue stay found.'])
    expect(wrapper.get('.raw-result pre').text()).toContain('"accommodations"')
  })

  it('renders a saved search lookup', async () => {
    respond(searchResponse)
    const wrapper = mount(AssistantPanel)

    await wrapper.get('#assistant-question').setValue('Show saved search 11')
    await wrapper.get('.assistant-submit').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('accommodation.get_search')
    expect(wrapper.text()).toContain('Tokyo Culture and Food')
    expect(wrapper.text()).toContain('Asakusa Lantern Hotel')
    expect(wrapper.text()).toContain('Best overall match.')
  })

  it('shows an empty catalogue state', async () => {
    respond({ ...findResponse, result: { ok: true, count: 0, accommodations: [] } })
    const wrapper = mount(AssistantPanel)

    await wrapper.get('#assistant-question').setValue('Stays in Tokyo')
    await wrapper.get('.assistant-submit').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('No active catalogue stays matched')
    expect(wrapper.find('.lookup-table').exists()).toBe(false)
  })

  it('does not send a blank question', async () => {
    const wrapper = mount(AssistantPanel)

    await wrapper.get('#assistant-question').setValue('   ')
    await wrapper.get('.assistant-submit').trigger('click')

    expect(fetch).not.toHaveBeenCalled()
    expect(wrapper.get('#assistant-question').attributes('aria-invalid')).toBe('true')
  })

  it('prevents duplicate submission while a question is pending', async () => {
    let resolve!: (response: Response) => void
    vi.mocked(fetch).mockImplementationOnce(() => new Promise((done) => { resolve = done }))
    const wrapper = mount(AssistantPanel)

    await wrapper.get('#assistant-question').setValue('Stays in Tokyo')
    await wrapper.get('.assistant-submit').trigger('click')
    await wrapper.get('.assistant-submit').trigger('click')

    expect(fetch).toHaveBeenCalledTimes(1)
    expect(wrapper.get('.assistant-submit').attributes('disabled')).toBeDefined()
    resolve(json(findResponse))
    await flushPromises()
    expect(wrapper.get('.assistant-submit').attributes('disabled')).toBeUndefined()
  })

  it.each([
    ['lookup_not_understood', 422, 'Please rephrase, e.g. "Find stays in Tokyo"', 'notice-warning', 'Please rephrase'],
    ['mode_disabled', 503, 'Catalogue lookup is disabled.', 'notice-information', 'turned off'],
    ['dependency_timeout', 504, 'The assistant service timed out.', 'notice-error', 'timed out'],
  ])('shows a distinct %s state', async (code, status, message, noticeClass, expected) => {
    respond({ error: { code, message, fields: {} } }, status)
    const wrapper = mount(AssistantPanel)

    await wrapper.get('#assistant-question').setValue('What is the weather?')
    await wrapper.get('.assistant-submit').trigger('click')
    await flushPromises()

    expect(wrapper.get('[role="alert"]').classes()).toContain(noticeClass)
    expect(wrapper.text()).toContain(expected)
    expect(wrapper.find('.lookup-result').exists()).toBe(false)
  })
})

function respond(body: unknown, status = 200) {
  vi.mocked(fetch).mockImplementationOnce(() => Promise.resolve(json(body, status)))
}

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}
