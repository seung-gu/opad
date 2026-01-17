'use client'

import { useState, useEffect } from 'react'
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

        {/* Content */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          {content ? (
            <MarkdownViewer content={content} />
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
