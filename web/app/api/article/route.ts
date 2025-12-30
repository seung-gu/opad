import { readFile } from 'fs/promises'
import { join } from 'path'
import { NextResponse } from 'next/server'

export async function GET() {
  try {
    // Try to read from output folder (for local development)
    // Fallback to public folder (for Vercel deployment)
    const possiblePaths = [
      // Local development: output folder (priority)
      join(process.cwd(), '..', 'output', 'adapted_reading_material.md'),
      join(process.cwd(), 'output', 'adapted_reading_material.md'),
      // Vercel/production: public folder (fallback)
      join(process.cwd(), 'public', 'adapted_reading_material.md'),
    ]

    let content = ''
    let lastError: Error | null = null

    for (const filePath of possiblePaths) {
      try {
        content = await readFile(filePath, 'utf-8')
        break // Exit loop on success
      } catch (error: any) {
        lastError = error
        continue
      }
    }

    if (!content) {
      throw lastError || new Error('File not found in any of the attempted paths')
    }

    return new NextResponse(content, {
      headers: {
        'Content-Type': 'text/markdown',
      },
    })
  } catch (error: any) {
    return new NextResponse(
      `# Article not found\n\nPlease generate an article first.\n\n**For local development:**\nRun: \`crewai run\` in the opad project\n\n**For Vercel deployment:**\nCopy the output file to web/public/adapted_reading_material.md`,
      {
        status: 404,
        headers: {
          'Content-Type': 'text/markdown',
        },
      }
    )
  }
}

