/**
 * Empty state: a short serif line, an explanation, and an optional action.
 */

interface EmptyStateProps {
  title: string
  description: string
  action?: {
    label: string
    onClick: () => void
  }
  className?: string
}

export default function EmptyState({ title, description, action, className = '' }: EmptyStateProps) {
  return (
    <div className={`border-t border-border-card py-10 ${className}`}>
      <p className="font-serif text-[19px] italic text-text-strong">{title}</p>
      <p className="mt-2 max-w-xl text-[14px] leading-relaxed text-text-dim">{description}</p>
      {action && (
        <button onClick={action.onClick} className="btn-outline mt-5">
          {action.label}
        </button>
      )}
    </div>
  )
}
