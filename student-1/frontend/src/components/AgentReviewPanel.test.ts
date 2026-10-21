import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiRequestError, reviewsApi, type ReviewRecord, type SearchResponse } from '../api'
import AgentReviewPanel from './AgentReviewPanel.vue'

vi.mock('../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api')>()),
  reviewsApi: { start: vi.fn(), list: vi.fn(), get: vi.fn(), decide: vi.fn() },
}))

const search: SearchResponse = {
  id: 11,
  title: 'Tokyo',
  destination: 'Tokyo',
  checkIn: '2026-11-01',
  checkOut: '2026-11-03',
  guests: 2,
  minimumPrice: 100,
  maximumPrice: 300,
  preferences: 'Quiet',
  rankingMode: 'programmatic',
  results: [
    { accommodationId: 51, name: 'Asakusa Lantern Hotel', destination: 'Tokyo', nightlyPrice: 168, maxGuests: 2, rank: 1, reason: 'Best fit.' },
    { accommodationId: 52, name: 'Shinjuku Rail Stay', destination: 'Tokyo', nightlyPrice: 150, maxGuests: 2, rank: 2, reason: 'Cheaper.' },
  ],
  createdAt: '2026-10-21T00:00:00Z',
  updatedAt: '2026-10-21T00:00:00Z',
  notice: null,
}

const workflowId = 'wf-20261021T044352Z-03a0f384'

function record(status: ReviewRecord['status'], extra: Partial<ReviewRecord> = {}): ReviewRecord {
  const reviewed = !['queued', 'planning', 'working'].includes(status)
  return {
    id: workflowId,
    task: 'Recommend which stays from saved search 11 best suit this traveller.',
    status,
    createdAt: '2026-10-21T04:43:52Z',
    updatedAt: '2026-10-21T04:44:40Z',
    evidence: [
      { id: 'search-11', title: 'Traveller criteria', text: 'Destination: Tokyo.' },
      { id: 'stay-51', title: 'Asakusa Lantern Hotel', text: 'Rank 1.' },
      { id: 'stay-52', title: 'Shinjuku Rail Stay', text: 'Rank 2.' },
    ],
    plan: reviewed
      ? { objective: 'Pick the best stays.', steps: [{ id: 's1', description: 'Compare prices.' }], requiredEvidenceIds: ['stay-51'], successCriteria: ['Cited'] }
      : null,
    work: reviewed
      ? {
          summary: 'Two stays fit.',
          items: [
            { id: 'i1', subject: 'Asakusa Lantern Hotel', detail: 'Ranked first and quiet.', evidenceIds: ['search-11', 'stay-51'] },
            { id: 'i2', subject: 'Shinjuku Rail Stay', detail: 'Cheaper option.', evidenceIds: ['stay-52'] },
          ],
        }
      : null,
    review: reviewed
      ? {
          verdict: 'concerns',
          modelVerdict: 'concerns',
          degraded: false,
          findings: [{ severity: 'warning', itemId: 'i2', message: 'Check transport claims.' }],
          recommendations: ['Confirm quiet hours.'],
        }
      : null,
    humanDecision: null,
    finalOutput: null,
    error: null,
    ...extra,
  }
}

beforeEach(() => {
  vi.useFakeTimers()
  vi.mocked(reviewsApi.list).mockResolvedValue([])
})

afterEach(() => {
  vi.useRealTimers()
  vi.resetAllMocks()
})

describe('AgentReviewPanel', () => {
  it('starts a review and checks back until it awaits a decision', async () => {
    vi.mocked(reviewsApi.start).mockResolvedValue({ id: workflowId, status: 'queued' })
    vi.mocked(reviewsApi.get)
      .mockResolvedValueOnce(record('planning'))
      .mockResolvedValueOnce(record('awaiting_human_review'))
    const wrapper = mount(AgentReviewPanel, { props: { search } })
    await flushPromises()

    await wrapper.get('.review-start').trigger('click')
    await flushPromises()

    expect(reviewsApi.start).toHaveBeenCalledWith(11)
    expect(wrapper.text()).toContain('Planner is making a plan')
    expect(wrapper.get('.review-start').attributes('disabled')).toBeDefined()

    await vi.advanceTimersByTimeAsync(3000)
    await flushPromises()

    expect(reviewsApi.get).toHaveBeenCalledTimes(2)
    expect(wrapper.text()).toContain('Waiting for your decision')
    expect(wrapper.text()).toContain('Ranked first and quiet.')
    expect(wrapper.text()).toContain('Based on: Traveller criteria, Asakusa Lantern Hotel')
    expect(wrapper.text()).toContain('Check transport claims.')
    expect(wrapper.find('.review-decision').exists()).toBe(true)

    await vi.advanceTimersByTimeAsync(10000)
    expect(reviewsApi.get).toHaveBeenCalledTimes(2)
  })

  it('stops checking back when the panel closes', async () => {
    vi.mocked(reviewsApi.list).mockResolvedValue([
      { id: workflowId, task: 'Task', status: 'working', createdAt: '2026-10-21T04:43:52Z', updatedAt: '2026-10-21T04:43:52Z' },
    ])
    vi.mocked(reviewsApi.get).mockResolvedValue(record('working'))
    const wrapper = mount(AgentReviewPanel, { props: { search } })
    await flushPromises()
    await wrapper.get('.review-history button').trigger('click')
    await flushPromises()

    wrapper.unmount()
    await vi.advanceTimersByTimeAsync(10000)

    expect(reviewsApi.get).toHaveBeenCalledTimes(1)
  })

  it('records a partial decision with only the kept recommendations', async () => {
    const decided = record('partially_accepted', {
      humanDecision: { decision: 'partial', notes: 'Too noisy', decidedBy: 'traveller', decidedAt: '2026-10-21T04:45:00Z', acceptedItemIds: ['i1'] },
      finalOutput: { summary: 'Two stays fit.', items: [record('awaiting_human_review').work!.items[0]!] },
    })
    vi.mocked(reviewsApi.decide).mockResolvedValue(decided)
    const wrapper = await mountAwaitingReview()

    await wrapper.get('input[value="partial"]').setValue(true)
    await wrapper.get('input[type="checkbox"][value="i2"]').setValue(false)
    await wrapper.get('#review-notes').setValue('  Too noisy  ')
    await wrapper.get('.review-decision').trigger('submit')
    await flushPromises()

    expect(reviewsApi.decide).toHaveBeenCalledWith(workflowId, {
      decision: 'partial',
      notes: 'Too noisy',
      acceptedItemIds: ['i1'],
    })
    expect(wrapper.text()).toContain('Partly accepted')
    expect(wrapper.text()).toContain('Notes: Too noisy')
    expect(wrapper.find('.review-decision').exists()).toBe(false)
  })

  it('sends corrected explanations with the original subjects and evidence', async () => {
    vi.mocked(reviewsApi.decide).mockResolvedValue(record('corrected'))
    const wrapper = await mountAwaitingReview()

    await wrapper.get('input[value="correct"]').setValue(true)
    await wrapper.get('#correction-i2').setValue('Lower price, further from the river.')
    await wrapper.get('.review-decision').trigger('submit')
    await flushPromises()

    expect(reviewsApi.decide).toHaveBeenCalledWith(workflowId, {
      decision: 'correct',
      notes: '',
      correctedOutput: {
        summary: 'Two stays fit.',
        items: [
          { id: 'i1', subject: 'Asakusa Lantern Hotel', detail: 'Ranked first and quiet.', evidenceIds: ['search-11', 'stay-51'] },
          { id: 'i2', subject: 'Shinjuku Rail Stay', detail: 'Lower price, further from the river.', evidenceIds: ['stay-52'] },
        ],
      },
    })
  })

  it('requires notes before rejecting', async () => {
    const wrapper = await mountAwaitingReview()

    await wrapper.get('input[value="reject"]').setValue(true)
    await wrapper.get('.review-decision').trigger('submit')

    expect(reviewsApi.decide).not.toHaveBeenCalled()
    expect(wrapper.get('.review-decision [role="alert"]').text()).toBe(
      'Add a note explaining why you are rejecting the review.',
    )
  })

  it('requires at least one kept recommendation for a partial decision', async () => {
    const wrapper = await mountAwaitingReview()

    await wrapper.get('input[value="partial"]').setValue(true)
    await wrapper.get('input[type="checkbox"][value="i1"]').setValue(false)
    await wrapper.get('input[type="checkbox"][value="i2"]').setValue(false)
    await wrapper.get('.review-decision').trigger('submit')

    expect(reviewsApi.decide).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('Select at least one recommendation to keep.')
  })

  it('shows a server decision error without leaving the decision form', async () => {
    vi.mocked(reviewsApi.decide).mockRejectedValue(
      new ApiRequestError('Workflow is approved, not awaiting human review.', {}, 'not_awaiting_review'),
    )
    const wrapper = await mountAwaitingReview()

    await wrapper.get('.review-decision').trigger('submit')
    await flushPromises()

    expect(wrapper.text()).toContain('Workflow is approved, not awaiting human review.')
    expect(wrapper.find('.review-decision').exists()).toBe(true)
  })

  it('explains when another review is already running', async () => {
    vi.mocked(reviewsApi.start).mockRejectedValue(
      new ApiRequestError('Another agent review is running. Try again when it finishes.', {}, 'multi_agent_busy'),
    )
    const wrapper = mount(AgentReviewPanel, { props: { search } })
    await flushPromises()

    await wrapper.get('.review-start').trigger('click')
    await flushPromises()

    expect(wrapper.get('[role="alert"]').text()).toContain('Another agent review is running.')
    expect(wrapper.get('.review-start').attributes('disabled')).toBeUndefined()
  })

  it('shows a failed stage and its message', async () => {
    vi.mocked(reviewsApi.list).mockResolvedValue([
      { id: workflowId, task: 'Task', status: 'failed', createdAt: '2026-10-21T04:43:52Z', updatedAt: '2026-10-21T04:43:52Z' },
    ])
    vi.mocked(reviewsApi.get).mockResolvedValue(record('failed', {
      plan: null,
      work: null,
      review: null,
      error: { code: 'model_unavailable', message: 'The model did not respond.', stage: 'planning' },
    }))
    const wrapper = mount(AgentReviewPanel, { props: { search } })
    await flushPromises()

    await wrapper.get('.review-history button').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('The planning stage failed.')
    expect(wrapper.text()).toContain('The model did not respond.')
    expect(wrapper.find('.review-decision').exists()).toBe(false)
  })
})

async function mountAwaitingReview() {
  vi.mocked(reviewsApi.list).mockResolvedValue([
    { id: workflowId, task: 'Task', status: 'awaiting_human_review', createdAt: '2026-10-21T04:43:52Z', updatedAt: '2026-10-21T04:44:40Z' },
  ])
  vi.mocked(reviewsApi.get).mockResolvedValue(record('awaiting_human_review'))
  const wrapper = mount(AgentReviewPanel, { props: { search } })
  await flushPromises()
  await wrapper.get('.review-history button').trigger('click')
  await flushPromises()
  return wrapper
}
