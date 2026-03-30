/**
 * Auth utilities for the frontend.
 * Manages JWT storage and provides auth state helpers.
 */

export function getAccessToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem('access_token')
}

export function isAuthenticated(): boolean {
  const token = getAccessToken()
  if (!token) return false

  // Basic JWT expiry check (without library)
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    return payload.exp * 1000 > Date.now()
  } catch {
    return false
  }
}

export function clearTokens(): void {
  if (typeof window === 'undefined') return
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
}
