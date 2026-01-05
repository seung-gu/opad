'use client'

import { useState, useEffect, useRef } from 'react'
import MarkdownViewer from '@/components/MarkdownViewer'
import InputForm from '@/components/InputForm'

export default function Home() {
  const [content, setContent] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [lastContent, setLastContent] = useState<string>('')
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null)

  const loadContent = () => {
    setLoading(true)
    // Add timestamp to bypass cache
    const timestamp = new Date().getTime()
    // Use API route (works on Railway, Docker, and local development)
    // API route fetches from R2 or falls back to local file
    fetch(`/api/article?t=${timestamp}`)
      .then(res => {
        if (res.ok) {
          return res.text()
        }
        throw new Error('Failed to fetch article')
      })
      .then(text => {
        // Check if content has changed (new article generated)
        if (text !== lastContent && lastContent !== '' && text !== '# No article found\n\nClick "Generate New Article" to create one.') {
          setGenerating(false) // Stop generating state if new content detected
          // Clear polling interval if content changed
          if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current)
            pollIntervalRef.current = null
          }
        }
        setContent(text)
        setLastContent(text)
        setLoading(false)
      })
      .catch(() => {
        setContent('# No article found\n\nClick "Generate New Article" to create one.')
        setLoading(false)
      })
  }

  useEffect(() => {
    loadContent()
    
    // Cleanup polling interval on unmount
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current)
      }
    }
  }, [])

  const handleGenerate = async (inputs: {
    language: string
    level: string
    length: string
    topic: string
  }) => {
    setGenerating(true)
    try {
      const response = await fetch('/api/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(inputs),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || 'Failed to generate article')
      }

      // Show success message
      alert('Article generation started! It will take a few minutes. The page will update automatically when ready.')

      // Poll for updated content (every 10 seconds for faster updates)
      let pollCount = 0
      const maxPolls = 120 // 10 seconds * 120 = 20 minutes max
      
      const interval = setInterval(() => {
        pollCount++
        loadContent()
        
        // Stop polling after max attempts
        if (pollCount >= maxPolls) {
          clearInterval(interval)
          pollIntervalRef.current = null
          setGenerating(false)
          alert('Article generation may still be in progress. Please refresh the page manually.')
        }
      }, 10000) // Poll every 10 seconds
      
      pollIntervalRef.current = interval

    } catch (error: any) {
      alert(`Error: ${error.message}`)
      setGenerating(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-xl">Loading...</div>
      </div>
    )
  }

  return (
    <main className="min-h-screen p-8 max-w-4xl mx-auto">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold">OPAD Reading Materials</h1>
        <div className="flex gap-2">
          <button
            onClick={loadContent}
            className="bg-gray-600 text-white px-4 py-2 rounded-md hover:bg-gray-700 transition-colors"
          >
            Refresh
          </button>
          <button
            onClick={() => setShowForm(!showForm)}
            className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition-colors"
          >
            {showForm ? 'Hide Form' : 'Generate New Article'}
          </button>
        </div>
      </div>

      {showForm && (
        <div className="mb-8">
          <InputForm onSubmit={handleGenerate} loading={generating} />
        </div>
      )}

      {generating && (
        <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-md">
          <p className="text-blue-800">
            ⏳ Generating article... This may take a few minutes. The page will update automatically when ready.
          </p>
        </div>
      )}

      <MarkdownViewer content={content} />
    </main>
  )
}

