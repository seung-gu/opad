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
