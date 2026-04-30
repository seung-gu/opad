import { NextRequest, NextResponse } from 'next/server'
import { apiBaseUrl } from '@/lib/api'

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

    // Forward Authorization header from client
    const authHeader = request.headers.get('Authorization')
    const headers: Record<string, string> = {
      'Content-Type': 'application/json'
    }
    if (authHeader) {
      headers['Authorization'] = authHeader
    }

    // Forward request to FastAPI
    const response = await fetch(`${apiBaseUrl}/dictionary/vocabulary`, {
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
  } catch (error: unknown) {
    console.error('[Vocabulary API] Error:', error)
    const message = error instanceof Error ? error.message : String(error)
    return NextResponse.json(
      { error: 'Internal server error', message },
      { status: 500 }
    )
  }
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const language = searchParams.get('language')

    // Build query string for aggregated vocabulary list
    const queryParams = new URLSearchParams()
    if (language) {
      queryParams.append('language', language)
    }

    const url = `${apiBaseUrl}/dictionary/vocabularies${queryParams.toString() ? '?' + queryParams.toString() : ''}`

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
  } catch (error: unknown) {
    console.error('[Vocabulary API] Error:', error)
    const message = error instanceof Error ? error.message : String(error)
    return NextResponse.json(
      { error: 'Internal server error', message },
      { status: 500 }
    )
  }
}
