'use client'

import { ArticleStatus } from '@/types/article'

interface ArticleStatusBadgeProps {
  status: ArticleStatus
  className?: string
}

/**
 * Reusable badge component for displaying article status.
 *
 * Provides consistent styling and color coding for different statuses:
 * - running: blue (accent)
 * - completed: purple (system)
 * - failed: red (danger)
 * - deleted: gray (text-dim)
 */
export default function ArticleStatusBadge({ status, className = '' }: ArticleStatusBadgeProps) {
  const statusConfig = {
    running: {
      label: 'Running',
      colorClass: 'bg-accent/20 text-accent border-accent/30'
    },
    completed: {
      label: 'Completed',
      colorClass: 'bg-system/20 text-system border-system/30'
    },
    failed: {
      label: 'Failed',
      colorClass: 'bg-accent-danger/20 text-accent-danger border-accent-danger/30'
    },
    deleted: {
      label: 'Deleted',
      colorClass: 'bg-text-dim/20 text-text-dim border-text-dim/30'
    }
  }

  const config = statusConfig[status] || statusConfig.running

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${config.colorClass} ${className}`}
    >
      {config.label}
    </span>
  )
}
