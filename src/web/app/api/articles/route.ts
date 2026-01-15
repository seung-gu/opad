import { NextRequest, NextResponse } from 'next/server'

// Prevent static optimization - only run at request time
export const dynamic = 'force-dynamic'
export const fetchCache = 'force-no-store'

/**
 * Get article list from FastAPI.
 * 
 * Query parameters:
 * - skip: Number of articles to skip (default: 0)
 * - limit: Maximum number of articles to return (default: 20, max: 100)
 * - status: Filter by status (optional)
 * - language: Filter by language (optional)
 * - level: Filter by level (optional)
 * - owner_id: Filter by owner_id (optional)
 * 
 * Flow:
 * 1. Extract query parameters
 * 2. Call FastAPI GET /articles with query params
 * 3. Return article list response
 */
export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams
    
    // Extract query parameters
    const skip = parseInt(searchParams.get('skip') || '0', 10)
    const limit = parseInt(searchParams.get('limit') || '20', 10)
    const status = searchParams.get('status') || undefined
    const language = searchParams.get('language') || undefined
    const level = searchParams.get('level') || undefined
    const owner_id = searchParams.get('owner_id') || undefined

    // FastAPI base URL
    const apiBaseUrl = process.env.API_BASE_URL || 'http://localhost:8000'

    // Build query string
    const queryParams = new URLSearchParams()
    if (skip > 0) queryParams.set('skip', skip.toString())
    queryParams.set('limit', limit.toString()) // Always include limit
    if (status) queryParams.set('status', status)
    if (language) queryParams.set('language', language)
    if (level) queryParams.set('level', level)
    if (owner_id) queryParams.set('owner_id', owner_id)

    const queryString = queryParams.toString()
    const url = `${apiBaseUrl}/articles${queryString ? `?${queryString}` : ''}`

    // Call FastAPI to get article list
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.detail || `Failed to fetch articles: ${response.statusText}`)
    }

    const data = await response.json()
    
    console.log(JSON.stringify({
      source: 'web',
      level: 'info',
      endpoint: '/api/articles',
      message: `Successfully loaded ${data.articles?.length || 0} articles`,
      total: data.total,
      skip: data.skip,
      limit: data.limit
    }))

    return NextResponse.json(data)
  } catch (error: any) {
    console.error(JSON.stringify({
      source: 'web',
      level: 'error',
      endpoint: '/api/articles',
      message: `Failed to load articles: ${error.message}`
    }))
    return NextResponse.json(
      { error: error.message || 'Failed to load articles' },
      { status: 500 }
    )
  }
}
