'use client'

import { useState, useEffect, useRef } from 'react'
import MarkdownViewer from '@/components/MarkdownViewer'
import InputForm from '@/components/InputForm'

export default function Home() {
  const [content, setContent] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [progress, setProgress] = useState({ current_task: '', progress: 0, message: '', error: null as string | null })
  const [currentJobId, setCurrentJobId] = useState<string | null>(null)
  const [currentArticleId, setCurrentArticleId] = useState<string | null>(null)
  const statusPollIntervalRef = useRef<NodeJS.Timeout | null>(null)
  const fetchAbortControllerRef = useRef<AbortController | null>(null)

  // Load latest article on mount
  useEffect(() => {
    const loadLatestArticle = async () => {
      try {
        // Call through Next.js API route to avoid CORS issues
        const response = await fetch('/api/latest')
        
        if (response.ok) {
          const article = await response.json()
          setCurrentArticleId(article.id)
          console.log('Loaded latest article:', article.id)
          setLoading(false)
        } else if (response.status === 404) {
          // No articles exist yet - this is normal for first-time users
          console.log('No articles found - showing welcome message')
          setLoading(false)
        } else {
          console.error('Failed to load latest article:', response.statusText)
          setLoading(false)
        }
      } catch (error) {
        console.error('Error loading latest article:', error)
        setLoading(false)
      }
    }
    
    loadLatestArticle()
  }, []) // Only run on mount

  const loadContent = (showLoading = true) => {
    // Cancel any pending fetch request to prevent race conditions
    if (fetchAbortControllerRef.current) {
      fetchAbortControllerRef.current.abort()
      fetchAbortControllerRef.current = null
    }
    
    if (showLoading) {
      setLoading(true)
    }
    
    // If no article_id, show message
    if (!currentArticleId) {
      const errorMessage = '# No article selected\n\nClick "Generate New Article" to create one.'
      setContent(prev => prev !== errorMessage ? errorMessage : prev)
      if (showLoading) {
        setLoading(false)
      }
      return
    }
    
    // Create new AbortController for this request
    const abortController = new AbortController()
    fetchAbortControllerRef.current = abortController
    
    // Add timestamp to bypass cache
    const timestamp = new Date().getTime()
    // Call FastAPI through web API route
    fetch(`/api/article?article_id=${currentArticleId}&t=${timestamp}`, {
      signal: abortController.signal
    })
      .then(res => {
        if (res.ok) {
          return res.text()
        }
        throw new Error('Failed to fetch article')
      })
      .then(text => {
        // Only update if this request wasn't aborted
        if (!abortController.signal.aborted) {
          setContent(prev => prev !== text ? text : prev)
          if (showLoading) {
            setLoading(false)
          }
          fetchAbortControllerRef.current = null
        }
      })
      .catch((error) => {
        // Ignore abort errors (expected when cancelling)
        if (error.name === 'AbortError') {
          return
        }
        // On error, show error message
        if (!abortController.signal.aborted) {
          const errorMessage = `# ⚠️ Error Loading Article\n\n**Failed to load article content.**\n\nThis could be due to:\n- Database connection issue\n- Article not found\n- Network error\n\nPlease try:\n- Clicking "Refresh" button\n- Generating a new article`
          setContent(prev => prev !== errorMessage ? errorMessage : prev)
          if (showLoading) {
            setLoading(false)
          }
          fetchAbortControllerRef.current = null
          console.error('Failed to load article:', error)
        }
      })
  }

  useEffect(() => {
    // Always call loadContent on mount or when currentArticleId changes
    // loadContent handles the case when currentArticleId is null (shows message)
    loadContent(true)
    
    // Cleanup: cancel any pending fetch when article_id changes or component unmounts
    return () => {
      if (fetchAbortControllerRef.current) {
        fetchAbortControllerRef.current.abort()
        fetchAbortControllerRef.current = null
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentArticleId])
  
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
      // jobId가 없으면 폴링하지 않음
      if (!currentJobId) {
        return
      }
      
      fetch(`/api/status?job_id=${currentJobId}`)
        .then(res => res.json())
        .then(data => {
          // Only update progress if it actually changed
          setProgress(prev => {
            const newProgress = {
              current_task: data.current_task || '',
              progress: data.progress || 0,
              message: data.message || '',
              error: data.error || null
            }
            // Only update if something actually changed
            if (prev.current_task !== newProgress.current_task || 
                prev.progress !== newProgress.progress || 
                prev.message !== newProgress.message ||
                prev.error !== newProgress.error) {
              return newProgress
            }
            return prev
          })
          
          if (data.status === 'completed') {
            setGenerating(false)
            setCurrentJobId(null) // Clear jobId
            // Load content without showing loading screen
            loadContent(false)
            // Clear interval immediately
            if (statusPollIntervalRef.current) {
              clearInterval(statusPollIntervalRef.current)
              statusPollIntervalRef.current = null
            }
          } else if (data.status === 'error') {
            setGenerating(false)
            setCurrentJobId(null) // Clear jobId
            // Show error message in content area
            const errorMessage = `# ❌ Generation Failed\n\n**Error:** ${data.error || data.message || 'Unknown error occurred'}\n\nPlease try generating a new article.`
            setContent(errorMessage)
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
  }, [generating, currentJobId])
  
  // No need to poll content - status polling will trigger loadContent when completed

  const handleGenerate = async (inputs: {
    language: string
    level: string
    length: string
    topic: string
  }, force: boolean = false) => {
    setGenerating(true)
    try {
      const response = await fetch('/api/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ ...inputs, force }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || 'Failed to generate article')
      }

      // Handle duplicate job - ask user to generate new or use existing
      if (data.duplicate && data.existing_job) {
        const job = data.existing_job
        const messages: Record<string, string> = {
          succeeded: 'A completed job exists. Do you want to generate new?',
          running: `A running job exists (${job.progress}%). Do you want to generate new?`,
          failed: `Previous job failed: ${job.error || 'Unknown error'}. Do you want to generate new?`,
          queued: 'A queued job exists. Do you want to generate new?'
        }
        
        // User confirms: generate new job (OK = true)
        if (window.confirm(messages[job.status])) {
          return handleGenerate(inputs, true)
        }
        
        // User cancels: use existing job (Cancel = false)
        if (job.status === 'succeeded' && data.article_id) {
          setCurrentArticleId(data.article_id)
          loadContent(true)
          setGenerating(false)
        } else if (job.status === 'running' || job.status === 'queued') {
          setCurrentJobId(job.id)
          setGenerating(true)
        } else {
          setGenerating(false)
        }
        return
      }

      // Save jobId and articleId for polling
      if (data.job_id) {
        setCurrentJobId(data.job_id)
      }
      if (data.article_id) {
        setCurrentArticleId(data.article_id)
      }

      // Show success message
      alert('Article generation started! It will take a few minutes. The page will update automatically when ready.')
      
      // generating state is already true, useEffect will handle polling

    } catch (error: any) {
      alert(`Error: ${error.message}`)
      setGenerating(false)
      setCurrentJobId(null) // Clear jobId on error
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
            {progress.error && (
              <div className="mb-2 p-3 bg-red-900/50 border border-red-700 rounded-md">
                <p className="text-red-300 text-sm font-medium">Error:</p>
                <p className="text-red-200 text-sm">{progress.error}</p>
              </div>
            )}
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

