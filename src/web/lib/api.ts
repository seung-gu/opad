/**
 * API client utilities with automatic authentication
 */

import { getToken } from './auth'

/**
 * Fetch wrapper that automatically adds Authorization header from localStorage
 */
export async function fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
  const token = getToken()

  const headers = {
    ...options.headers,
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
  }

  return fetch(url, {
    ...options,
    headers,
  })
}
