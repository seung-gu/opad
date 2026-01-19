'use client'

import { useState, useEffect, useRef } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import MarkdownViewer from '@/components/MarkdownViewer'
import ArticleStatusBadge from '@/components/ArticleStatusBadge'
import { Article } from '@/types/article'

/**
 * Article detail page.
 * 
 * Displays:
 * - Article metadata
 * - Article content (markdown)
 * - Status badge
 * - Progress bar (when status is 'running')
 * - Back to list link
 */
export default function ArticleDetailPage() {
  const params = useParams()
  const router = useRouter()
  const articleId = params.id as string

  const [article, setArticle] = useState<Article | null>(null)
  const [content, setContent] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [progress, setProgress] = useState({ current_task: '', progress: 0, message: '', error: null as string | null })
  const [currentJobId, setCurrentJobId] = useState<string | null>(null)
  const statusPollIntervalRef = useRef<NodeJS.Timeout | null>(null)

  // Load article metadata and content
  useEffect(() => {
    const fetchArticle = async () => {
      try {
        setLoading(true)
        setError(null)

        // Fetch article metadata via Next.js API route
        const metadataResponse = await fetch(`/api/articles/${articleId}`)
        if (metadataResponse.ok) {
          const articleData: Article = await metadataResponse.json()
          setArticle(articleData)
          // Set job_id for polling (same as main page)
          if (articleData.job_id) {
            setCurrentJobId(articleData.job_id)
          }
        } else if (metadataResponse.status === 404) {
          throw new Error('Article not found')
        }

        // Fetch article content
        const contentResponse = await fetch(`/api/article?article_id=${articleId}`)
        
        if (!contentResponse.ok) {
          if (contentResponse.status === 404) {
            setContent('# Article content not found\n\nThe article may still be processing.')
            return
          }
          throw new Error('Failed to load article content')
        }

        const contentText = await contentResponse.text()
        setContent(contentText)
      } catch (err: any) {
        setError(err.message || 'Failed to load article')
        console.error('Error fetching article:', err)
      } finally {
        setLoading(false)
      }
    }

    if (articleId) {
      fetchArticle()
    }
  }, [articleId])

  // Poll status when article is running (same logic as main page)
  useEffect(() => {
    // Only poll if article is running
    if (!article || article.status !== 'running') {
      // Clear interval when not running
      if (statusPollIntervalRef.current) {
        clearInterval(statusPollIntervalRef.current)
        statusPollIntervalRef.current = null
      }
      return
    }

    const loadStatus = () => {
      // If no jobId, don't poll
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
            setCurrentJobId(null) // Clear jobId (same as main page)
            // Reload article metadata and content
            const fetchArticle = async () => {
              try {
                const metadataResponse = await fetch(`/api/articles/${articleId}`)
                if (metadataResponse.ok) {
                  const articleData: Article = await metadataResponse.json()
                  setArticle(articleData)
                }

                const contentResponse = await fetch(`/api/article?article_id=${articleId}`)
                if (contentResponse.ok) {
                  const contentText = await contentResponse.text()
                  setContent(contentText)
                }
              } catch (err) {
                console.error('Error reloading article:', err)
              }
            }
            fetchArticle()
            // Clear interval immediately
            if (statusPollIntervalRef.current) {
              clearInterval(statusPollIntervalRef.current)
              statusPollIntervalRef.current = null
            }
          } else if (data.status === 'error') {
            setCurrentJobId(null) // Clear jobId (same as main page)
            // Reload article metadata to reflect failed status
            const fetchArticle = async () => {
              try {
                const metadataResponse = await fetch(`/api/articles/${articleId}`)
                if (metadataResponse.ok) {
                  const articleData: Article = await metadataResponse.json()
                  setArticle(articleData)
                }
              } catch (err) {
                console.error('Error reloading article:', err)
              }
            }
            fetchArticle()
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
  }, [article, currentJobId, articleId])

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 py-8">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="animate-pulse">
            <div className="h-8 bg-gray-200 rounded w-3/4 mb-4"></div>
            <div className="h-4 bg-gray-200 rounded w-1/2 mb-8"></div>
            <div className="space-y-4">
              <div className="h-4 bg-gray-200 rounded"></div>
              <div className="h-4 bg-gray-200 rounded w-5/6"></div>
              <div className="h-4 bg-gray-200 rounded w-4/6"></div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (error || !article) {
    return (
      <div className="min-h-screen bg-gray-50 py-8">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="bg-red-50 border border-red-200 rounded-lg p-6">
            <h2 className="text-xl font-semibold text-red-900 mb-2">Error</h2>
            <p className="text-red-800 mb-4">{error || 'Article not found'}</p>
            <Link
              href="/articles"
              className="text-blue-600 hover:text-blue-800 underline"
            >
              ← Back to Articles
            </Link>
          </div>
        </div>
      </div>
    )
  }

  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString)
      return new Intl.DateTimeFormat('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      }).format(date)
    } catch {
      return dateString
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-6">
          <Link
            href="/articles"
            className="text-blue-600 hover:text-blue-800 text-sm mb-4 inline-block"
          >
            ← Back to Articles
          </Link>
          
          <div className="flex items-start justify-between gap-4 mb-4">
            <div className="flex-1">
              <h1 className="text-3xl font-bold text-gray-900 mb-2">
                {article.topic || 'Untitled Article'}
              </h1>
              <div className="flex flex-wrap items-center gap-3 text-sm text-gray-600 mb-2">
                <span className="font-medium">{article.language}</span>
                <span>•</span>
                <span>Level {article.level}</span>
                <span>•</span>
                <span>{article.length} words</span>
              </div>
              <div className="text-xs text-gray-500">
                Created: {formatDate(article.created_at)}
              </div>
            </div>
            <ArticleStatusBadge status={article.status} />
          </div>
        </div>

        {/* Progress Bar (only when running) */}
        {article.status === 'running' && currentJobId && (
          <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg shadow-sm">
            <div className="mb-2">
              <p className="text-gray-800 font-medium mb-2">
                ⏳ {progress.message || 'Generating article...'}
              </p>
              {progress.error && (
                <div className="mb-2 p-3 bg-red-50 border border-red-200 rounded-md">
                  <p className="text-red-800 text-sm font-medium">Error:</p>
                  <p className="text-red-700 text-sm">{progress.error}</p>
                </div>
              )}
              <div className="w-full bg-gray-200 rounded-full h-3">
                <div
                  className="bg-blue-600 h-3 rounded-full transition-all duration-300"
                  style={{ width: `${progress.progress}%` }}
                ></div>
              </div>
              <p className="text-sm text-blue-700 mt-2">{progress.progress}%</p>
            </div>
          </div>
        )}

        {/* Content */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          {content ? (
            <MarkdownViewer content={content} language={article?.language} />
          ) : (
            <div className="text-center py-12">
              <p className="text-gray-500">
                {article.status === 'running'
                  ? 'Article is being generated. Please check back later.'
                  : 'Article content is not available.'}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
