import { NextResponse } from 'next/server'

// Prevent static optimization - only run at request time
export const dynamic = 'force-dynamic'
export const fetchCache = 'force-no-store'

/**
 * Get latest article from FastAPI (MongoDB).
 * 
 * Flow:
 * 1. Call FastAPI GET /articles/latest
 * 2. Return article metadata
 */
export async function GET() {
  try {
    // FastAPI base URL
    const apiBaseUrl = process.env.API_BASE_URL || 'http://localhost:8001'

    // Call FastAPI to get latest article from MongoDB
    const response = await fetch(`${apiBaseUrl}/articles/latest`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    if (!response.ok) {
      if (response.status === 404) {
        return new NextResponse(
          JSON.stringify({ error: 'No articles found' }),
          {
            status: 404,
            headers: {
              'Content-Type': 'application/json',
            },
          }
        )
      }
      throw new Error(`Failed to fetch latest article: ${response.statusText}`)
    }

    const article = await response.json()
    
    console.log(JSON.stringify({
      source: 'web',
      level: 'info',
      endpoint: '/api/latest',
      message: `Successfully loaded latest article: ${article.id}`
    }))

    return new NextResponse(JSON.stringify(article), {
      headers: {
        'Content-Type': 'application/json',
      },
    })
  } catch (error: any) {
    console.error(JSON.stringify({
      source: 'web',
      level: 'error',
      endpoint: '/api/latest',
      message: `Failed to load latest article: ${error.message}`
    }))
    return new NextResponse(
      JSON.stringify({ error: 'Failed to load latest article' }),
      {
        status: 500,
        headers: {
          'Content-Type': 'application/json',
        },
      }
    )
  }
}
