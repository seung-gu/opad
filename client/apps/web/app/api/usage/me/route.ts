import { NextRequest, NextResponse } from 'next/server'

// Prevent static optimization - only run at request time
export const dynamic = 'force-dynamic'
export const fetchCache = 'force-no-store'

/**
 * Get token usage summary from FastAPI.
 *
 * Query parameters:
 * - days: Number of days to look back (default: 30, range: 1-365)
 *
 * Flow:
 * 1. Extract Authorization header
 * 2. Call FastAPI GET /usage/me with query params
 * 3. Return usage summary response
 */
export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams

    // Extract query parameters
    const days = searchParams.get('days') || '30'

    // FastAPI base URL
    const apiBaseUrl = process.env.API_BASE_URL || 'http://localhost:8001'

    // Build query string
    const queryParams = new URLSearchParams()
    queryParams.set('days', days)

    const url = `${apiBaseUrl}/usage/me?${queryParams.toString()}`

    // Get Authorization header from client request
    const authorization = request.headers.get('authorization')

    if (!authorization) {
      return NextResponse.json(
        { error: 'Authorization header required' },
        { status: 401 }
      )
    }

    // Call FastAPI to get usage summary
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': authorization,
      },
    })

    if (!response.ok) {
      if (response.status === 401) {
        return NextResponse.json(
          { error: 'Unauthorized' },
          { status: 401 }
        )
      }
      const errorData = await response.json().catch(() => ({}))
      return NextResponse.json(
        { error: errorData.detail || `Failed to fetch usage data` },
        { status: response.status }
      )
    }

    const usageData = await response.json()
    return NextResponse.json(usageData)
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Failed to fetch usage data'
    console.error('Error fetching usage:', message)
    return NextResponse.json(
      { error: message },
      { status: 500 }
    )
  }
}
