'use client'

import { ArticleStatus } from '@opad/libs'

interface ArticleStatusBadgeProps {
  status: ArticleStatus
  className?: string
}

/**
 * Status label for an article.
 *
 * Rendered as plain coloured text rather than a pill, so it sits inside a
 * metadata line without interrupting it.
 */
export default function ArticleStatusBadge({ status, className = '' }: ArticleStatusBadgeProps) {
  const statusConfig = {
    running: { label: 'Running', colorClass: 'text-accent' },
    completed: { label: 'Completed', colorClass: 'text-good' },
    failed: { label: 'Failed', colorClass: 'text-accent-danger' },
    deleted: { label: 'Deleted', colorClass: 'text-text-dim' },
  }

  const config = statusConfig[status] || statusConfig.running

  return <span className={`text-[12px] font-medium ${config.colorClass} ${className}`}>{config.label}</span>
}
