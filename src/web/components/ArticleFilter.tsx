'use client'

import { ArticleStatus } from '@/types/article'

interface ArticleFilterProps {
  selectedStatus?: ArticleStatus
  onStatusChange: (status: ArticleStatus | undefined) => void
}

const STATUS_OPTIONS: { value: ArticleStatus | ''; label: string }[] = [
  { value: '', label: 'All' },
  { value: 'running', label: 'Running' },
  { value: 'completed', label: 'Completed' },
  { value: 'failed', label: 'Failed' }
]

/**
 * Reusable filter component for article list.
 * 
 * Provides status filtering dropdown.
 */
export default function ArticleFilter({ selectedStatus, onStatusChange }: ArticleFilterProps) {
  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value
    onStatusChange(value === '' ? undefined : (value as ArticleStatus))
  }

  return (
    <div className="flex items-center gap-2">
      <label htmlFor="status-filter" className="text-sm font-medium text-foreground">
        Filter by status:
      </label>
      <select
        id="status-filter"
        value={selectedStatus || ''}
        onChange={handleChange}
        className="px-3 py-2 bg-card border border-border-card rounded-md text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-accent focus:border-accent"
      >
        {STATUS_OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  )
}
