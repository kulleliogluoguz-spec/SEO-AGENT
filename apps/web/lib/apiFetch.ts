/**
 * apiFetch — global authenticated fetch wrapper.
 *
 * Automatically:
 *   1. Injects JWT Authorization header from localStorage
 *   2. Sets Content-Type: application/json
 *   3. Redirects to /auth on 401 (session expired)
 *   4. Throws on non-2xx with message from response body
 *
 * Usage:
 *   const data = await apiFetch('/api/v1/growth/dashboard/x')
 *   const result = await apiFetch('/api/v1/ads/launch', { method: 'POST', body: JSON.stringify({...}) })
 */

const API = process.env.NEXT_PUBLIC_API_URL ?? ''

export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export async function apiFetch<T = unknown>(
  path: string,
  options: RequestInit & { timeoutMs?: number } = {},
): Promise<T> {
  const token =
    typeof window !== 'undefined'
      ? (localStorage.getItem('access_token') ?? '')
      : ''

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const url = path.startsWith('http') ? path : `${API}${path}`

  const { timeoutMs, ...fetchOptions } = options
  const controller = new AbortController()
  const timeoutId = setTimeout(
    () => controller.abort(),
    timeoutMs ?? 15000,
  )

  let res: Response
  try {
    res = await fetch(url, { ...fetchOptions, headers, signal: controller.signal })
  } catch (err) {
    clearTimeout(timeoutId)
    if (err instanceof Error && err.name === 'AbortError') {
      throw new ApiError('Request timed out — is the server running?', 408)
    }
    throw err
  }
  clearTimeout(timeoutId)

  if (res.status === 401) {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      window.location.replace('/auth')
    }
    throw new ApiError('Session expired. Please log in again.', 401)
  }

  if (!res.ok) {
    let message = `HTTP ${res.status}`
    try {
      const body = await res.json()
      message = body?.detail ?? body?.message ?? body?.error ?? message
    } catch {
      // Non-JSON error body — use status text
      message = res.statusText || message
    }
    throw new ApiError(message, res.status)
  }

  // Handle empty responses (204 No Content)
  if (res.status === 204) return {} as T

  return res.json() as Promise<T>
}

/**
 * Convenience: GET request
 */
export const apiGet = <T = unknown>(path: string) => apiFetch<T>(path)

/**
 * Convenience: POST request with JSON body
 */
export const apiPost = <T = unknown>(path: string, body: unknown) =>
  apiFetch<T>(path, { method: 'POST', body: JSON.stringify(body) })
