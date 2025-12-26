import { readFile } from 'fs/promises'
import { join, dirname } from 'path'
import { fileURLToPath } from 'url'
import { NextResponse } from 'next/server'

export async function GET() {
  try {
    // output 폴더의 마크다운 파일 읽기
    // 여러 경로 시도
    const possiblePaths = [
      join(process.cwd(), '..', 'output', 'adapted_reading_material.md'), // web/에서 실행 시
      join(process.cwd(), 'output', 'adapted_reading_material.md'), // opad/에서 실행 시
      '/Users/seung-gu/projects/opad/output/adapted_reading_material.md', // 절대 경로
    ]

    let content = ''
    let lastError: Error | null = null

    for (const filePath of possiblePaths) {
      try {
        content = await readFile(filePath, 'utf-8')
        break // 성공하면 루프 종료
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
      `# Article not found\n\nError: ${error.message}\n\nTried paths:\n- ${join(process.cwd(), '..', 'output', 'adapted_reading_material.md')}\n- ${join(process.cwd(), 'output', 'adapted_reading_material.md')}\n\nPlease generate an article first.\n\nRun: \`crewai run\` in the opad project.`,
      {
        status: 404,
        headers: {
          'Content-Type': 'text/markdown',
        },
      }
    )
  }
}

