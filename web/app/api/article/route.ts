import { readFile } from 'fs/promises'
import { join } from 'path'
import { NextResponse } from 'next/server'
import { S3Client, GetObjectCommand } from '@aws-sdk/client-s3'

// Prevent static optimization - only run at request time
export const dynamic = 'force-dynamic'
export const fetchCache = 'force-no-store'

const R2_DIRECTORY = 'public'
const ARTICLE_FILENAME = 'adapted_reading_material.md'
const DEFAULT_ARTICLE_PATH = `${R2_DIRECTORY}/${ARTICLE_FILENAME}`

// Create S3 client for R2 - read env vars at runtime
function getR2Client() {
  const R2_BUCKET_NAME = process.env.R2_BUCKET_NAME || ''
  const R2_ACCOUNT_ID = process.env.R2_ACCOUNT_ID || ''
  const R2_ACCESS_KEY_ID = process.env.R2_ACCESS_KEY_ID || ''
  const R2_SECRET_ACCESS_KEY = process.env.R2_SECRET_ACCESS_KEY || ''
  
  if (!R2_BUCKET_NAME || !R2_ACCOUNT_ID || !R2_ACCESS_KEY_ID || !R2_SECRET_ACCESS_KEY) {
    return null
  }
  
  return new S3Client({
    region: 'auto',
    endpoint: `https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com`,
    credentials: {
      accessKeyId: R2_ACCESS_KEY_ID,
      secretAccessKey: R2_SECRET_ACCESS_KEY,
    },
  })
}

export async function GET() {
  try {
    // Try R2 first (production)
    try {
      const s3Client = getR2Client()
      if (!s3Client) {
        throw new Error('R2 client not available')
      }
      
      const R2_BUCKET_NAME = process.env.R2_BUCKET_NAME || ''
      const command = new GetObjectCommand({
        Bucket: R2_BUCKET_NAME,
        Key: DEFAULT_ARTICLE_PATH,
      })
      
      const response = await s3Client.send(command)
      const content = await response.Body?.transformToString()
      
      if (content && content.length > 0) {
        console.log(JSON.stringify({
          source: 'web',
          level: 'info',
          endpoint: '/api/article',
          message: `Successfully loaded article from R2 (${content.length} bytes)`
        }))
        return new NextResponse(content, {
          headers: {
            'Content-Type': 'text/markdown',
          },
        })
      }
    } catch (r2Error: any) {
      console.error(JSON.stringify({
        source: 'web',
        level: 'error',
        endpoint: '/api/article',
        message: `R2 download error: ${r2Error.message}`
      }))
      // Fall through to local file
    }

    // Fallback to local file (for local development)
    const possiblePaths = [
      join(process.cwd(), '..', 'output', 'adapted_reading_material.md'),
      join(process.cwd(), 'output', 'adapted_reading_material.md'),
    ]

    for (const filePath of possiblePaths) {
      try {
        const content = await readFile(filePath, 'utf-8')
        console.log(JSON.stringify({
          source: 'web',
          level: 'info',
          endpoint: '/api/article',
          message: `Successfully loaded article from local file: ${filePath}`
        }))
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
      `# No article found\n\nClick "Generate New Article" to create one.`,
      {
        status: 404,
        headers: {
          'Content-Type': 'text/markdown',
        },
      }
    )
  } catch (error: any) {
    console.error(JSON.stringify({
      source: 'web',
      level: 'error',
      endpoint: '/api/article',
      message: `Fatal error: ${error.message}`
    }))
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

