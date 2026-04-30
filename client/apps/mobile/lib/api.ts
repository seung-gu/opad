/**
 * API base URL helper for mobile.
 *
 * Mobile calls FastAPI directly (no Next.js proxy). The base URL differs
 * across environments (iOS Simulator / Android Emulator / device / production)
 * and is configured via the EXPO_PUBLIC_API_BASE_URL env var.
 *
 * See README for environment-specific values.
 */

const FALLBACK_BASE_URL = 'http://localhost:8001'

export const apiBaseUrl: string =
  process.env.EXPO_PUBLIC_API_BASE_URL ?? FALLBACK_BASE_URL

/**
 * Build a full API URL by joining the base URL with a path.
 *
 * @example
 *   apiUrl('/articles')           // 'http://localhost:8001/articles'
 *   apiUrl('/articles/123')       // 'http://localhost:8001/articles/123'
 */
export function apiUrl(path: string): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${apiBaseUrl}${normalizedPath}`
}
