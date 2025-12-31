import { NextRequest, NextResponse } from 'next/server'

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

    // Get GitHub token from environment variable
    const githubToken = process.env.GITHUB_TOKEN
    if (!githubToken) {
      return NextResponse.json(
        { error: 'GitHub token not configured' },
        { status: 500 }
      )
    }

    // Get repository info from environment or use defaults
    const repoOwner = process.env.GITHUB_REPO_OWNER || 'YOUR_USERNAME'
    const repoName = process.env.GITHUB_REPO_NAME || 'opad'

    // Create input file content
    const inputContent = JSON.stringify({
      language,
      level,
      length,
      topic,
      timestamp: new Date().toISOString()
    }, null, 2)

    // Create or update the input file in GitHub
    const filePath = 'input.json'
    const apiUrl = `https://api.github.com/repos/${repoOwner}/${repoName}/contents/${filePath}`

    // Check if file exists
    let sha: string | undefined
    try {
      const getResponse = await fetch(apiUrl, {
        headers: {
          'Authorization': `token ${githubToken}`,
          'Accept': 'application/vnd.github.v3+json'
        }
      })
      if (getResponse.ok) {
        const fileData = await getResponse.json()
        sha = fileData.sha
      }
    } catch (error) {
      // File doesn't exist, will create new one
    }

    // Create or update file
    const content = Buffer.from(inputContent).toString('base64')
    const response = await fetch(apiUrl, {
      method: 'PUT',
      headers: {
        'Authorization': `token ${githubToken}`,
        'Accept': 'application/vnd.github.v3+json',
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        message: `Update input: ${topic}`,
        content: content,
        ...(sha && { sha })
      })
    })

    if (!response.ok) {
      const error = await response.text()
      return NextResponse.json(
        { error: `GitHub API error: ${error}` },
        { status: response.status }
      )
    }

    // Workflow will be automatically triggered by push event on input.json
    return NextResponse.json({
      success: true,
      message: 'Input saved. Workflow will start automatically.'
    })
  } catch (error: any) {
    return NextResponse.json(
      { error: error.message || 'Internal server error' },
      { status: 500 }
    )
  }
}

