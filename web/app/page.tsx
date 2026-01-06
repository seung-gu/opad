'use client'

import { useState, useEffect, useRef } from 'react'
import MarkdownViewer from '@/components/MarkdownViewer'
import InputForm from '@/components/InputForm'

export default function Home() {
  const [content, setContent] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [progress, setProgress] = useState({ current_task: '', progress: 0, message: '' })
  const statusPollIntervalRef = useRef<NodeJS.Timeout | null>(null)

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
        setContent(text)
        setLoading(false)
      })
      .catch(() => {
        // On error, show generating message instead of "No article found"
        setContent('# Generating article...\n\nPlease wait. The article will appear here when ready.')
        setLoading(false)
      })
  }

  useEffect(() => {
    loadContent()
  }, [])
  
  // Poll status when generating
  useEffect(() => {
    if (!generating) {
      // Clear interval when not generating
      if (statusPollIntervalRef.current) {
        clearInterval(statusPollIntervalRef.current)
        statusPollIntervalRef.current = null
      }
      return
    }

    const loadStatus = () => {
      fetch('/api/status')
        .then(res => res.json())
        .then(data => {
          console.log('Status update:', data) // Debug log
          setProgress({
            current_task: data.current_task || '',
            progress: data.progress || 0,
            message: data.message || ''
          })
          if (data.status === 'completed') {
            setGenerating(false)
            loadContent()
          } else if (data.status === 'error') {
            setGenerating(false)
          }
        })
        .catch((err) => {
          console.error('Failed to fetch status:', err)
        })
    }
    
    // Load immediately
    loadStatus()
    
    // Set up polling interval
    const interval = setInterval(loadStatus, 2000) // Poll every 2 seconds
    statusPollIntervalRef.current = interval
    
    return () => {
      if (statusPollIntervalRef.current) {
        clearInterval(statusPollIntervalRef.current)
        statusPollIntervalRef.current = null
      }
    }
  }, [generating])
  
  // No need to poll content - status polling will trigger loadContent when completed

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
      
      // generating state is already true, useEffect will handle polling

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
          <div className="mb-2">
            <p className="text-blue-800 font-medium mb-2">
              ⏳ {progress.message || 'Generating article...'}
            </p>
            <div className="w-full bg-gray-200 rounded-full h-2.5">
              <div
                className="bg-blue-600 h-2.5 rounded-full transition-all duration-300"
                style={{ width: `${progress.progress}%` }}
              ></div>
            </div>
            <p className="text-sm text-blue-600 mt-1">{progress.progress}%</p>
          </div>
        </div>
      )}

      <MarkdownViewer content={content} />
    </main>
  )
}

