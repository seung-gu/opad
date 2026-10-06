'use client'

import { ArticleStatus } from '@opad/libs'

interface ArticleFilterProps {
  selectedStatus?: ArticleStatus
  onStatusChange: (status: ArticleStatus | undefined) => void
}

const STATUS_OPTIONS: { value: ArticleStatus | undefined; label: string }[] = [
  { value: undefined, label: 'All' },
  { value: 'running', label: 'Running' },
  { value: 'completed', label: 'Completed' },
  { value: 'failed', label: 'Failed' },
]

/**
 * Status filter, as an underlined segmented control.
 */
export default function ArticleFilter({ selectedStatus, onStatusChange }: ArticleFilterProps) {
  return (
    <div className="flex items-baseline gap-2">
      <span className="text-[12px] text-text-dim">Status</span>
      <div className="flex flex-wrap items-baseline">
        {STATUS_OPTIONS.map((option) => (
          <button
            key={option.label}
            type="button"
            aria-pressed={selectedStatus === option.value}
            onClick={() => onStatusChange(option.value)}
            className={`border-b-2 px-1.5 pb-0.5 text-[13px] transition-colors ${
              selectedStatus === option.value
                ? 'border-accent font-medium text-foreground'
                : 'border-transparent text-text-dim hover:text-foreground'
            }`}
          >
            {option.label}
          </button>
        ))}
      </div>
    </div>
  )
}
