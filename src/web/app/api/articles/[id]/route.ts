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

    // Call FastAPI to get article metadata
    const response = await fetch(`${apiBaseUrl}/articles/${articleId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
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
    
    console.log(JSON.stringify({
      source: 'web',
      level: 'info',
      endpoint: `/api/articles/${articleId}`,
      message: `Successfully loaded article: ${articleId}`
    }))

    return NextResponse.json(article)
  } catch (error: any) {
    console.error(JSON.stringify({
      source: 'web',
      level: 'error',
      endpoint: `/api/articles/${params.id}`,
      message: `Failed to load article: ${error.message}`
    }))
    return NextResponse.json(
      { error: error.message || 'Failed to load article' },
      { status: 500 }
    )
  }
}
