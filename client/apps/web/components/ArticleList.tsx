'use client'

import { Article } from '@opad/libs'
import ArticleCard from './ArticleCard'

interface ArticleListProps {
  articles: Article[]
  loading?: boolean
  emptyMessage?: string
}

/**
 * Article list: hairline-separated rows, with a matching skeleton while loading.
 */
export default function ArticleList({
  articles,
  loading = false,
  emptyMessage = 'No articles found',
}: ArticleListProps) {
  if (loading) {
    return (
      <ul>
        {[1, 2, 3].map((i) => (
          <li key={i} className="border-b border-border-card py-5 last:border-b-0">
            <div className="h-5 w-3/5 animate-pulse bg-card-hover" />
          </li>
        ))}
      </ul>
    )
  }

  if (articles.length === 0) {
    return <p className="py-10 text-[14px] text-text-dim">{emptyMessage}</p>
  }

  return (
    <ul>
      {articles.map((article) => (
        <li key={article.id} className="border-b border-border-card last:border-b-0">
          <ArticleCard article={article} />
        </li>
      ))}
    </ul>
  )
}
