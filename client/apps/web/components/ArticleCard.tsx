'use client'

import Link from 'next/link'
import { Article } from '@opad/libs'
import ArticleStatusBadge from './ArticleStatusBadge'
import { formatDateTime } from '@opad/libs'

interface ArticleCardProps {
  article: Article
}

/**
 * A single article as an editorial list row: serif headline on the left,
 * metadata on the right, separated from its neighbours by a hairline.
 */
export default function ArticleCard({ article }: ArticleCardProps) {
  return (
    <Link
      href={`/articles/${article.id}`}
      className="group flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1 py-4"
    >
      <span className="font-serif text-[19px] leading-snug text-text-strong transition-colors group-hover:text-accent">
        {article.topic || 'Untitled Article'}
      </span>

      <span className="flex shrink-0 items-baseline gap-3 text-[12px] text-text-dim">
        <span>
          {article.language} · {article.level} · {article.length} words · {formatDateTime(article.created_at)}
        </span>
        {article.status !== 'completed' && <ArticleStatusBadge status={article.status} />}
      </span>
    </Link>
  )
}
