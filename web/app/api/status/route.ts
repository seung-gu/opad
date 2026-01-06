import { readFile } from 'fs/promises'
import { join } from 'path'
import { NextResponse } from 'next/server'

// Prevent static optimization - only run at request time
export const dynamic = 'force-dynamic'
export const fetchCache = 'force-no-store'

export async function GET() {
  try {
    // Try multiple possible paths for status.json
    const possiblePaths = [
      join(process.cwd(), '..', 'status.json'),  // Railway/Docker: /app/../status.json
      join(process.cwd(), 'status.json'),          // Local: web/status.json (shouldn't happen but try)
    ]
    
    for (const statusPath of possiblePaths) {
      try {
        const content = await readFile(statusPath, 'utf-8')
        const status = JSON.parse(content)
        console.log(JSON.stringify({
          source: 'web',
          level: 'info',
          endpoint: '/api/status',
          message: 'Status file read successfully',
          path: statusPath,
          status: status.status
        }))
        return NextResponse.json(status)
      } catch (err) {
        // Try next path
        continue
      }
    }
    
    // No status file found
    console.log(JSON.stringify({
      source: 'web',
      level: 'warn',
      endpoint: '/api/status',
      message: 'Status file not found',
      triedPaths: possiblePaths
    }))
    return NextResponse.json({
      current_task: 'idle',
      progress: 0,
      status: 'idle',
      message: 'No generation in progress',
      updated_at: new Date().toISOString()
    })
  } catch (error: any) {
    console.error(JSON.stringify({
      source: 'web',
      level: 'error',
      endpoint: '/api/status',
      message: `Error reading status: ${error.message}`
    }))
    return NextResponse.json({
      current_task: 'idle',
      progress: 0,
      status: 'idle',
      message: 'No generation in progress',
      updated_at: new Date().toISOString()
    })
  }
}

