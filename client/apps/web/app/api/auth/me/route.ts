import { NextRequest, NextResponse } from 'next/server'
import { apiBaseUrl, fetchFromApi } from '@/lib/api'

export const dynamic = 'force-dynamic'
export const fetchCache = 'force-no-store'

/**
 * Get current user endpoint (Next.js API route → FastAPI proxy)
 *
 * Forwards request to FastAPI /auth/me endpoint
 */
export async function GET(request: NextRequest) {
  try {
    // Get Authorization header from client request
    const authorization = request.headers.get('authorization')

    if (!authorization) {
      return NextResponse.json(
        { detail: 'Not authenticated' },
        { status: 401 }
      )
    }

    const response = await fetchFromApi(`${apiBaseUrl}/auth/me`, {
      authorization,
    })

    const data = await response.json()

    if (!response.ok) {
      return NextResponse.json(data, { status: response.status })
    }

    return NextResponse.json(data)
  } catch (error: unknown) {
    console.error('Get current user error:', error)
    return NextResponse.json(
      { detail: error instanceof Error ? error.message : 'Internal server error' },
      { status: 500 }
    )
  }
}
