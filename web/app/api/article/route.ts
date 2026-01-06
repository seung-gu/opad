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
    console.error('Missing R2 credentials:', {
      R2_BUCKET_NAME: R2_BUCKET_NAME ? 'set' : 'MISSING',
      R2_ACCOUNT_ID: R2_ACCOUNT_ID ? 'set' : 'MISSING',
      R2_ACCESS_KEY_ID: R2_ACCESS_KEY_ID ? 'set' : 'MISSING',
      R2_SECRET_ACCESS_KEY: R2_SECRET_ACCESS_KEY ? 'set' : 'MISSING',
    })
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
      console.error('=== R2 Download Attempt ===')
      console.error('DEFAULT_ARTICLE_PATH:', DEFAULT_ARTICLE_PATH)
      
      const s3Client = getR2Client()
      if (!s3Client) {
        console.error('R2 client is null - missing credentials')
        throw new Error('R2 client not available - check environment variables')
      }
      
      console.error('R2 client created successfully')
      console.error('Attempting to download:', DEFAULT_ARTICLE_PATH)
      
      const R2_BUCKET_NAME = process.env.R2_BUCKET_NAME || ''
      const command = new GetObjectCommand({
        Bucket: R2_BUCKET_NAME,
        Key: DEFAULT_ARTICLE_PATH,
      })
      
      const response = await s3Client.send(command)
      console.error('R2 response received, status:', response.$metadata.httpStatusCode)
      
      const content = await response.Body?.transformToString()
      
      if (content && content.length > 0) {
        console.error('✅ Successfully downloaded from R2, content length:', content.length)
        return new NextResponse(content, {
          headers: {
            'Content-Type': 'text/markdown',
          },
        })
      } else {
        console.error('R2 download returned empty content')
        throw new Error('R2 returned empty content')
      }
    } catch (r2Error: any) {
      console.error('❌ R2 download failed:', r2Error.message)
      console.error('R2 error name:', r2Error.name)
      console.error('R2 error code:', r2Error.Code || r2Error.code)
      if (r2Error.$metadata) {
        console.error('R2 metadata:', JSON.stringify(r2Error.$metadata, null, 2))
      }
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
        console.error('✅ Loaded from local file:', filePath)
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
    console.error('No article found in R2 or local files')
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
    console.error('Fatal error in GET /api/article:', error)
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

