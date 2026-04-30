import { NextRequest, NextResponse } from 'next/server'
import { apiBaseUrl, fetchFromApi } from '@/lib/api'

/**
 * Get database statistics from FastAPI.
 *
 * Flow:
 * 1. Call FastAPI GET /articles/stats
 * 2. Return formatted statistics
 */
export async function GET(_request: NextRequest) {
  try {
    // Call FastAPI to get database statistics
    const response = await fetchFromApi(`${apiBaseUrl}/stats`)

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.detail || `Failed to fetch stats: ${response.statusText}`)
    }

    const stats = await response.json()
    
    return NextResponse.json(stats)
  } catch (error: unknown) {
    console.error('Error fetching stats:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to fetch database statistics' },
      { status: 500 }
    )
  }
}
