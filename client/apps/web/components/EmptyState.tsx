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
    <div className={`bg-card rounded-lg border border-border-card p-8 text-center ${className}`}>
      {icon && <div className="text-4xl mb-4">{icon}</div>}
      <p className="text-text-dim text-lg mb-4">{title}</p>
      <p className="text-text-dim">{description}</p>
      {action && (
        <button
          onClick={action.onClick}
          className="btn-primary mt-4"
        >
          {action.label}
        </button>
      )}
    </div>
  )
}
