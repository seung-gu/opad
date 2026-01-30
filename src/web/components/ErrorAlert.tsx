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
    <div className={`mb-6 p-4 bg-red-50 border border-red-200 rounded-lg ${className}`}>
      <p className="text-red-800">{error}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-2 text-sm text-red-600 hover:text-red-800 underline"
        >
          Try again
        </button>
      )}
    </div>
  )
}
