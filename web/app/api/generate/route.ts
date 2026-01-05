import { NextRequest, NextResponse } from 'next/server'
import { exec } from 'child_process'
import { writeFile } from 'fs/promises'
import { join } from 'path'

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

    // Create input JSON
    const inputs = {
      language,
      level,
      length,
      topic,
      timestamp: new Date().toISOString()
    }

    // Write input.json
    const projectRoot = join(process.cwd(), '..')
    const inputPath = join(projectRoot, 'input.json')
    await writeFile(inputPath, JSON.stringify(inputs, null, 2))

    // Execute Python script in background
    const pythonScript = join(projectRoot, 'src', 'opad', 'main.py')
    const env = {
      ...process.env,
      PYTHONPATH: join(projectRoot, 'src'),
    }

    exec(
      `cd ${projectRoot} && python3 ${pythonScript}`,
      { env },
      (error, stdout, stderr) => {
        if (error) {
          console.error(`Python script error: ${error}`)
          return
        }
        console.log('Python script completed')
      }
    )

    // Return immediately (async processing)
    return NextResponse.json({
      success: true,
      message: 'Article generation started. This may take a few minutes. The page will update automatically when ready.'
    })
  } catch (error: any) {
    return NextResponse.json(
      { error: error.message || 'Internal server error' },
      { status: 500 }
    )
  }
}

