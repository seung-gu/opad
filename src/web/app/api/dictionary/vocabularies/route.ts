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

    // Forward Authorization header from client
    const authHeader = request.headers.get('Authorization')
    const headers: Record<string, string> = {
      'Content-Type': 'application/json'
    }
    if (authHeader) {
      headers['Authorization'] = authHeader
    }

    // Forward request to FastAPI
    const response = await fetch(`${apiUrl}/dictionary/vocabulary`, {
      method: 'POST',
      headers,
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
    const language = searchParams.get('language')

    // Get FastAPI URL from environment
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ||
                   process.env.API_BASE_URL ||
                   'http://localhost:8001'

    // Build query string for aggregated vocabulary list
    const queryParams = new URLSearchParams()
    if (language) {
      queryParams.append('language', language)
    }

    const url = `${apiUrl}/dictionary/vocabularies${queryParams.toString() ? '?' + queryParams.toString() : ''}`

    // Forward Authorization header from client
    const authHeader = request.headers.get('Authorization')
    const headers: Record<string, string> = {
      'Content-Type': 'application/json'
    }
    if (authHeader) {
      headers['Authorization'] = authHeader
    }

    // Forward request to FastAPI
    const response = await fetch(url, {
      method: 'GET',
      headers
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
