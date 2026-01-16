'use client'

import { useState, useEffect, useCallback } from 'react'
import { Article, ArticleListResponse, ArticleStatus } from '@/types/article'
import ArticleList from '@/components/ArticleList'
import ArticleFilter from '@/components/ArticleFilter'

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

      const response = await fetch(`/api/articles?${params.toString()}`)
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.error || 'Failed to load articles')
      }

      const data: ArticleListResponse = await response.json()
      setArticles(data.articles)
      setTotal(data.total)
    } catch (err: any) {
      setError(err.message || 'Failed to load articles')
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

  const currentPage = Math.floor(skip / limit) + 1
  const totalPages = Math.ceil(total / limit)
  const hasNextPage = skip + limit < total
  const hasPrevPage = skip > 0

  const handleNextPage = () => {
    if (hasNextPage) {
      setSkip(skip + limit)
    }
  }

  const handlePrevPage = () => {
    if (hasPrevPage) {
      setSkip(Math.max(0, skip - limit))
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Articles</h1>
          <p className="text-gray-600">
            {loading ? 'Loading...' : `${total} article${total !== 1 ? 's' : ''} found`}
          </p>
        </div>

        {/* Filter */}
        <div className="mb-6">
          <ArticleFilter
            selectedStatus={selectedStatus}
            onStatusChange={handleStatusChange}
          />
        </div>

        {/* Error State */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-800">{error}</p>
            <button
              onClick={fetchArticles}
              className="mt-2 text-sm text-red-600 hover:text-red-800 underline"
            >
              Try again
            </button>
          </div>
        )}

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
          <div className="mt-6 flex items-center justify-between border-t border-gray-200 pt-6">
            <div className="text-sm text-gray-700">
              Showing {skip + 1} to {skip + articles.length} of {total} articles
            </div>
            <div className="flex gap-2">
              <button
                onClick={handlePrevPage}
                disabled={!hasPrevPage || loading}
                className={`px-4 py-2 rounded-md text-sm font-medium ${
                  hasPrevPage && !loading
                    ? 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
                    : 'bg-gray-100 text-gray-400 cursor-not-allowed'
                }`}
              >
                Previous
              </button>
              <div className="px-4 py-2 text-sm text-gray-700">
                Page {currentPage} of {totalPages}
              </div>
              <button
                onClick={handleNextPage}
                disabled={!hasNextPage || loading}
                className={`px-4 py-2 rounded-md text-sm font-medium ${
                  hasNextPage && !loading
                    ? 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
                    : 'bg-gray-100 text-gray-400 cursor-not-allowed'
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
