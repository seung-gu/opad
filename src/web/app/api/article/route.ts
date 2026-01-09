import { NextRequest, NextResponse } from 'next/server'

// Prevent static optimization - only run at request time
export const dynamic = 'force-dynamic'
export const fetchCache = 'force-no-store'

/**
 * Get article content from FastAPI (MongoDB).
 * 
 * Query parameters:
 * - article_id: Article ID (optional, if not provided, returns error)
 * 
 * Flow:
 * 1. Get article_id from query parameter
 * 2. Call FastAPI GET /articles/:id/content
 * 3. Return markdown content
 */
export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams
    const articleId = searchParams.get('article_id')
    
    if (!articleId) {
      return new NextResponse(
        `# No article ID provided\n\nPlease provide article_id as query parameter.`,
        {
          status: 400,
          headers: {
            'Content-Type': 'text/markdown',
          },
        }
      )
    }

    // FastAPI base URL
    const apiBaseUrl = process.env.API_BASE_URL || 'http://localhost:8000'

    // Call FastAPI to get article content from MongoDB
    const response = await fetch(`${apiBaseUrl}/articles/${articleId}/content`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    if (!response.ok) {
      if (response.status === 404) {
        return new NextResponse(
          `# No article found\n\nClick "Generate New Article" to create one.`,
          {
            status: 404,
            headers: {
              'Content-Type': 'text/markdown',
            },
          }
        )
      }
      throw new Error(`Failed to fetch article: ${response.statusText}`)
    }

    const content = await response.text()
    
    console.log(JSON.stringify({
      source: 'web',
      level: 'info',
      endpoint: '/api/article',
      message: `Successfully loaded article from MongoDB (${content.length} bytes)`
    }))

    return new NextResponse(content, {
      headers: {
        'Content-Type': 'text/markdown',
      },
    })
  } catch (error: any) {
    console.error(JSON.stringify({
      source: 'web',
      level: 'error',
      endpoint: '/api/article',
      message: `Fatal error: ${error.message}`
    }))
    return new NextResponse(
      `# Error\n\nFailed to load article: ${error.message}`,
      {
        status: 500,
        headers: {
          'Content-Type': 'text/markdown',
        },
      }
    )
  }
}

