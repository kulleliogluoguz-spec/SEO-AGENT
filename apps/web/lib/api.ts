/**
 * API Client — typed wrapper around all backend endpoints.
 * Uses fetch with automatic token injection and error handling.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? ''

// ─── Types ───────────────────────────────────────────────────────────────────

export interface User {
  id: string
  email: string
  full_name: string | null
  is_active: boolean
  created_at: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export interface Workspace {
  id: string
  organization_id: string
  name: string
  slug: string
  description: string | null
  autonomy_level: number
  is_active: boolean
  created_at: string
}

export interface Site {
  id: string
  workspace_id: string
  url: string
  domain: string
  name: string | null
  status: 'pending' | 'validating' | 'active' | 'error' | 'archived'
  product_summary: string | null
  category: string | null
  icp_summary: string | null
  last_crawled_at: string | null
  created_at: string
}

export interface Crawl {
  id: string
  site_id: string
  status: 'queued' | 'in_progress' | 'completed' | 'failed' | 'cancelled'
  max_pages: number
  pages_crawled: number
  pages_failed: number
  error_message: string | null
  started_at: string | null
  completed_at: string | null
  created_at: string
}

export interface CrawlPage {
  id: string
  crawl_id: string
  url: string
  status_code: number | null
  title: string | null
  meta_description: string | null
  h1: string | null
  word_count: number
  issues: Record<string, unknown>[]
  crawled_at: string
}

export interface Recommendation {
  id: string
  site_id: string
  title: string
  category: string
  subcategory: string | null
  summary: string
  rationale: string
  evidence: Record<string, unknown>[]
  affected_urls: string[]
  proposed_action: string | null
  impact_score: number
  effort_score: number
  confidence_score: number
  urgency_score: number
  priority_score: number
  target_metric: string | null
  risk_flags: string[]
  status: string
  approval_required: boolean
  generated_by_agent: string | null
  created_at: string
}

export interface ContentAsset {
  id: string
  workspace_id: string
  title: string
  asset_type: string
  status: string
  content: string | null
  brief: Record<string, unknown>
  compliance_flags: string[]
  risk_score: number
  created_at: string
}

export interface Approval {
  id: string
  workspace_id: string
  entity_type: string
  entity_id: string
  title: string
  description: string | null
  risk_level: string
  policy_flags: unknown[]
  status: string
  created_at: string
}

export interface Report {
  id: string
  workspace_id: string
  report_type: string
  title: string
  summary: string | null
  kpis: Record<string, unknown>
  period_start: string | null
  period_end: string | null
  created_at: string
}

export interface ReportDetail extends Report {
  content_md: string | null
  sections: Record<string, unknown>[]
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  pages: number
}

// ─── Client ──────────────────────────────────────────────────────────────────

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public data?: unknown,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

function getToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem('access_token')
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
  })

  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new ApiError(res.status, data.error || res.statusText, data)
  }

  if (res.status === 204) return undefined as T
  return res.json()
}

// ─── Auth ─────────────────────────────────────────────────────────────────────

export const auth = {
  async login(email: string, password: string): Promise<TokenResponse> {
    const data = await request<TokenResponse>('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
    if (typeof window !== 'undefined') {
      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('refresh_token', data.refresh_token)
    }
    return data
  },

  async register(email: string, password: string, full_name: string): Promise<User> {
    return request('/api/v1/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, full_name }),
    })
  },

  async me(): Promise<User> {
    return request('/api/v1/auth/me')
  },

  logout() {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
    }
  },
}

// ─── Sites ────────────────────────────────────────────────────────────────────

export const sites = {
  async list(workspaceId: string, page = 1): Promise<PaginatedResponse<Site>> {
    return request(`/api/v1/sites?workspace_id=${workspaceId}&page=${page}`)
  },

  async get(siteId: string): Promise<Site> {
    return request(`/api/v1/sites/${siteId}`)
  },

  async create(workspaceId: string, url: string, name?: string, maxPages = 100): Promise<Site> {
    return request(`/api/v1/sites?workspace_id=${workspaceId}`, {
      method: 'POST',
      body: JSON.stringify({ url, name, max_pages: maxPages }),
    })
  },

  async listCrawls(siteId: string): Promise<Crawl[]> {
    return request(`/api/v1/sites/${siteId}/crawls`)
  },

  async triggerCrawl(siteId: string, maxPages = 100): Promise<Crawl> {
    return request(`/api/v1/sites/${siteId}/crawl?max_pages=${maxPages}`, {
      method: 'POST',
    })
  },
}

// ─── Crawls ───────────────────────────────────────────────────────────────────

export const crawls = {
  async get(crawlId: string): Promise<Crawl> {
    return request(`/api/v1/crawls/${crawlId}`)
  },

  async listPages(crawlId: string, page = 1): Promise<PaginatedResponse<CrawlPage>> {
    return request(`/api/v1/crawls/${crawlId}/pages?page=${page}`)
  },
}

// ─── Recommendations ──────────────────────────────────────────────────────────

export const recommendations = {
  async list(
    siteId: string,
    opts: { category?: string; status?: string; page?: number } = {},
  ): Promise<PaginatedResponse<Recommendation>> {
    const params = new URLSearchParams({ site_id: siteId })
    if (opts.category) params.set('category', opts.category)
    if (opts.status) params.set('status', opts.status)
    if (opts.page) params.set('page', String(opts.page))
    return request(`/api/v1/recommendations?${params}`)
  },

  async get(recId: string): Promise<Recommendation> {
    return request(`/api/v1/recommendations/${recId}`)
  },

  async updateStatus(recId: string, status: string): Promise<Recommendation> {
    return request(`/api/v1/recommendations/${recId}`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    })
  },
}

// ─── Content ──────────────────────────────────────────────────────────────────

export const content = {
  async list(workspaceId: string, opts: { asset_type?: string; status?: string } = {}): Promise<PaginatedResponse<ContentAsset>> {
    const params = new URLSearchParams({ workspace_id: workspaceId })
    if (opts.asset_type) params.set('asset_type', opts.asset_type)
    if (opts.status) params.set('status', opts.status)
    return request(`/api/v1/content?${params}`)
  },

  async get(assetId: string): Promise<ContentAsset> {
    return request(`/api/v1/content/${assetId}`)
  },

  async createBrief(params: {
    site_id: string
    content_type: string
    topic: string
    target_keyword?: string
    tone?: string
    word_count_target?: number
    notes?: string
  }): Promise<ContentAsset> {
    return request('/api/v1/content/briefs', {
      method: 'POST',
      body: JSON.stringify(params),
    })
  },

  async generate(briefId: string): Promise<ContentAsset> {
    return request('/api/v1/content/generate', {
      method: 'POST',
      body: JSON.stringify({ brief_id: briefId }),
    })
  },

  async approve(assetId: string): Promise<ContentAsset> {
    return request(`/api/v1/content/${assetId}/approve`, { method: 'POST' })
  },
}

// ─── Approvals ────────────────────────────────────────────────────────────────

export const approvals = {
  async list(workspaceId: string, status?: string): Promise<PaginatedResponse<Approval>> {
    const params = new URLSearchParams({ workspace_id: workspaceId })
    if (status) params.set('status', status)
    return request(`/api/v1/approvals?${params}`)
  },

  async action(approvalId: string, action: 'approve' | 'reject', note?: string): Promise<Approval> {
    return request(`/api/v1/approvals/${approvalId}/action`, {
      method: 'POST',
      body: JSON.stringify({ action, note }),
    })
  },
}

// ─── Reports ──────────────────────────────────────────────────────────────────

export const reports = {
  async list(workspaceId: string): Promise<PaginatedResponse<Report>> {
    return request(`/api/v1/reports?workspace_id=${workspaceId}`)
  },

  async get(reportId: string): Promise<ReportDetail> {
    return request(`/api/v1/reports/${reportId}`)
  },
}

// ─── Health ───────────────────────────────────────────────────────────────────

export const health = {
  async check(): Promise<{ status: string; version: string }> {
    return request('/health')
  },
}

export { ApiError }
