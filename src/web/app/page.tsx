'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import MarkdownViewer from '@/components/MarkdownViewer'
import InputForm from '@/components/InputForm'

export default function Home() {
  const router = useRouter()
  const [content, setContent] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [progress, setProgress] = useState({ current_task: '', progress: 0, message: '', error: null as string | null })
  const [currentJobId, setCurrentJobId] = useState<string | null>(null)
  const [currentArticleId, setCurrentArticleId] = useState<string | null>(null)
  const statusPollIntervalRef = useRef<NodeJS.Timeout | null>(null)
  const fetchAbortControllerRef = useRef<AbortController | null>(null)

  const loadContent = useCallback((showLoading = true, articleId?: string | null) => {
    // Use provided articleId or fall back to currentArticleId
    const targetArticleId = articleId !== undefined ? articleId : currentArticleId
    
    // Cancel any pending fetch request to prevent race conditions
    if (fetchAbortControllerRef.current) {
      fetchAbortControllerRef.current.abort()
      fetchAbortControllerRef.current = null
    }
    
    if (showLoading) {
      setLoading(true)
    }
    
    // If no article_id, show welcome message
    if (!targetArticleId) {
      const welcomeMessage = `# 👋 Welcome to One Story A Day

**One Story A Day** is an AI-powered tool that creates personalized reading materials for language learners using real, current news content.

🌍 **One Story A Day supports all languages** — choose any language you want to learn and get customized reading materials at your proficiency level.

---

## ✨ How It Works

Generate an article by choosing your topic, language, and proficiency level:

**1. 🔍 Search**  
One Story A Day searches the web for recent news articles, stories, and other content on your topic.

**2. 📚 Collect**  
It gathers relevant articles from various sources.

**3. 🎨 Transform**  
The content is adapted to match your language level.

**4. 📖 Deliver**  
You receive a customized study resource ready to use.

Instead of outdated textbooks, get **real, current news content, stories, and other content** tailored to your learning needs. 🚀

---

## 🎯 Get Started

Click **"Generate New Article"** above to create your first reading material, or click **"Articles"** to view and manage all your generated articles.

Choose a topic you're interested in and start learning with content that matches your level! 💪`
      setContent(prev => prev !== welcomeMessage ? welcomeMessage : prev)
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
    fetch(`/api/articles/${targetArticleId}/content?t=${timestamp}`, {
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
          // Only clear ref if it still points to this controller
          // This prevents race conditions when multiple fetches are triggered
          if (fetchAbortControllerRef.current === abortController) {
            fetchAbortControllerRef.current = null
          }
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
          // Only clear ref if it still points to this controller
          // This prevents race conditions when multiple fetches are triggered
          if (fetchAbortControllerRef.current === abortController) {
            fetchAbortControllerRef.current = null
          }
          console.error('Failed to load article:', error)
        }
      })
  }, [currentArticleId])

  useEffect(() => {
    // Call loadContent when currentArticleId changes
    // loadContent handles the case when currentArticleId is null (shows welcome message)
    // Only load if not currently generating (to prevent flicker when cancelling duplicate)
    // Note: We call loadContent even when currentArticleId is null to show welcome message
    // Don't auto-load when generating becomes false - let the completion handler manage that
    if (!generating) {
      // Only load if currentArticleId is set, or if content is empty (show welcome message)
      if (currentArticleId || !content) {
        loadContent(true)
      }
    }
    
    // Cleanup: cancel any pending fetch when article_id changes or component unmounts
    return () => {
      if (fetchAbortControllerRef.current) {
        fetchAbortControllerRef.current.abort()
        fetchAbortControllerRef.current = null
      }
    }
  }, [currentArticleId, generating, loadContent])
  
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
            // Show success message instead of loading article
            const successMessage = `# ✅ Article Generation Complete!\n\nYour article has been successfully generated.\n\nPlease go to **Articles** page to view and read your new article.`
            setContent(successMessage)
            setCurrentArticleId(null) // Clear articleId so it doesn't auto-load
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
    const interval = setInterval(loadStatus, 5000) // Poll every 5 seconds
    statusPollIntervalRef.current = interval
    
    return () => {
      if (statusPollIntervalRef.current) {
        clearInterval(statusPollIntervalRef.current)
        statusPollIntervalRef.current = null
      }
    }
  }, [generating, currentJobId, loadContent])
  
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

      // Handle duplicate job (409 Conflict) - must check before general error handling
      // since 409 has response.ok === false
      if (response.status === 409 || data.duplicate) {
        // If existing_job is null, job status data couldn't be retrieved
        if (!data.existing_job) {
          // Still show message and allow regeneration
          const shouldRegenerate = window.confirm(
            'A duplicate job was detected, but its status could not be retrieved. Do you want to generate a new article anyway?'
          )
          if (shouldRegenerate) {
            return await handleGenerate(inputs, true)
          }
          // User cancelled: clear generating state
          setGenerating(false)
          return
        }
        
        const job = data.existing_job
        const messages: Record<string, string> = {
          completed: 'A completed job exists within the last 24 hours. Do you want to generate new?',
          running: `A running job exists (${job.progress}%). Do you want to generate new?`,
          failed: `Previous job failed: ${job.error || 'Unknown error'}. Do you want to generate new?`,
          queued: 'A queued job already exists. Do you want to generate new?'
        }
        
        // User confirms: generate new job (OK = true)
        if (window.confirm(messages[job.status])) {
          return await handleGenerate(inputs, true)
        }
        
        // User cancels: use existing job (Cancel = false)
        if (job.status === 'completed' && data.article_id) {
          // Load content directly without showing loading state to prevent flicker
          if (currentArticleId !== data.article_id) {
            // Load content first (generating is still true, so useEffect won't trigger)
            loadContent(false, data.article_id)
            // Then update state and set generating to false
            // useEffect will see generating=false but content is already loaded
            setCurrentArticleId(data.article_id)
          }
          setGenerating(false)
        } else if (job.status === 'running' || job.status === 'queued') {
          // Set both jobId and articleId so content can be loaded when job completes
          setCurrentJobId(job.id)
          if (data.article_id) {
            setCurrentArticleId(data.article_id)
          }
          setGenerating(true)
        } else if (job.status === 'failed') {
          // Failed job: show error message to user
          const errorMessage = `# ❌ Generation Failed\n\n**Error:** ${job.error || 'Unknown error occurred'}\n\nPlease try generating a new article.`
          setContent(errorMessage)
          setProgress(prev => ({
            ...prev,
            error: job.error || 'Generation failed',
            message: 'Previous generation failed',
            progress: 0
          }))
          setGenerating(false)
        } else {
          setGenerating(false)
        }
        return
      }

      // Handle other non-2xx errors (409 duplicate is already handled above)
      if (!response.ok) {
        throw new Error(data.error || 'Failed to generate article')
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
    <main className="min-h-screen p-8 max-w-4xl mx-auto bg-white rounded-lg shadow-2xl my-8">
      <div className="flex justify-end items-center mb-8 gap-3">
        <button
          onClick={() => router.push('/articles')}
          className="bg-gray-700 text-white px-6 py-2.5 rounded-lg hover:bg-gray-600 transition-colors font-medium"
        >
          Articles
        </button>
        <button
          onClick={() => setShowForm(!showForm)}
          className="bg-emerald-600 text-white px-6 py-2.5 rounded-lg hover:bg-emerald-500 transition-colors font-medium"
        >
          {showForm ? 'Hide Form' : 'Generate New Article'}
        </button>
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

      <MarkdownViewer content={content} dark={false} clickable={false} />
    </main>
  )
}

