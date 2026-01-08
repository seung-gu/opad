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
    const generateResponse = await fetch(`${apiBaseUrl}/articles/${articleId}/generate`, {
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

    if (!generateResponse.ok) {
      const errorData = await generateResponse.json().catch(() => ({}))
      throw new Error(
        errorData.detail || `Failed to enqueue job: ${generateResponse.statusText}`
      )
    }

    const generateData = await generateResponse.json()
    const jobId = generateData.job_id

    console.log(JSON.stringify({
      source: 'web',
      level: 'info',
      endpoint: '/api/generate',
      message: `Job enqueued: ${jobId} for article ${articleId}`
    }))

    // Return jobId and articleId for client to poll
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

