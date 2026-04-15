'use client'

import { useState, useEffect, useCallback } from 'react'
import Link from 'next/link'
import { Article, ArticleListResponse, ArticleStatus } from '@/types/article'
import ArticleList from '@/components/ArticleList'
import ArticleFilter from '@/components/ArticleFilter'
import { fetchWithAuth, parseErrorResponse } from '@/lib/api'
import ErrorAlert from '@/components/ErrorAlert'
import { usePagination } from '@/hooks/usePagination'

/**
 * Article list page.
 * 
 * Features:
 * - Display list of articles with metadata
 * - Filter by status
 * - Sort by latest first (handled by backend)
 * - Link to individual article pages
 * - Handle loading and processing states
 */
function formatArticleCount(total: number): string {
  return `${total} article${total === 1 ? '' : 's'} found`
}

export default function ArticlesPage() {
  const [articles, setArticles] = useState<Article[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [total, setTotal] = useState(0)
  const [selectedStatus, setSelectedStatus] = useState<ArticleStatus | undefined>()
  const [skip, setSkip] = useState(0)
  const limit = 10 // Articles per page

  const fetchArticles = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const params = new URLSearchParams()
      if (selectedStatus) {
        params.set('status', selectedStatus)
      }
      params.set('skip', skip.toString())
      params.set('limit', limit.toString())

      const response = await fetchWithAuth(`/api/articles?${params.toString()}`)

      if (!response.ok) {
        const errorMsg = await parseErrorResponse(response, 'Failed to load articles')
        throw new Error(errorMsg)
      }

      const data: ArticleListResponse = await response.json()
      setArticles(data.articles)
      setTotal(data.total)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to load articles'
      setError(message)
      console.error('Error fetching articles:', err)
    } finally {
      setLoading(false)
    }
  }, [selectedStatus, skip, limit])

  useEffect(() => {
    setSkip(0) // Reset to first page when filter changes
  }, [selectedStatus])

  useEffect(() => {
    fetchArticles()
  }, [fetchArticles])

  const handleStatusChange = (status: ArticleStatus | undefined) => {
    setSelectedStatus(status)
  }

  const { currentPage, totalPages, hasNextPage, hasPrevPage, nextSkip, prevSkip } = usePagination({
    total,
    limit,
    skip
  })

  const handleNextPage = () => {
    if (hasNextPage) {
      setSkip(nextSkip)
    }
  }

  const handlePrevPage = () => {
    if (hasPrevPage) {
      setSkip(prevSkip)
    }
  }

  return (
    <div className="min-h-screen bg-background py-8">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <h1 className="text-3xl font-bold font-mono text-accent">Articles</h1>
            <Link
              href="/"
              className="text-xl font-medium text-foreground hover:text-foreground/80 transition-colors"
              title="Go to Home"
            >
              <span className="text-[0.9rem]">◀</span> Home
            </Link>
          </div>
          <p className="text-text-dim">
            {loading ? 'Loading...' : formatArticleCount(total)}
          </p>
        </div>

        {/* Filter */}
        <div className="mb-6 flex items-center justify-between">
          <ArticleFilter
            selectedStatus={selectedStatus}
            onStatusChange={handleStatusChange}
          />
          <div className="flex items-center gap-2">
            <Link href="/usage" className="btn-outline">
              Usage
            </Link>
            <Link href="/vocabulary" className="btn-outline btn-vocab">
              Vocabulary
            </Link>
          </div>
        </div>

        {/* Error State */}
        <ErrorAlert error={error} onRetry={fetchArticles} />

        {/* Article List */}
        <ArticleList
          articles={articles}
          loading={loading}
          emptyMessage={
            selectedStatus
              ? `No articles with status "${selectedStatus}" found`
              : 'No articles found. Generate your first article to get started!'
          }
        />

        {/* Pagination */}
        {total > 0 && (
          <div className="mt-6 flex items-center justify-between border-t border-border-card pt-6">
            <div className="text-sm text-foreground">
              Showing {skip + 1} to {skip + articles.length} of {total} articles
            </div>
            <div className="flex gap-2">
              <button
                onClick={handlePrevPage}
                disabled={!hasPrevPage || loading}
                className={`px-4 py-2 rounded-md text-sm font-medium ${
                  hasPrevPage && !loading
                    ? 'bg-card text-foreground border border-border-card hover:bg-card-hover'
                    : 'bg-card-hover text-text-dim cursor-not-allowed'
                }`}
              >
                Previous
              </button>
              <div className="px-4 py-2 text-sm text-foreground">
                Page {currentPage} of {totalPages}
              </div>
              <button
                onClick={handleNextPage}
                disabled={!hasNextPage || loading}
                className={`px-4 py-2 rounded-md text-sm font-medium ${
                  hasNextPage && !loading
                    ? 'bg-card text-foreground border border-border-card hover:bg-card-hover'
                    : 'bg-card-hover text-text-dim cursor-not-allowed'
                }`}
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
