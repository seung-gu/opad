'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { TokenUsageSummary } from '@/types/usage'
import { fetchWithAuth, parseErrorResponse } from '@/lib/api'
import { useAuth } from '@/contexts/AuthContext'
import ErrorAlert from '@/components/ErrorAlert'
import EmptyState from '@/components/EmptyState'
import UsageSummary from '@/components/UsageSummary'

/**
 * Token usage dashboard page.
 *
 * Features:
 * - Display token usage summary with totals
 * - Breakdown by operation type
 * - Daily usage chart
 * - Configurable time period (7, 30, 90, 365 days)
 * - Requires authentication
 */
export default function UsagePage() {
  const router = useRouter()
  const { isAuthenticated } = useAuth()
  const [summary, setSummary] = useState<TokenUsageSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [days, setDays] = useState(30)
  const abortControllerRef = useRef<AbortController | null>(null)

  const fetchUsage = useCallback(async (signal?: AbortSignal) => {
    try {
      setLoading(true)
      setError(null)

      const response = await fetchWithAuth(`/api/usage/me?days=${days}`, { signal })

      if (!response.ok) {
        if (response.status === 401) {
          router.push('/login')
          return
        }
        const errorMsg = await parseErrorResponse(response, 'Failed to load usage data')
        throw new Error(errorMsg)
      }

      const data: TokenUsageSummary = await response.json()
      setSummary(data)
    } catch (err: unknown) {
      // Ignore aborted requests
      if (err instanceof Error && err.name === 'AbortError') {
        return
      }
      const message = err instanceof Error ? err.message : 'Failed to load usage data'
      setError(message)
      console.error('Error fetching usage:', err)
    } finally {
      setLoading(false)
    }
  }, [router, days])

  const createFetchWithAbort = useCallback(() => {
    // Cancel any in-flight request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }

    // Create new controller
    const controller = new AbortController()
    abortControllerRef.current = controller

    fetchUsage(controller.signal)
  }, [fetchUsage])

  useEffect(() => {
    // Redirect to login if not authenticated
    if (!isAuthenticated) {
      router.push('/login')
      return
    }

    createFetchWithAbort()

    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
      }
    }
  }, [isAuthenticated, router, createFetchWithAbort])

  const handleDaysChange = (newDays: number) => {
    setDays(newDays)
  }

  // Check if summary has any data
  const hasData = summary && (summary.total_tokens > 0 || summary.daily_usage.length > 0)

  return (
    <div className="min-h-screen bg-background py-8">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <h1 className="text-3xl font-bold font-mono text-accent">Token Usage</h1>
            <Link
              href="/articles"
              className="text-xl font-medium text-foreground hover:text-foreground transition-colors"
              title="Go to Articles"
            >
              <span className="text-[0.9rem]">◀</span> Articles
            </Link>
          </div>
          <p className="text-text-dim">
            Track your API token consumption and costs
          </p>
        </div>

        {/* Days Selector */}
        <div className="mb-6 flex items-center gap-4">
          <label htmlFor="days-select" className="text-sm font-medium text-foreground">
            Time Period:
          </label>
          <select
            id="days-select"
            value={days}
            onChange={(e) => handleDaysChange(Number(e.target.value))}
            className="px-4 py-2 border border-border-card rounded-lg bg-card text-foreground focus:ring-2 focus:ring-accent focus:border-accent"
            disabled={loading}
          >
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
            <option value={365}>Last 365 days</option>
          </select>
        </div>

        {/* Error State */}
        <ErrorAlert error={error} onRetry={createFetchWithAbort} />

        {/* Loading State - only show full loader when no data exists */}
        {loading && !hasData && (
          <div className="bg-card rounded-lg shadow-lg p-8">
            <div className="flex items-center justify-center">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-accent"></div>
              <p className="ml-4 text-lg text-text-dim">Loading usage data...</p>
            </div>
          </div>
        )}

        {/* Empty State */}
        {!loading && !error && !hasData && (
          <EmptyState
            title="No usage data found."
            description="Start using the dictionary search or article generation features to track your token usage."
            action={{
              label: 'Go to Articles',
              onClick: () => router.push('/articles')
            }}
          />
        )}

        {/* Usage Summary */}
        {!error && hasData && summary && (
          <div className={`bg-card rounded-lg shadow-lg overflow-hidden transition-opacity hover:border-accent/50 transition-colors ${loading ? 'opacity-50' : ''}`}>
            {/* Header */}
            <div className="bg-gradient-to-r from-accent to-accent/80 p-6">
              <h2 className="text-sm font-semibold font-mono text-white tracking-wide uppercase">Token Usage Summary</h2>
              <p className="text-white/80">Last {days} days</p>
            </div>

            {/* Content */}
            <div className="p-6">
              <UsageSummary summary={summary} days={days} />
            </div>
          </div>
        )}

        {/* Refresh Button */}
        {hasData && (
          <div className="mt-6 text-center">
            <button
              onClick={createFetchWithAbort}
              disabled={loading}
              className="btn-outline"
            >
              {loading ? 'Refreshing...' : 'Refresh Data'}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
