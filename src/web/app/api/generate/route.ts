import { NextRequest, NextResponse } from 'next/server'

// Prevent static optimization - only run at request time
export const dynamic = 'force-dynamic'
export const fetchCache = 'force-no-store'

/**
 * 변경 사항:
 * - Python spawn 제거 ✅
 * - FastAPI 호출로 변경 ✅
 * 
 * 새로운 흐름:
 * 1. Article 생성 (POST /articles)
 * 2. Job enqueue (POST /articles/:id/generate)
 * 3. jobId 반환 → 클라이언트가 폴링
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

    // FastAPI base URL (환경변수 또는 기본값)
    const apiBaseUrl = process.env.API_BASE_URL || 'http://localhost:8000'

    console.log(JSON.stringify({
      source: 'web',
      level: 'info',
      endpoint: '/api/generate',
      message: `Calling FastAPI at ${apiBaseUrl}`
    }))

    // Step 1: Create article
    const createArticleResponse = await fetch(`${apiBaseUrl}/articles`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        language,
        level,
        length,
        topic,
      }),
    })

    if (!createArticleResponse.ok) {
      const errorData = await createArticleResponse.json().catch(() => ({}))
      throw new Error(
        errorData.detail || `Failed to create article: ${createArticleResponse.statusText}`
      )
    }

    const article = await createArticleResponse.json()
    const articleId = article.id

    console.log(JSON.stringify({
      source: 'web',
      level: 'info',
      endpoint: '/api/generate',
      message: `Article created: ${articleId}`
    }))

    // Step 2: Enqueue generation job
    // Check for force parameter in request body
    const force = body.force === true
    
    const generateUrl = `${apiBaseUrl}/articles/${articleId}/generate${force ? '?force=true' : ''}`
    const generateResponse = await fetch(generateUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
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
      return NextResponse.json({
        success: false,
        duplicate: true,
        existing_job: detail.existing_job || null,
        article_id: detail.article_id || articleId,
        message: detail.message || 'A job with identical parameters was created within the last 24 hours.'
      })
    }
    
    if (!generateResponse.ok) {
      const errorData = await generateResponse.json().catch(() => ({}))
      throw new Error(
        errorData.detail || `Failed to enqueue job: ${generateResponse.statusText}`
      )
    }

    const generateData = await generateResponse.json()
    const jobId = generateData.job_id
    
    if (!jobId) {
      // job_id should always be present for successful generation
      console.error(JSON.stringify({
        source: 'web',
        level: 'error',
        endpoint: '/api/generate',
        message: `Missing job_id in generate response for article ${articleId}`
      }))
      return NextResponse.json(
        { success: false, error: 'Failed to generate job: missing job_id' },
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
  } catch (error: any) {
    console.error(JSON.stringify({
      source: 'web',
      level: 'error',
      endpoint: '/api/generate',
      message: error.message || 'Internal server error'
    }))
    return NextResponse.json(
      { error: error.message || 'Internal server error' },
      { status: 500 }
    )
  }
}

