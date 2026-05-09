import { NextRequest, NextResponse } from 'next/server'
import { apiBaseUrl, fetchFromApi } from '@/lib/api'

// Prevent static optimization - only run at request time
export const dynamic = 'force-dynamic'
export const fetchCache = 'force-no-store'

const LOG_ENDPOINT = '/api/articles'

function logError(message: string, extra?: Record<string, unknown>) {
  console.error(JSON.stringify({
    source: 'web',
    level: 'error',
    endpoint: LOG_ENDPOINT,
    message,
    ...extra
  }))
}

interface ArticleQueryParams {
  skip: number
  limit: number
  status?: string
  language?: string
  level?: string
  user_id?: string
}

function buildQueryString(params: ArticleQueryParams): string {
  const queryParams = new URLSearchParams()
  if (params.skip > 0) queryParams.set('skip', params.skip.toString())
  queryParams.set('limit', params.limit.toString())
  if (params.status) queryParams.set('status', params.status)
  if (params.language) queryParams.set('language', params.language)
  if (params.level) queryParams.set('level', params.level)
  if (params.user_id) queryParams.set('user_id', params.user_id)
  return queryParams.toString()
}

function parseQueryParams(searchParams: URLSearchParams): ArticleQueryParams {
  return {
    skip: Number.parseInt(searchParams.get('skip') || '0', 10),
    limit: Number.parseInt(searchParams.get('limit') || '20', 10),
    status: searchParams.get('status') || undefined,
    language: searchParams.get('language') || undefined,
    level: searchParams.get('level') || undefined,
    user_id: searchParams.get('user_id') || undefined
  }
}

/**
 * Get article list from FastAPI.
 * 
 * Query parameters:
 * - skip: Number of articles to skip (default: 0)
 * - limit: Maximum number of articles to return (default: 20, max: 100)
 * - status: Filter by status (optional)
 * - language: Filter by language (optional)
 * - level: Filter by level (optional)
 * - user_id: Filter by user_id (optional)
 * 
 * Flow:
 * 1. Extract query parameters
 * 2. Call FastAPI GET /articles with query params
 * 3. Return article list response
 */
export async function GET(request: NextRequest) {
  try {
    const params = parseQueryParams(request.nextUrl.searchParams)
    const queryString = buildQueryString(params)
    const url = `${apiBaseUrl}/articles${queryString ? '?' + queryString : ''}`
    const authorization = request.headers.get('authorization')

    const response = await fetchFromApi(url, { authorization })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      logError(`API returned error: ${response.status} ${response.statusText}`, { errorData, url })
      throw new Error(errorData.detail || `Failed to fetch articles: ${response.status} ${response.statusText}`)
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Failed to load articles'
    logError(`Failed to load articles: ${message}`)
    return NextResponse.json(
      { error: message },
      { status: 500 }
    )
  }
}
