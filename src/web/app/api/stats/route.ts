import { NextRequest, NextResponse } from 'next/server'

/**
 * Get database statistics from FastAPI.
 * 
 * Flow:
 * 1. Call FastAPI GET /articles/stats
 * 2. Return formatted statistics
 */
export async function GET(request: NextRequest) {
  try {
    // FastAPI base URL
    const apiBaseUrl = process.env.API_BASE_URL || 'http://localhost:8001'

    // Call FastAPI to get database statistics
    const response = await fetch(`${apiBaseUrl}/stats`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.detail || `Failed to fetch stats: ${response.statusText}`)
    }

    const stats = await response.json()
    
    return NextResponse.json(stats)
  } catch (error: any) {
    console.error('Error fetching stats:', error)
    return NextResponse.json(
      { error: error.message || 'Failed to fetch database statistics' },
      { status: 500 }
    )
  }
}
