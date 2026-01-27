import { NextRequest, NextResponse } from 'next/server'

// Prevent static optimization
export const dynamic = 'force-dynamic'
export const fetchCache = 'force-no-store'

/**
 * Proxy to FastAPI dictionary stats endpoint
 * 
 * Returns HTML page showing vocabulary word list grouped by language
 */
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const language = searchParams.get('language')

    // Get FastAPI URL from environment
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 
                   process.env.API_BASE_URL || 
                   'http://localhost:8001'
    
    // Build query string
    const queryParams = new URLSearchParams()
    if (language) {
      queryParams.append('language', language)
    }
    
    const url = `${apiUrl}/dictionary/stats${queryParams.toString() ? '?' + queryParams.toString() : ''}`
    
    // Forward request to FastAPI
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'text/html'
      }
    })

    if (!response.ok) {
      const errorData = await response.text().catch(() => 'Unknown error')
      return new NextResponse(errorData, { 
        status: response.status,
        headers: { 'Content-Type': 'text/html' }
      })
    }

    // Return HTML as-is
    const html = await response.text()
    return new NextResponse(html, {
      status: 200,
      headers: { 'Content-Type': 'text/html' }
    })
  } catch (error: any) {
    console.error('[Dictionary Stats API] Error:', error)
    return NextResponse.json(
      { error: 'Internal server error', message: error?.message || String(error) },
      { status: 500 }
    )
  }
}
