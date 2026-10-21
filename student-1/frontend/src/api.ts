export interface SearchRequest {
  destination: string
  checkIn: string
  checkOut: string
  guests: number
  minimumPrice: number
  maximumPrice: number
  preferences: string
  useAi: boolean
}

export interface SearchResult {
  accommodationId: number
  name: string
  destination: string
  nightlyPrice: number
  maxGuests: number
  rank: number
  reason: string
}

export interface SearchSummary {
  id: number
  title: string
  destination: string
  checkIn: string
  checkOut: string
  guests: number
  rankingMode: 'ai' | 'fallback' | 'programmatic'
  createdAt: string
  updatedAt: string
}

export interface SearchResponse extends SearchSummary {
  minimumPrice: number
  maximumPrice: number
  preferences: string
  results: SearchResult[]
  notice: string | null
  importedProviderData?: boolean
}

interface ErrorEnvelope {
  error?: {
    code?: string
    message?: string
    fields?: Record<string, string>
  }
}

export class ApiRequestError extends Error {
  readonly fields: Record<string, string>
  readonly code: string | undefined

  constructor(
    message: string,
    fields: Record<string, string> = {},
    code?: string,
  ) {
    super(message)
    this.fields = fields
    this.code = code
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init)

  if (!response.ok) {
    let error: ErrorEnvelope | null = null
    try {
      error = (await response.json()) as ErrorEnvelope
    } catch {
      // The public message below is used when a dependency returns a non-JSON error.
    }

    throw new ApiRequestError(
      error?.error?.message ?? 'The accommodation service could not complete the request.',
      error?.error?.fields,
      error?.error?.code,
    )
  }

  if (response.status === 204) {
    return undefined as T
  }

  return (await response.json()) as T
}

export const searchesApi = {
  create(search: SearchRequest) {
    return request<SearchResponse>('/api/searches', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(search),
    })
  },

  list() {
    return request<SearchSummary[]>('/api/searches')
  },

  get(id: number) {
    return request<SearchResponse>(`/api/searches/${id}`)
  },

  rename(id: number, title: string) {
    return request<SearchResponse>(`/api/searches/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title }),
    })
  },

  delete(id: number) {
    return request<void>(`/api/searches/${id}`, { method: 'DELETE' })
  },
}

export interface Capabilities {
  aiRanking: boolean
  lookup: boolean
  guide: boolean
  multiAgent: boolean
}

export const capabilitiesApi = {
  get() {
    return request<Capabilities>('/api/capabilities')
  },
}

export type ReviewStatus =
  | 'queued'
  | 'planning'
  | 'working'
  | 'reviewing'
  | 'awaiting_human_review'
  | 'approved'
  | 'corrected'
  | 'partially_accepted'
  | 'rejected'
  | 'failed'

export type ReviewDecisionChoice = 'approve' | 'correct' | 'partial' | 'reject'

export interface ReviewSummary {
  id: string
  task: string
  status: ReviewStatus
  createdAt: string
  updatedAt: string
}

export interface ReviewWorkItem {
  id: string
  subject: string
  detail: string
  evidenceIds: string[]
}

export interface ReviewWork {
  summary: string
  items: ReviewWorkItem[]
}

export interface ReviewRecord extends ReviewSummary {
  evidence: Array<{ id: string; title: string; text: string }>
  plan: {
    objective: string
    steps: Array<{ id: string; description: string }>
    requiredEvidenceIds: string[]
    successCriteria: string[]
  } | null
  work: ReviewWork | null
  review: {
    verdict: 'pass' | 'concerns' | 'fail'
    modelVerdict: 'pass' | 'concerns' | 'fail'
    degraded: boolean
    findings: Array<{ severity: 'info' | 'warning' | 'blocking'; itemId: string | null; message: string }>
    recommendations: string[]
  } | null
  humanDecision: {
    decision: ReviewDecisionChoice
    notes: string
    decidedBy: string
    decidedAt: string
    acceptedItemIds: string[] | null
  } | null
  finalOutput: ReviewWork | null
  error: { code: string; message: string; stage: string | null } | null
}

export interface ReviewDecision {
  decision: ReviewDecisionChoice
  notes: string
  acceptedItemIds?: string[]
  correctedOutput?: ReviewWork
}

export const reviewsApi = {
  start(searchId: number) {
    return request<{ id: string; status: ReviewStatus }>(`/api/searches/${searchId}/reviews`, {
      method: 'POST',
    })
  },

  list(searchId: number) {
    return request<ReviewSummary[]>(`/api/searches/${searchId}/reviews`)
  },

  get(id: string) {
    return request<ReviewRecord>(`/api/reviews/${encodeURIComponent(id)}`)
  },

  decide(id: string, decision: ReviewDecision) {
    return request<ReviewRecord>(`/api/reviews/${encodeURIComponent(id)}/decision`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(decision),
    })
  },
}

export type AssistantMode = 'lookup' | 'guide'

export interface CatalogueStay {
  id: number
  name: string
  destination: string
  nightlyPrice: number
  maxGuests: number
  amenities: string[]
}

export interface SavedSearchLookup {
  id: number
  title: string
  criteria: {
    destination: string
    checkIn: string
    checkOut: string
    guests: number
    minimumPrice: number
    maximumPrice: number
  }
  rankingMode: 'ai' | 'fallback' | 'programmatic'
  results: Array<{
    rank: number
    accommodationId: number
    name: string
    nightlyPrice: number
    reason: string
  }>
}

export type LookupResponse =
  | {
      mode: 'lookup'
      tool: 'accommodation.find'
      arguments: Record<string, string | number>
      result: { ok: true; count: number; accommodations: CatalogueStay[] }
    }
  | {
      mode: 'lookup'
      tool: 'accommodation.get_search'
      arguments: Record<string, string | number>
      result: { ok: true; search: SavedSearchLookup }
    }

export interface GuideCitation {
  source: string
  chunk_id: string
  snippet: string
  score: number
}

export interface GuideResponse {
  mode: 'guide'
  answer: string
  citations: GuideCitation[]
  confidence: 'high' | 'medium' | 'low' | 'insufficient'
}

export type AssistantResponse = LookupResponse | GuideResponse

export const assistantApi = {
  ask(mode: AssistantMode, question: string) {
    return request<AssistantResponse>('/api/assistant', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode, question }),
    })
  },
}
