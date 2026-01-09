import { NextRequest, NextResponse } from 'next/server'

// Prevent static optimization - only run at request time
export const dynamic = 'force-dynamic'
export const fetchCache = 'force-no-store'

/**
 * 변경 사항:
 * - status.json 파일 읽기 제거 ✅
 * - FastAPI GET /jobs/:jobId 호출로 변경 ✅
 * 
 * Query parameter: job_id (필수)
 */
export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams
    const jobId = searchParams.get('job_id')

    if (!jobId) {
      // jobId가 없으면 idle 상태 반환 (하위 호환성)
      return NextResponse.json({
        current_task: 'idle',
        progress: 0,
        status: 'idle',
        message: 'No generation in progress',
        updated_at: new Date().toISOString()
      })
    }

    // FastAPI base URL
    const apiBaseUrl = process.env.API_BASE_URL || 'http://localhost:8000'

    // FastAPI에서 job 상태 조회
    const response = await fetch(`${apiBaseUrl}/jobs/${jobId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    if (!response.ok) {
      if (response.status === 404) {
        // Job이 없으면 idle 상태 반환
        return NextResponse.json({
          current_task: 'idle',
          progress: 0,
          status: 'idle',
          message: 'Job not found',
          updated_at: new Date().toISOString()
        })
      }
      throw new Error(`Failed to fetch job status: ${response.statusText}`)
    }

    const jobData = await response.json()

    // 기존 status.json 형식과 호환되도록 변환
    // page.tsx가 기대하는 형식: { current_task, progress, status, message, error }
    // Status mapping:
    // - queued: Job is waiting in queue (not yet picked up by worker)
    // - running: Job is actively being processed by worker
    // - completed/error: Terminal states (stop polling)
    return NextResponse.json({
      current_task: jobData.status === 'running' ? 'processing' : 
                   jobData.status === 'queued' ? 'queued' : '',
      progress: jobData.progress || 0,
      status: jobData.status === 'succeeded' ? 'completed' : 
             jobData.status === 'failed' ? 'error' : 
             jobData.status === 'running' ? 'running' :
             jobData.status === 'queued' ? 'queued' : 'idle',
      message: jobData.message || '',
      error: jobData.error || null,  // Include error message for failed jobs
      updated_at: jobData.updated_at || new Date().toISOString()
    })
  } catch (error: any) {
    console.error(JSON.stringify({
      source: 'web',
      level: 'error',
      endpoint: '/api/status',
      message: `Error fetching job status: ${error.message}`
    }))
    return NextResponse.json({
      current_task: 'idle',
      progress: 0,
      status: 'idle',
      message: 'Error fetching status',
      updated_at: new Date().toISOString()
    })
  }
}

