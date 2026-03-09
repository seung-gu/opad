import { NextRequest, NextResponse } from 'next/server'

// Prevent static optimization
export const dynamic = 'force-dynamic'
export const fetchCache = 'force-no-store'

/**
 * Proxy to FastAPI dictionary endpoint
 * 
 * Forwards word definition requests to FastAPI backend
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { sentence, word, language, article_id } = body

    if (!sentence || !word) {
      return NextResponse.json(
        { error: 'Missing sentence or word' },
        { status: 400 }
      )
    }

    // Get FastAPI URL from environment
    // Try multiple env var names for compatibility
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ||
                   process.env.API_BASE_URL ||
                   'http://localhost:8001'

    // Forward Authorization header from client
    const authHeader = request.headers.get('Authorization')
    const headers: Record<string, string> = {
      'Content-Type': 'application/json'
    }
    if (authHeader) {
      headers['Authorization'] = authHeader
    }

    // Forward request to FastAPI
    // Only include article_id if it's a valid non-empty string
    const requestBody: Record<string, string> = {
      word: word,
      sentence: sentence,
      language: language
    }
    if (article_id && typeof article_id === 'string' && article_id.trim()) {
      requestBody.article_id = article_id
    }

    const response = await fetch(`${apiUrl}/dictionary/search`, {
      method: 'POST',
      headers,
      body: JSON.stringify(requestBody)
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
  } catch (error: unknown) {
    console.error('[Dictionary Proxy] Error:', error)
    const message = error instanceof Error ? error.message : String(error)
    return NextResponse.json(
      { error: 'Internal server error', message },
      { status: 500 }
    )
  }
}
