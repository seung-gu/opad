'use client'

import Link from 'next/link'
import { Article } from '@/types/article'
import ArticleStatusBadge from './ArticleStatusBadge'

interface ArticleCardProps {
  article: Article
}

/**
 * Reusable card component for displaying a single article in a list.
 * 
 * Displays:
 * - Topic (as title/link)
 * - Status badge
 * - Metadata (language, level, length)
 * - Created time
 * - Link to article detail page
 */
export default function ArticleCard({ article }: ArticleCardProps) {
  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString)
      return new Intl.DateTimeFormat('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      }).format(date)
    } catch {
      return dateString
    }
  }

  return (
    <Link
      href={`/articles/${article.id}`}
      className="block p-4 bg-white border border-gray-200 rounded-lg hover:border-blue-300 hover:shadow-md transition-all duration-200"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <h3 className="text-lg font-semibold text-gray-900 mb-2 truncate">
            {article.topic || 'Untitled Article'}
          </h3>
          
          <div className="flex flex-wrap items-center gap-3 text-sm text-gray-600 mb-3">
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

        <div className="flex-shrink-0">
          <ArticleStatusBadge status={article.status} />
        </div>
      </div>
    </Link>
  )
}
