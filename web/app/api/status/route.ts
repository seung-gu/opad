import { readFile } from 'fs/promises'
import { join } from 'path'
import { NextResponse } from 'next/server'

// Prevent static optimization - only run at request time
export const dynamic = 'force-dynamic'
export const fetchCache = 'force-no-store'

export async function GET() {
  try {
    const statusPath = join(process.cwd(), '..', 'status.json')
    const content = await readFile(statusPath, 'utf-8')
    const status = JSON.parse(content)
    return NextResponse.json(status)
  } catch (error: any) {
    // Status file doesn't exist or error reading
    return NextResponse.json({
      current_task: 'idle',
      progress: 0,
      status: 'idle',
      message: 'No generation in progress',
      updated_at: new Date().toISOString()
    })
  }
}

