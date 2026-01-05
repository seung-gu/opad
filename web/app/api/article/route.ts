import { readFile } from 'fs/promises'
import { join } from 'path'
import { NextResponse } from 'next/server'
import { exec } from 'child_process'
import { promisify } from 'util'

const execAsync = promisify(exec)

export async function GET() {
  try {
    // Try R2 first (production)
    // In Docker/Railway: process.cwd() is /app/web, so ../src is /app/src
    try {
      const projectRoot = join(process.cwd(), '..')
      const srcPath = join(projectRoot, 'src')
      // Download from R2 - use print for content, logging for errors
      const pythonCode = `import sys; import logging; logging.basicConfig(level=logging.ERROR, handlers=[logging.StreamHandler(sys.stderr)], force=True); sys.path.insert(0, ${JSON.stringify(srcPath)}); from utils.cloudflare import download_from_cloud; content = download_from_cloud(); sys.stdout.write(content) if content else (sys.stderr.write("ERROR: No content from R2\\n"), sys.exit(1))`
      
      try {
        const { stdout, stderr } = await execAsync(`python3 -c ${JSON.stringify(pythonCode)}`, {
          cwd: projectRoot,
          env: process.env,
          maxBuffer: 10 * 1024 * 1024, // 10MB buffer for large content
        })
        
        console.log('R2 download stdout length:', stdout?.length || 0)
        if (stderr) {
          console.error('R2 download stderr:', stderr)
        }
        
        if (stdout && stdout.trim()) {
          console.log('Successfully downloaded from R2, content length:', stdout.trim().length)
          return new NextResponse(stdout.trim(), {
            headers: {
              'Content-Type': 'text/markdown',
            },
          })
        } else {
          console.warn('R2 download returned empty content')
        }
      } catch (execError: any) {
        console.error('R2 download exec error:', execError.message)
        console.error('R2 download stderr:', execError.stderr || 'none')
        console.error('R2 download stdout:', execError.stdout || 'none')
        throw execError
      }
    } catch (r2Error: any) {
      // Log the error for debugging
      console.error('R2 download error:', r2Error.message)
      if (r2Error.stderr) {
        console.error('R2 download stderr:', r2Error.stderr)
      }
      // R2 not available, fall through to local file
    }

    // Fallback to local file (for local development)
    const possiblePaths = [
      join(process.cwd(), '..', 'output', 'adapted_reading_material.md'),
      join(process.cwd(), 'output', 'adapted_reading_material.md'),
    ]

    for (const filePath of possiblePaths) {
      try {
        const content = await readFile(filePath, 'utf-8')
        return new NextResponse(content, {
          headers: {
            'Content-Type': 'text/markdown',
          },
        })
      } catch (error) {
        continue
      }
    }

    // No file found
    return new NextResponse(
      `# Article not found\n\nPlease generate an article first.`,
      {
        status: 404,
        headers: {
          'Content-Type': 'text/markdown',
        },
      }
    )
  } catch (error: any) {
    return new NextResponse(
      `# Error\n\nFailed to load article: ${error.message}`,
      {
        status: 500,
        headers: {
          'Content-Type': 'text/markdown',
        },
      }
    )
  }
}

