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
      // Download from R2 using logging (outputs to stdout)
      const pythonCode = `import sys; import logging; logging.basicConfig(level=logging.INFO, format='%(message)s', handlers=[logging.StreamHandler(sys.stdout)], force=True); sys.path.insert(0, ${JSON.stringify(srcPath)}); from utils.cloudflare import download_from_cloud; content = download_from_cloud(); logging.info(content) if content else (logging.error("ERROR: No content from R2"), sys.exit(1))`
      const { stdout, stderr } = await execAsync(`python3 -c ${JSON.stringify(pythonCode)}`, {
        cwd: projectRoot,
        env: process.env,
      })
      
      if (stdout && stdout.trim()) {
        console.log('Successfully downloaded from R2')
        return new NextResponse(stdout.trim(), {
          headers: {
            'Content-Type': 'text/markdown',
          },
        })
      } else {
        console.warn('R2 download returned empty content')
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

