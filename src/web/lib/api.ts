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

/**
 * Parse error message from API response.
 *
 * Attempts to extract error message from response JSON in this order:
 * 1. error field
 * 2. detail field
 * 3. message field
 * 4. Falls back to provided default message
 *
 * @param response - Fetch Response object
 * @param defaultMessage - Default error message if parsing fails
 * @returns Promise resolving to error message string
 *
 * @example
 * ```typescript
 * const response = await fetch('/api/endpoint')
 * if (!response.ok) {
 *   const errorMsg = await parseErrorResponse(response, 'Failed to fetch data')
 *   throw new Error(errorMsg)
 * }
 * ```
 */
export async function parseErrorResponse(
  response: Response,
  defaultMessage: string = 'An error occurred'
): Promise<string> {
  try {
    const data = await response.json()
    return data.error || data.detail || data.message || defaultMessage
  } catch {
    // If response body is not JSON or already consumed
    return defaultMessage
  }
}
