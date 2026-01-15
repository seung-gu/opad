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
 * - pending: yellow/orange
 * - running: blue
 * - succeeded: green
 * - failed: red
 * - deleted: gray
 */
export default function ArticleStatusBadge({ status, className = '' }: ArticleStatusBadgeProps) {
  const statusConfig = {
    pending: {
      label: 'Pending',
      colorClass: 'bg-yellow-100 text-yellow-800 border-yellow-200'
    },
    running: {
      label: 'Running',
      colorClass: 'bg-blue-100 text-blue-800 border-blue-200'
    },
    succeeded: {
      label: 'Completed',
      colorClass: 'bg-green-100 text-green-800 border-green-200'
    },
    failed: {
      label: 'Failed',
      colorClass: 'bg-red-100 text-red-800 border-red-200'
    },
    deleted: {
      label: 'Deleted',
      colorClass: 'bg-gray-100 text-gray-800 border-gray-200'
    }
  }

  const config = statusConfig[status] || statusConfig.pending

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${config.colorClass} ${className}`}
    >
      {config.label}
    </span>
  )
}
