import { NextRequest, NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'
export const fetchCache = 'force-no-store'

/**
 * Get current user endpoint (Next.js API route → FastAPI proxy)
 *
 * Forwards request to FastAPI /auth/me endpoint
 */
export async function GET(request: NextRequest) {
  try {
    // FastAPI base URL
    const apiBaseUrl = process.env.API_BASE_URL || 'http://localhost:8001'

    // Get Authorization header from client request
    const authorization = request.headers.get('authorization')

    if (!authorization) {
      return NextResponse.json(
        { detail: 'Not authenticated' },
        { status: 401 }
      )
    }

    const response = await fetch(`${apiBaseUrl}/auth/me`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': authorization,
      },
    })

    const data = await response.json()

    if (!response.ok) {
      return NextResponse.json(data, { status: response.status })
    }

    return NextResponse.json(data)
  } catch (error: any) {
    console.error('Get current user error:', error)
    return NextResponse.json(
      { detail: error.message || 'Internal server error' },
      { status: 500 }
    )
  }
}
