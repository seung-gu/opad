/**
 * Reusable error alert component for displaying error messages.
 *
 * Features:
 * - Consistent error styling (red background with border)
 * - Optional retry button
 * - Automatic hiding when error is null
 */

interface ErrorAlertProps {
  error: string | null
  onRetry?: () => void
  className?: string
}

export default function ErrorAlert({ error, onRetry, className = '' }: ErrorAlertProps) {
  if (!error) return null

  return (
    <div className={`mb-6 p-4 bg-accent-danger/20 border border-accent-danger/50 rounded-lg ${className}`}>
      <p className="text-accent-danger">{error}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-2 text-sm text-accent-danger hover:text-accent-danger/80 underline"
        >
          Try again
        </button>
      )}
    </div>
  )
}
