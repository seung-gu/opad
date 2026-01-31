import { NextRequest, NextResponse } from 'next/server'

// Prevent static optimization - only run at request time
export const dynamic = 'force-dynamic'
export const fetchCache = 'force-no-store'

/**
 * Get article metadata by ID from FastAPI.
 * 
 * Flow:
 * 1. Extract article ID from route params
 * 2. Call FastAPI GET /articles/:id
 * 3. Return article metadata
 */
export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const articleId = params.id

    if (!articleId) {
      return NextResponse.json(
        { error: 'Article ID is required' },
        { status: 400 }
      )
    }

    // FastAPI base URL
    const apiBaseUrl = process.env.API_BASE_URL || 'http://localhost:8001'

    // Get Authorization header from client request
    const authorization = request.headers.get('authorization')

    // Call FastAPI to get article metadata
    const response = await fetch(`${apiBaseUrl}/articles/${articleId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...(authorization ? { 'Authorization': authorization } : {}),
      },
    })

    if (!response.ok) {
      if (response.status === 404) {
        return NextResponse.json(
          { error: 'Article not found' },
          { status: 404 }
        )
      }
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.detail || `Failed to fetch article: ${response.statusText}`)
    }

    const article = await response.json()

    return NextResponse.json(article)
  } catch (error: unknown) {
    const errorMessage = error instanceof Error ? error.message : 'Failed to load article'
    console.error(JSON.stringify({
      source: 'web',
      level: 'error',
      endpoint: `/api/articles/${params.id}`,
      message: `Failed to load article: ${errorMessage}`
    }))
    return NextResponse.json(
      { error: errorMessage },
      { status: 500 }
    )
  }
}
