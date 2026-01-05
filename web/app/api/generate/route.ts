import { NextRequest, NextResponse } from 'next/server'
import { spawn } from 'child_process'
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

    // Execute Python script in background with stdout/stderr visible in Railway logs
    const childProcess = spawn('python3', [pythonScript], {
      cwd: projectRoot,
      env: env,
      stdio: ['ignore', 'pipe', 'pipe'],
      detached: true
    })
    
    // Unref to allow parent process to exit
    childProcess.unref()
    
    // Forward stdout/stderr to console so Railway can see the logs
    childProcess.stdout.on('data', (data) => {
      console.log(`[Python] ${data.toString()}`)
    })
    
    childProcess.stderr.on('data', (data) => {
      console.error(`[Python] ${data.toString()}`)
    })
    
    childProcess.on('error', (error) => {
      console.error(`Python script spawn error: ${error}`)
    })
    
    childProcess.on('exit', (code) => {
      console.log(`Python script exited with code ${code}`)
    })
    
    console.log('Python script started in background')

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

