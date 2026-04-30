import { NextRequest, NextResponse } from 'next/server'
import { apiBaseUrl, fetchFromApi } from '@/lib/api'

// Prevent static optimization
export const dynamic = 'force-dynamic'
export const fetchCache = 'force-no-store'

/**
 * Proxy to FastAPI article vocabularies endpoint
 *
 * GET /api/articles/[id]/vocabularies
 */
export async function GET(request: NextRequest, props: { params: Promise<{ id: string }> }) {
  const params = await props.params;
  try {
    const articleId = params.id

    // Forward Authorization header from client
    const authorization = request.headers.get('Authorization')

    // Forward request to FastAPI
    const response = await fetchFromApi(`${apiBaseUrl}/articles/${articleId}/vocabularies`, {
      authorization,
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
    console.error('[Article Vocabularies API] Error:', error)
    const message = error instanceof Error ? error.message : String(error)
    return NextResponse.json(
      { error: 'Internal server error', message },
      { status: 500 }
    )
  }
}
