import { NextRequest, NextResponse } from 'next/server'
import { apiBaseUrl } from '@/lib/api'

// Prevent static optimization
export const dynamic = 'force-dynamic'
export const fetchCache = 'force-no-store'

/**
 * Delete vocabulary endpoint
 */
export async function DELETE(request: NextRequest, props: { params: Promise<{ id: string }> }) {
  const params = await props.params;
  try {
    const vocabularyId = params.id

    // Forward Authorization header from client
    const authHeader = request.headers.get('Authorization')
    const headers: Record<string, string> = {
      'Content-Type': 'application/json'
    }
    if (authHeader) {
      headers['Authorization'] = authHeader
    }

    // Forward request to FastAPI
    const response = await fetch(`${apiBaseUrl}/dictionary/vocabularies/${vocabularyId}`, {
      method: 'DELETE',
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
