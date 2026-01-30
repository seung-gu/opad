'use client'

import { useState, useEffect, useCallback } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import MarkdownViewer from '@/components/MarkdownViewer'
import ArticleStatusBadge from '@/components/ArticleStatusBadge'
import VocabularyList from '@/components/VocabularyList'
import { Article, Vocabulary } from '@/types/article'
import { fetchWithAuth } from '@/lib/api'
import { useVocabularyDelete } from '@/hooks/useVocabularyDelete'
import { formatDate } from '@/lib/formatters'
import { useStatusPolling } from '@/hooks/useStatusPolling'

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
  const { deleteVocabulary } = useVocabularyDelete()

  const [article, setArticle] = useState<Article | null>(null)
  const [content, setContent] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [currentJobId, setCurrentJobId] = useState<string | null>(null)
  const [vocabularies, setVocabularies] = useState<Vocabulary[]>([])

  // Reload article data (used by status polling on completion)
  const reloadArticleData = useCallback(async () => {
    try {
      const metadataResponse = await fetchWithAuth(`/api/articles/${articleId}`)
      if (metadataResponse.ok) {
        const articleData: Article = await metadataResponse.json()
        setArticle(articleData)
        if (articleData.job_id) {
          setCurrentJobId(articleData.job_id)
        } else {
          setCurrentJobId(null)
        }
      }

      const contentResponse = await fetchWithAuth(`/api/articles/${articleId}/content`)
      if (contentResponse.ok) {
        const contentText = await contentResponse.text()
        setContent(contentText)
      }
    } catch (err) {
      console.error('Error reloading article:', err)
    }
  }, [articleId])

  // Use status polling hook
  const { progress } = useStatusPolling({
    jobId: currentJobId,
    enabled: article?.status === 'running',
    onComplete: () => {
      setCurrentJobId(null)
      reloadArticleData()
    },
    onError: () => {
      setCurrentJobId(null)
      reloadArticleData()
    }
  })

  // Load article metadata and content
  useEffect(() => {
    const fetchArticle = async () => {
      try {
        setLoading(true)
        setError(null)

        // Fetch article metadata via Next.js API route
        const metadataResponse = await fetchWithAuth(`/api/articles/${articleId}`)
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
        const contentResponse = await fetchWithAuth(`/api/articles/${articleId}/content`)
        
        if (!contentResponse.ok) {
          if (contentResponse.status === 404) {
            setContent('## Article content is loading...')
            return
          }
          throw new Error('Failed to load article content')
        }

        const contentText = await contentResponse.text()
        setContent(contentText)
        
        // Load vocabularies for this article
        try {
          const vocabResponse = await fetchWithAuth(`/api/articles/${articleId}/vocabularies`)
          if (vocabResponse.ok) {
            const vocabData = await vocabResponse.json()
            console.log('[Vocab] Loaded vocabularies:', vocabData.map((v: Vocabulary) => ({ word: v.word, span_id: v.span_id })))
            setVocabularies(vocabData)
          }
        } catch (vocabErr) {
          console.error('Error fetching vocabularies:', vocabErr)
        }
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : 'Failed to load article'
        setError(message)
        console.error('Error fetching article:', err)
      } finally {
        setLoading(false)
      }
    }

    if (articleId) {
      fetchArticle()
    }
  }, [articleId])
  
  // Listen for vocabulary removal events
  useEffect(() => {
    const handleVocabularyRemoved = (event: CustomEvent) => {
      const vocabId = event.detail
      setVocabularies(prev => prev.filter(v => v.id !== vocabId))
    }
    
    window.addEventListener('vocabulary-removed', handleVocabularyRemoved as EventListener)
    return () => {
      window.removeEventListener('vocabulary-removed', handleVocabularyRemoved as EventListener)
    }
  }, [])
  
  // Handle vocabulary addition
  const handleAddVocabulary = (newVocab: Vocabulary) => {
    setVocabularies(prev => {
      // Check if already exists (avoid duplicates)
      if (prev.some(v => v.id === newVocab.id || v.lemma.toLowerCase() === newVocab.lemma.toLowerCase())) {
        return prev
      }
      return [...prev, newVocab]
    })
  }
  
  // Handle vocabulary deletion
  const handleDeleteVocabulary = async (vocabId: string) => {
    try {
      await deleteVocabulary(vocabId)
      setVocabularies(prev => prev.filter(v => v.id !== vocabId))
    } catch (error) {
      console.error('Failed to delete vocabulary:', error)
    }
  }

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
            /*
             * Key prop pattern forces component remount on content change.
             * Pattern: ${articleId}-${content.length}
             * - Prevents React hydration mismatches
             * - Resets data-processed attribute (MarkdownViewer.tsx:456)
             * - Clears stale event listeners
             * See: docs/ARCHITECTURE.md "React Component Remounting Pattern"
             */
            <MarkdownViewer
              key={`${articleId}-${content.length}`}
              content={content}
              language={article?.language}
              articleId={articleId}
              vocabularies={vocabularies}
              onAddVocabulary={handleAddVocabulary}
            />
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
        
        {/* Vocabulary List */}
        <VocabularyList 
          vocabularies={vocabularies}
          onDelete={handleDeleteVocabulary}
        />
      </div>
    </div>
  )
}
