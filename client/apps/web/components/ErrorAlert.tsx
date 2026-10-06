/**
 * Error message, marked with an accent rule rather than a filled panel.
 */

interface ErrorAlertProps {
  error: string | null
  onRetry?: () => void
  className?: string
}

export default function ErrorAlert({ error, onRetry, className = '' }: ErrorAlertProps) {
  if (!error) return null

  return (
    <div className={`mb-6 border-l-2 border-accent-danger pl-4 ${className}`}>
      <p className="text-[12px] font-medium text-accent-danger">Error</p>
      <p className="mt-0.5 text-[14px] text-foreground">{error}</p>
      {onRetry && (
        <button onClick={onRetry} className="mt-1 text-[13px] text-accent hover:opacity-80">
          Try again
        </button>
      )}
    </div>
  )
}
