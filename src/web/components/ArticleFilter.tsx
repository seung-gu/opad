'use client'

import { ArticleStatus } from '@/types/article'

interface ArticleFilterProps {
  selectedStatus?: ArticleStatus
  onStatusChange: (status: ArticleStatus | undefined) => void
}

const STATUS_OPTIONS: { value: ArticleStatus | ''; label: string }[] = [
  { value: '', label: 'All Statuses' },
  { value: 'pending', label: 'Pending' },
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
      <label htmlFor="status-filter" className="text-sm font-medium text-gray-700">
        Filter by status:
      </label>
      <select
        id="status-filter"
        value={selectedStatus || ''}
        onChange={handleChange}
        className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
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
