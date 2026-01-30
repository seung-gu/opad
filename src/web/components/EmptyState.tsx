/**
 * Reusable empty state component for displaying when no data is available.
 *
 * Features:
 * - Consistent empty state styling
 * - Optional action button
 * - Centered layout with icon
 */

interface EmptyStateProps {
  title: string
  description: string
  icon?: string
  action?: {
    label: string
    onClick: () => void
  }
  className?: string
}

export default function EmptyState({
  title,
  description,
  icon,
  action,
  className = ''
}: EmptyStateProps) {
  return (
    <div className={`bg-white rounded-lg shadow-lg p-8 text-center ${className}`}>
      {icon && <div className="text-4xl mb-4">{icon}</div>}
      <p className="text-gray-500 text-lg mb-4">{title}</p>
      <p className="text-gray-400">{description}</p>
      {action && (
        <button
          onClick={action.onClick}
          className="inline-block mt-4 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          {action.label}
        </button>
      )}
    </div>
  )
}
