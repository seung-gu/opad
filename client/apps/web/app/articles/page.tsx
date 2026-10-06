'use client'

import { useState, useEffect, useCallback } from 'react'
import Link from 'next/link'
import { Article, ArticleListResponse, ArticleStatus, formatArticleCount } from '@opad/libs'
import ArticleList from '@/components/ArticleList'
import SiteHeader from '@/components/SiteHeader'
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
    <div className="min-h-screen bg-background">
      <SiteHeader title="One story a day" />

      <main className="mx-auto max-w-3xl px-6">
        <section className="pb-8 pt-12">
          <h1 className="font-serif text-[34px] leading-tight text-text-strong">Articles</h1>
          <p className="mt-2 text-[14px] text-text-dim">{loading ? 'Loading…' : formatArticleCount(total)}</p>
        </section>

        <div className="flex flex-wrap items-baseline justify-between gap-4 border-t border-border-card py-4">
          <ArticleFilter selectedStatus={selectedStatus} onStatusChange={handleStatusChange} />
          <Link href="/" className="text-[13px] text-text-dim transition-colors hover:text-accent">
            New article
          </Link>
        </div>

        <ErrorAlert error={error} onRetry={fetchArticles} />

        <div className="border-t border-border-card">
          <ArticleList
            articles={articles}
            loading={loading}
            emptyMessage={
              selectedStatus
                ? `No articles with status "${selectedStatus}".`
                : 'No articles yet. Generate your first one from the home page.'
            }
          />
        </div>

        {total > 0 && (
          <div className="mt-6 flex flex-wrap items-baseline justify-between gap-4 border-t border-border-card pt-6">
            <div className="text-[13px] text-text-dim">
              Showing {skip + 1}&ndash;{skip + articles.length} of {total}
            </div>
            <div className="flex items-baseline gap-5 text-[13px]">
              <button
                onClick={handlePrevPage}
                disabled={!hasPrevPage || loading}
                className="text-accent transition-opacity hover:opacity-80 disabled:text-text-dim disabled:opacity-40"
              >
                Previous
              </button>
              <span className="text-text-dim tabular-nums">
                Page {currentPage} of {totalPages}
              </span>
              <button
                onClick={handleNextPage}
                disabled={!hasNextPage || loading}
                className="text-accent transition-opacity hover:opacity-80 disabled:text-text-dim disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>
        )}

        <footer className="mt-14 border-t border-border-card py-6 text-[12px] text-text-dim">
          One story a day
        </footer>
      </main>
    </div>
  )
}
