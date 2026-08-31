export interface SearchRequest {
  destination: string
  checkIn: string
  checkOut: string
  guests: number
  minimumPrice: number
  maximumPrice: number
  preferences: string
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
  rankingMode: 'ai' | 'fallback'
  createdAt: string
  updatedAt: string
}

export interface SearchResponse extends SearchSummary {
  minimumPrice: number
  maximumPrice: number
  preferences: string
  results: SearchResult[]
  notice: string | null
}

interface ErrorEnvelope {
  error?: {
    message?: string
    fields?: Record<string, string>
  }
}

export class ApiRequestError extends Error {
  readonly fields: Record<string, string>

  constructor(
    message: string,
    fields: Record<string, string> = {},
  ) {
    super(message)
    this.fields = fields
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
