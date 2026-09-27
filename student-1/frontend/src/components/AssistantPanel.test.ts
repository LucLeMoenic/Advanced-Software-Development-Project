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

const groundedResponse = {
  mode: 'guide',
  answer: 'Tokyo is generally considered very safe. <b>Bold</b> [tokyo#3]\n\nBarcelona nightlife starts late. [barcelona#2]',
  citations: [
    { source: 'Tokyo — Where to Stay', chunk_id: 'tokyo#3', snippet: 'Tokyo safety: Tokyo is generally considered a very safe city.', score: 0.4632 },
    { source: 'Barcelona — Where to Stay', chunk_id: 'barcelona#2', snippet: 'Barcelona who it suits: nightlife starts late.', score: 0.281 },
  ],
  confidence: 'low',
}

const insufficientResponse = {
  mode: 'guide',
  answer: 'Not enough information in the knowledge base to answer this.',
  citations: [],
  confidence: 'insufficient',
}

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn())
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('AssistantPanel', () => {
  it('labels the panel as single-question with two explicit modes and lookup selected', () => {
    const wrapper = mount(AssistantPanel)

    expect(wrapper.text()).toContain('Single question, no memory')
    expect(wrapper.get<HTMLInputElement>('input[value="lookup"]').element.checked).toBe(true)
    expect(wrapper.get('input[value="guide"]').attributes('disabled')).toBeUndefined()
  })

  it('sends a guide question and renders the answer, markers as text, citations and badge', async () => {
    respond(groundedResponse)
    const wrapper = mount(AssistantPanel)

    await wrapper.get('input[value="guide"]').setValue(true)
    await wrapper.get('#assistant-question').setValue('Is Tokyo safe? Barcelona nightlife?')
    await wrapper.get('.assistant-submit').trigger('click')
    await flushPromises()

    const [, init] = vi.mocked(fetch).mock.calls[0]!
    expect(JSON.parse(init?.body as string)).toEqual({ mode: 'guide', question: 'Is Tokyo safe? Barcelona nightlife?' })
    const answer = wrapper.get('.guide-answer')
    expect(answer.text()).toContain('[tokyo#3]')
    expect(answer.text()).toContain('<b>Bold</b>')
    expect(answer.find('b').exists()).toBe(false)
    expect(wrapper.get('.confidence-badge').text()).toBe('low confidence')
    expect(wrapper.get('.confidence-badge').classes()).toContain('confidence-low')
    const citations = wrapper.findAll('.guide-citations li')
    expect(citations).toHaveLength(2)
    expect(citations[0]!.text()).toContain('Tokyo — Where to Stay')
    expect(citations[0]!.text()).toContain('[tokyo#3]')
    expect(citations[0]!.text()).toContain('Tokyo safety: Tokyo is generally considered a very safe city.')
    expect(wrapper.emitted('status')!.at(-1)).toEqual(['Answer ready with low confidence and 2 sources.'])
  })

  it('offers one pre-fill action per cited catalogue city', async () => {
    respond(groundedResponse)
    const wrapper = mount(AssistantPanel)

    await wrapper.get('input[value="guide"]').setValue(true)
    await wrapper.get('#assistant-question').setValue('Is Tokyo safe?')
    await wrapper.get('.assistant-submit').trigger('click')
    await flushPromises()

    const actions = wrapper.findAll('.guide-actions button')
    expect(actions.map((button) => button.text())).toEqual([
      'Search accommodation in Tokyo',
      'Search accommodation in Barcelona',
    ])
    await actions[1]!.trigger('click')
    expect(wrapper.emitted('prefill')).toEqual([['Barcelona']])
  })

  it('does not map sources that are not exact catalogue guide titles', async () => {
    respond({
      ...groundedResponse,
      citations: [{ source: 'Bali — Where to Stay', chunk_id: 'bali#1', snippet: 'Bali.', score: 0.3 }],
      answer: 'Bali. [bali#1]',
    })
    const wrapper = mount(AssistantPanel)

    await wrapper.get('input[value="guide"]').setValue(true)
    await wrapper.get('#assistant-question').setValue('Bali?')
    await wrapper.get('.assistant-submit').trigger('click')
    await flushPromises()

    expect(wrapper.find('.guide-actions').exists()).toBe(false)
  })

  it('shows a distinct insufficient-context state without citations', async () => {
    respond(insufficientResponse)
    const wrapper = mount(AssistantPanel)

    await wrapper.get('input[value="guide"]').setValue(true)
    await wrapper.get('#assistant-question').setValue('Tell me about Bali')
    await wrapper.get('.assistant-submit').trigger('click')
    await flushPromises()

    expect(wrapper.get('.guide-insufficient').text()).toContain('Not covered by the destination guides.')
    expect(wrapper.get('.guide-insufficient').text()).toContain('Not enough information in the knowledge base')
    expect(wrapper.find('.guide-citations').exists()).toBe(false)
    expect(wrapper.find('.confidence-badge').exists()).toBe(false)
    expect(wrapper.emitted('status')!.at(-1)).toEqual(['The destination guides do not cover that question.'])
  })

  it('clears the previous answer when the mode changes', async () => {
    respond(findResponse)
    const wrapper = mount(AssistantPanel)

    await wrapper.get('#assistant-question').setValue('Stays in Tokyo')
    await wrapper.get('.assistant-submit').trigger('click')
    await flushPromises()
    await wrapper.get('input[value="guide"]').setValue(true)

    expect(wrapper.find('.lookup-result').exists()).toBe(false)
  })

  it('names the disabled guide mode', async () => {
    respond({ error: { code: 'mode_disabled', message: 'Destination guide is disabled.', fields: {} } }, 503)
    const wrapper = mount(AssistantPanel)

    await wrapper.get('input[value="guide"]').setValue(true)
    await wrapper.get('#assistant-question').setValue('Is Tokyo safe?')
    await wrapper.get('.assistant-submit').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Destination guide is turned off in this environment.')
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
