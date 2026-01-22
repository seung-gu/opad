import { NextRequest, NextResponse } from 'next/server'

// Prevent static optimization
export const dynamic = 'force-dynamic'
export const fetchCache = 'force-no-store'

/**
 * Proxy to FastAPI vocabulary endpoints
 * 
 * Handles vocabulary CRUD operations
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json()

    // Get FastAPI URL from environment
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 
                   process.env.API_BASE_URL || 
                   'http://localhost:8001'
    
    // Forward request to FastAPI
    const response = await fetch(`${apiUrl}/dictionary/vocabularies`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(body)
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ error: 'Unknown error' }))
      return NextResponse.json(
        errorData,
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error: any) {
    console.error('[Vocabulary API] Error:', error)
    return NextResponse.json(
      { error: 'Internal server error', message: error?.message || String(error) },
      { status: 500 }
    )
  }
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const articleId = searchParams.get('article_id')

    // Get FastAPI URL from environment
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 
                   process.env.API_BASE_URL || 
                   'http://localhost:8001'
    
    // Build query string
    const queryParams = new URLSearchParams()
    if (articleId) {
      queryParams.append('article_id', articleId)
    }
    
    const url = `${apiUrl}/dictionary/vocabularies${queryParams.toString() ? '?' + queryParams.toString() : ''}`
    
    // Forward request to FastAPI
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      }
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ error: 'Unknown error' }))
      return NextResponse.json(
        errorData,
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error: any) {
    console.error('[Vocabulary API] Error:', error)
    return NextResponse.json(
      { error: 'Internal server error', message: error?.message || String(error) },
      { status: 500 }
    )
  }
}
