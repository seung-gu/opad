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

  const loadContent = (showLoading = true) => {
    if (showLoading) {
      setLoading(true)
    }
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
        // Only update if content actually changed
        setContent(prev => prev !== text ? text : prev)
        if (showLoading) {
          setLoading(false)
        }
      })
      .catch(() => {
        // On error, show generating message instead of "No article found"
        const errorMessage = '# Generating article...\n\nPlease wait. The article will appear here when ready.'
        setContent(prev => prev !== errorMessage ? errorMessage : prev)
        if (showLoading) {
          setLoading(false)
        }
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
          // Only update progress if it actually changed
          setProgress(prev => {
            const newProgress = {
              current_task: data.current_task || '',
              progress: data.progress || 0,
              message: data.message || ''
            }
            // Only update if something actually changed
            if (prev.current_task !== newProgress.current_task || 
                prev.progress !== newProgress.progress || 
                prev.message !== newProgress.message) {
              return newProgress
            }
            return prev
          })
          
          if (data.status === 'completed') {
            setGenerating(false)
            // Load content without showing loading screen
            loadContent(false)
            // Clear interval immediately
            if (statusPollIntervalRef.current) {
              clearInterval(statusPollIntervalRef.current)
              statusPollIntervalRef.current = null
            }
          } else if (data.status === 'error') {
            setGenerating(false)
            // Clear interval on error
            if (statusPollIntervalRef.current) {
              clearInterval(statusPollIntervalRef.current)
              statusPollIntervalRef.current = null
            }
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
      <div className="min-h-screen flex items-center justify-center bg-white">
        <div className="text-xl text-slate-900">Loading...</div>
      </div>
    )
  }

  return (
    <main className="min-h-screen p-8 max-w-4xl mx-auto bg-slate-900 rounded-lg shadow-2xl my-8">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold text-white">OPAD Reading Materials</h1>
        <div className="flex gap-2">
          <button
            onClick={() => loadContent(true)}
            className="bg-slate-700 text-white px-4 py-2 rounded-md hover:bg-slate-600 transition-colors"
          >
            Refresh
          </button>
          <button
            onClick={() => setShowForm(!showForm)}
            className="bg-emerald-600 text-white px-4 py-2 rounded-md hover:bg-emerald-500 transition-colors"
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
        <div className="mb-4 p-4 bg-slate-800 border border-slate-700 rounded-lg shadow-lg">
          <div className="mb-2">
            <p className="text-white font-medium mb-2">
              ⏳ {progress.message || 'Generating article...'}
            </p>
            <div className="w-full bg-slate-700 rounded-full h-3">
              <div
                className="bg-emerald-500 h-3 rounded-full transition-all duration-300"
                style={{ width: `${progress.progress}%` }}
              ></div>
            </div>
            <p className="text-sm text-emerald-400 mt-2">{progress.progress}%</p>
          </div>
        </div>
      )}

      <MarkdownViewer content={content} />
    </main>
  )
}

