'use client'

import { Article } from '@/types/article'
import ArticleCard from './ArticleCard'

interface ArticleListProps {
  articles: Article[]
  loading?: boolean
  emptyMessage?: string
}

/**
 * Reusable list component for displaying multiple articles.
 * 
 * Handles:
 * - Empty state
 * - Loading state (via parent)
 * - Rendering article cards
 */
export default function ArticleList({ 
  articles, 
  loading = false,
  emptyMessage = 'No articles found'
}: ArticleListProps) {
  if (loading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="p-4 bg-card border border-border-card rounded-lg animate-pulse"
          >
            <div className="h-6 bg-card-hover rounded w-3/4 mb-3"></div>
            <div className="h-4 bg-card-hover rounded w-1/2"></div>
          </div>
        ))}
      </div>
    )
  }

  if (articles.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-text-dim text-lg">{emptyMessage}</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {articles.map((article) => (
        <ArticleCard key={article.id} article={article} />
      ))}
    </div>
  )
}
