import { NextResponse } from 'next/server'
import { S3Client, GetObjectCommand, ListObjectsV2Command } from '@aws-sdk/client-s3'

export async function GET() {
  // Read env vars at runtime
  const R2_BUCKET_NAME = process.env.R2_BUCKET_NAME || ''
  const R2_ACCOUNT_ID = process.env.R2_ACCOUNT_ID || ''
  const R2_ACCESS_KEY_ID = process.env.R2_ACCESS_KEY_ID || ''
  const R2_SECRET_ACCESS_KEY = process.env.R2_SECRET_ACCESS_KEY || ''

  // Debug: Show all env vars starting with R2_
  const allR2Envs: any = {}
  Object.keys(process.env).forEach(key => {
    if (key.startsWith('R2_')) {
      allR2Envs[key] = process.env[key] ? `${process.env[key]?.substring(0, 10)}...` : 'empty'
    }
  })

  // Debug: Show ALL env var keys (not values, just keys)
  const allEnvKeys = Object.keys(process.env).sort()

  const results: any = {
    debug_total_env_count: allEnvKeys.length,
    debug_all_env_keys: allEnvKeys,
    debug_all_r2_env_keys: Object.keys(process.env).filter(k => k.startsWith('R2_')),
    debug_all_r2_envs: allR2Envs,
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

