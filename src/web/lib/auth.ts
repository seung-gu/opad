/**
 * Token management utilities for JWT authentication
 *
 * Handles storing, retrieving, and removing JWT tokens from localStorage.
 */

const TOKEN_KEY = 'opad_auth_token'

/**
 * Save JWT token to localStorage
 */
export function saveToken(token: string): void {
  if (typeof window === 'undefined') return
  localStorage.setItem(TOKEN_KEY, token)
}

/**
 * Get JWT token from localStorage
 */
export function getToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem(TOKEN_KEY)
}

/**
 * Remove JWT token from localStorage (logout)
 */
export function removeToken(): void {
  if (typeof window === 'undefined') return
  localStorage.removeItem(TOKEN_KEY)
}
