import { useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { fetchWithAuth, parseErrorResponse } from '@/lib/api'

/**
 * Generic hook for async data fetching with loading/error/data state management.
 *
 * Provides:
 * - Automatic loading state management
 * - Error handling with message extraction
 * - Automatic 401 redirect to login page
 * - Type-safe data state
 *
 * @example
 * ```typescript
 * const { data, loading, error, fetch } = useAsyncFetch<Article[]>()
 *
 * useEffect(() => {
 *   fetch('/api/articles')
 * }, [fetch])
 * ```
 */
export function useAsyncFetch<T>() {
  const router = useRouter()
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = useCallback(
    async (url: string, options?: RequestInit) => {
      try {
        setLoading(true)
        setError(null)

        const response = await fetchWithAuth(url, options)

        // Handle 401 - redirect to login
        if (response.status === 401) {
          router.push('/login')
          return
        }

        // Handle error responses
        if (!response.ok) {
          const errorMsg = await parseErrorResponse(response, 'Failed to fetch data')
          throw new Error(errorMsg)
        }

        // Parse and set data
        const result: T = await response.json()
        setData(result)
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : 'An error occurred'
        setError(message)
        console.error('Fetch error:', err)
      } finally {
        setLoading(false)
      }
    },
    [router]
  )

  return {
    data,
    loading,
    error,
    fetch: fetchData,
    setData,
    setError
  }
}
