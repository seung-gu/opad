import { NextRequest, NextResponse } from 'next/server'

// Prevent static optimization - only run at request time
export const dynamic = 'force-dynamic'
export const fetchCache = 'force-no-store'

/**
 * Generate article endpoint (Next.js API route)
 * 
 * Flow:
 * 1. POST /articles/generate (unified endpoint)
 *    - Check for duplicates first
 *    - If no duplicate, create article + enqueue job
 * 2. Return jobId → client polls for status
 * 
 * See 참고문서.md for detailed sequence diagrams.
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { language, level, length, topic } = body

    // Validate inputs
    if (!language || !level || !length || !topic) {
      return NextResponse.json(
        { error: 'Missing required fields' },
        { status: 400 }
      )
    }

    // FastAPI base URL (Environment variable or default value)
    const apiBaseUrl = process.env.API_BASE_URL || 'http://localhost:8001'

    console.log(JSON.stringify({
      source: 'web',
      level: 'info',
      endpoint: '/api/generate',
      message: `Calling FastAPI at ${apiBaseUrl}`
    }))

    // Get Authorization header from client request
    const authorization = request.headers.get('authorization')

    // Call unified endpoint: duplicate check + article creation + job enqueue
    const force = body.force === true
    const generateUrl = `${apiBaseUrl}/articles/generate${force ? '?force=true' : ''}`
    const generateResponse = await fetch(generateUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(authorization ? { 'Authorization': authorization } : {}),
      },
      body: JSON.stringify({
        language,
        level,
        length,
        topic,
      }),
    })

    // Handle duplicate job (409 Conflict)
    if (generateResponse.status === 409) {
      const errorData = await generateResponse.json().catch(() => ({}))
      // FastAPI returns HTTPException detail directly in response body, not nested under "detail"
      const detail = errorData.detail || errorData
      
      console.log(JSON.stringify({
        source: 'web',
        level: 'info',
        endpoint: '/api/generate',
        message: `Duplicate job detected: ${detail.existing_job?.id}`
      }))
      
      // Return in same format as before for frontend compatibility
      // Note: Return with 409 status code so frontend can detect it via response.status
      return NextResponse.json({
        success: false,
        duplicate: true,
        existing_job: detail.existing_job || null,
        article_id: detail.article_id || null,
        message: detail.message || 'A job with identical parameters was created within the last 24 hours.'
      }, { status: 409 })
    }
    
    // Handle other non-2xx errors (409 is already handled above)
    if (!generateResponse.ok) {
      const errorData = await generateResponse.json().catch(() => ({}))
      throw new Error(
        errorData.detail || `Failed to generate: ${generateResponse.statusText}`
      )
    }

    const generateData = await generateResponse.json()
    const jobId = generateData.job_id
    const articleId = generateData.article_id
    
    if (!jobId || !articleId) {
      // job_id and article_id should always be present for successful generation
      console.error(JSON.stringify({
        source: 'web',
        level: 'error',
        endpoint: '/api/generate',
        message: `Missing job_id or article_id in generate response`
      }))
      return NextResponse.json(
        { success: false, error: 'Failed to generate: missing job_id or article_id' },
        { status: 500 }
      )
    }
    
    console.log(JSON.stringify({
      source: 'web',
      level: 'info',
      endpoint: '/api/generate',
      message: `Job enqueued: ${jobId} for article ${articleId}`
    }))

    return NextResponse.json({
      success: true,
      job_id: jobId,
      article_id: articleId,
      message: 'Article generation started. Use job_id to track progress.'
    })
  } catch (error: unknown) {
    const errorMessage = error instanceof Error ? error.message : 'Internal server error'
    console.error(JSON.stringify({
      source: 'web',
      level: 'error',
      endpoint: '/api/generate',
      message: errorMessage
    }))
    return NextResponse.json(
      { error: errorMessage },
      { status: 500 }
    )
  }
}

