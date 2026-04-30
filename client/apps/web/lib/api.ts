/**
 * API helpers for web.
 *
 * This module is intentionally split into two sections:
 *
 *   1. Client-side: `fetchWithAuth` — used by React components in the browser
 *      to call Next.js API Routes (`/api/*`) with the JWT token attached.
 *
 *   2. Server-side: `apiBaseUrl` — used by Next.js API Route handlers
 *      (`app/api/.../route.ts`) to forward requests to the FastAPI backend.
 *      Uses `API_BASE_URL` (without NEXT_PUBLIC_ prefix) so the value is
 *      never exposed to the browser bundle.
 *
 * The two run in different runtimes and never share state. Co-locating them
 * here keeps the naming consistent with `client/apps/mobile/lib/api.ts`.
 */

import { getToken } from './auth'

export { parseErrorResponse } from '@opad/libs'

// ---------------------------------------------------------------------------
// Client-side (browser)
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Server-side (Next.js API Routes -> FastAPI proxy)
// ---------------------------------------------------------------------------

const FALLBACK_BASE_URL = 'http://localhost:8001'

/**
 * Base URL of the FastAPI backend.
 *
 * Server-side only — uses `API_BASE_URL` (no NEXT_PUBLIC_ prefix), so the
 * value will be `undefined` (and fall back to localhost) if accidentally
 * imported from client code.
 */
export const apiBaseUrl: string = process.env.API_BASE_URL ?? FALLBACK_BASE_URL

const DEFAULT_TIMEOUT_MS = 30_000

export interface FetchFromApiOptions {
  /** HTTP method. Defaults to 'GET'. */
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH'
  /** Authorization header value (e.g. `Bearer <token>`). Forwarded as-is. */
  authorization?: string | null
  /** Request body. Stringify objects yourself (or pass a JSON string). */
  body?: BodyInit | null
  /** Extra headers merged after Content-Type and before Authorization. */
  headers?: Record<string, string>
  /** Timeout in milliseconds before aborting the fetch. Defaults to 30s. */
  timeoutMs?: number
}

/**
 * Forward a request from a Next.js API Route to the FastAPI backend.
 *
 * Handles three concerns that every proxy handler needs:
 *   1. Timeout via AbortController (default 30 s) — prevents hung connections
 *   2. Authorization header forwarding (when `authorization` is provided)
 *   3. Friendly error messages that include the upstream URL on failure
 *
 * The function does not interpret the response; non-2xx statuses are returned
 * as-is so the caller can apply route-specific handling (404, 409, etc.).
 *
 * @example
 *   const res = await fetchFromApi(`${apiBaseUrl}/articles`, {
 *     authorization: request.headers.get('authorization'),
 *   })
 *
 * @example POST with body
 *   const res = await fetchFromApi(`${apiBaseUrl}/auth/login`, {
 *     method: 'POST',
 *     body: JSON.stringify({ email, password }),
 *   })
 */
export async function fetchFromApi(
  url: string,
  options: FetchFromApiOptions = {}
): Promise<Response> {
  const {
    method = 'GET',
    authorization = null,
    body = null,
    headers: extraHeaders = {},
    timeoutMs = DEFAULT_TIMEOUT_MS,
  } = options

  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs)

  try {
    const response = await fetch(url, {
      method,
      headers: {
        'Content-Type': 'application/json',
        ...extraHeaders,
        ...(authorization ? { Authorization: authorization } : {}),
      },
      body,
      signal: controller.signal,
    })
    clearTimeout(timeoutId)
    return response
  } catch (fetchError: unknown) {
    clearTimeout(timeoutId)
    const error =
      fetchError instanceof Error ? fetchError : new Error('Unknown fetch error')
    const isTimeout = error.name === 'AbortError'
    const seconds = Math.round(timeoutMs / 1000)
    const errorMsg = isTimeout
      ? `Connection timeout: API server at ${apiBaseUrl} did not respond within ${seconds} seconds`
      : `Failed to connect to API server at ${apiBaseUrl}: ${error.message}`
    throw new Error(errorMsg)
  }
}
