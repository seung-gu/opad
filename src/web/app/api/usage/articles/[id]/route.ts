import { NextRequest, NextResponse } from 'next/server'

// Prevent static optimization - only run at request time
export const dynamic = 'force-dynamic'
export const fetchCache = 'force-no-store'

/**
 * Get token usage records for a specific article from FastAPI.
 *
 * Flow:
 * 1. Extract Authorization header
 * 2. Call FastAPI GET /usage/articles/{article_id}
 * 3. Return token usage records
 */
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id: articleId } = await params

    // FastAPI base URL
    const apiBaseUrl = process.env.API_BASE_URL || 'http://localhost:8001'
    const url = `${apiBaseUrl}/usage/articles/${articleId}`

    // Get Authorization header from client request
    const authorization = request.headers.get('authorization')

    if (!authorization) {
      return NextResponse.json(
        { error: 'Authorization header required' },
        { status: 401 }
      )
    }

    // Call FastAPI to get article usage
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': authorization,
      },
    })

    if (!response.ok) {
      if (response.status === 401) {
        return NextResponse.json(
          { error: 'Unauthorized' },
          { status: 401 }
        )
      }
      if (response.status === 403) {
        return NextResponse.json(
          { error: 'You don\'t have permission to access this article\'s usage' },
          { status: 403 }
        )
      }
      if (response.status === 404) {
        return NextResponse.json(
          { error: 'Article not found' },
          { status: 404 }
        )
      }
      const errorData = await response.json().catch(() => ({}))
      return NextResponse.json(
        { error: errorData.detail || 'Failed to fetch article usage' },
        { status: response.status }
      )
    }

    const usageData = await response.json()
    return NextResponse.json(usageData)
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Failed to fetch article usage'
    console.error('Error fetching article usage:', message)
    return NextResponse.json(
      { error: message },
      { status: 500 }
    )
  }
}
