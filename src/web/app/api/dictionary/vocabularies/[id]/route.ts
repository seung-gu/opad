import { NextRequest, NextResponse } from 'next/server'

// Prevent static optimization
export const dynamic = 'force-dynamic'
export const fetchCache = 'force-no-store'

/**
 * Delete vocabulary endpoint
 */
export async function DELETE(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const vocabularyId = params.id

    // Get FastAPI URL from environment
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 
                   process.env.API_BASE_URL || 
                   'http://localhost:8001'
    
    // Forward request to FastAPI
    const response = await fetch(`${apiUrl}/dictionary/vocabularies/${vocabularyId}`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json'
      }
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
