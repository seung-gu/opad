import { useState, useEffect, useRef, useCallback, MutableRefObject } from 'react'
import { fetchWithAuth } from '@/lib/api'

/**
 * Hook for polling job status with automatic interval management.
 *
 * Provides:
 * - Automatic polling at 5-second intervals
 * - Progress state management
 * - Automatic cleanup on completion/error
 * - Callbacks for status changes
 *
 * @example
 * ```typescript
 * const { progress, isPolling } = useStatusPolling({
 *   jobId: currentJobId,
 *   enabled: article?.status === 'running',
 *   onComplete: () => {
 *     // Reload data
 *     fetchArticle()
 *   },
 *   onError: () => {
 *     // Handle error
 *     console.error('Job failed')
 *   }
 * })
 * ```
 */

interface ProgressState {
  current_task: string
  progress: number
  message: string
  error: string | null
}

interface UseStatusPollingProps {
  /** Job ID to poll for status */
  jobId: string | null
  /** Whether polling is enabled (e.g., only poll when status is 'running') */
  enabled: boolean
  /** Callback when job completes successfully */
  onComplete?: () => void
  /** Callback when job fails */
  onError?: () => void
  /** Polling interval in milliseconds (default: 5000) */
  interval?: number
}

interface UseStatusPollingResult {
  progress: ProgressState
  isPolling: boolean
}

export function useStatusPolling({
  jobId,
  enabled,
  onComplete,
  onError,
  interval = 5000
}: UseStatusPollingProps): UseStatusPollingResult {
  const [progress, setProgress] = useState<ProgressState>({
    current_task: '',
    progress: 0,
    message: '',
    error: null
  })
  const [isPolling, setIsPolling] = useState(false)
  const intervalRef = useRef<NodeJS.Timeout | null>(null)

  // Use refs for callbacks to prevent stale closures
  const onCompleteRef = useRef(onComplete)
  const onErrorRef = useRef(onError)

  useEffect(() => {
    onCompleteRef.current = onComplete
    onErrorRef.current = onError
  }, [onComplete, onError])

  const loadStatus = useCallback(async () => {
    if (!jobId) return

    try {
      const response = await fetchWithAuth(`/api/status?job_id=${jobId}`)
      const data = await response.json()

      // Update progress state only if changed
      setProgress(prev => {
        const newProgress: ProgressState = {
          current_task: data.current_task || '',
          progress: data.progress || 0,
          message: data.message || '',
          error: data.error || null
        }

        // Check if anything changed
        if (
          prev.current_task !== newProgress.current_task ||
          prev.progress !== newProgress.progress ||
          prev.message !== newProgress.message ||
          prev.error !== newProgress.error
        ) {
          return newProgress
        }
        return prev
      })

      // Handle completion
      if (data.status === 'completed') {
        setIsPolling(false)
        if (intervalRef.current) {
          clearInterval(intervalRef.current)
          intervalRef.current = null
        }
        onCompleteRef.current?.()
      }
      // Handle error
      else if (data.status === 'error') {
        setIsPolling(false)
        if (intervalRef.current) {
          clearInterval(intervalRef.current)
          intervalRef.current = null
        }
        onErrorRef.current?.()
      }
    } catch (err) {
      console.error('Failed to fetch status:', err)
    }
  }, [jobId])

  useEffect(() => {
    // Clear interval if polling is disabled
    if (!enabled || !jobId) {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
        setIsPolling(false)
      }
      return
    }

    // Start polling
    setIsPolling(true)
    loadStatus() // Load immediately

    // Set up polling interval
    const pollInterval = setInterval(loadStatus, interval)
    intervalRef.current = pollInterval

    // Cleanup on unmount or when dependencies change
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }
  }, [enabled, jobId, interval, loadStatus])

  return {
    progress,
    isPolling
  }
}
