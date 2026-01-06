import { NextResponse } from 'next/server'
import { S3Client, GetObjectCommand, ListObjectsV2Command } from '@aws-sdk/client-s3'

export async function GET() {
  // Read env vars at runtime
  const R2_BUCKET_NAME = process.env.R2_BUCKET_NAME || ''
  const R2_ACCOUNT_ID = process.env.R2_ACCOUNT_ID || ''
  const R2_ACCESS_KEY_ID = process.env.R2_ACCESS_KEY_ID || ''
  const R2_SECRET_ACCESS_KEY = process.env.R2_SECRET_ACCESS_KEY || ''

  const results: any = {
    env_check: {
      R2_BUCKET_NAME: R2_BUCKET_NAME ? 'set' : 'MISSING',
      R2_ACCOUNT_ID: R2_ACCOUNT_ID ? 'set' : 'MISSING',
      R2_ACCESS_KEY_ID: R2_ACCESS_KEY_ID ? 'set' : 'MISSING',
      R2_SECRET_ACCESS_KEY: R2_SECRET_ACCESS_KEY ? 'set' : 'MISSING',
    },
    tests: []
  }

  try {
    const s3Client = new S3Client({
      region: 'auto',
      endpoint: `https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com`,
      credentials: {
        accessKeyId: R2_ACCESS_KEY_ID,
        secretAccessKey: R2_SECRET_ACCESS_KEY,
      },
    })

    // Test 1: List objects in bucket
    try {
      const listCommand = new ListObjectsV2Command({
        Bucket: R2_BUCKET_NAME,
        Prefix: 'public/',
      })
      const listResponse = await s3Client.send(listCommand)
      results.tests.push({
        test: 'List objects in public/',
        success: true,
        files: listResponse.Contents?.map(obj => ({
          key: obj.Key,
          size: obj.Size,
          lastModified: obj.LastModified
        })) || []
      })
    } catch (error: any) {
      results.tests.push({
        test: 'List objects in public/',
        success: false,
        error: error.message
      })
    }

    // Test 2: Download specific file
    try {
      const getCommand = new GetObjectCommand({
        Bucket: R2_BUCKET_NAME,
        Key: 'public/adapted_reading_material.md',
      })
      const getResponse = await s3Client.send(getCommand)
      const content = await getResponse.Body?.transformToString()
      results.tests.push({
        test: 'Download public/adapted_reading_material.md',
        success: true,
        contentLength: content?.length || 0,
        preview: content?.substring(0, 200)
      })
    } catch (error: any) {
      results.tests.push({
        test: 'Download public/adapted_reading_material.md',
        success: false,
        error: error.message,
        errorCode: error.Code || error.code
      })
    }

  } catch (error: any) {
    results.tests.push({
      test: 'Create S3 client',
      success: false,
      error: error.message
    })
  }

  return NextResponse.json(results, { status: 200 })
}

