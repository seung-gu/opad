'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { TokenUsageSummary } from '@opad/libs'
import { fetchWithAuth, parseErrorResponse } from '@/lib/api'
import { useAuth } from '@/contexts/AuthContext'
import ErrorAlert from '@/components/ErrorAlert'
import EmptyState from '@/components/EmptyState'
import SiteHeader from '@/components/SiteHeader'
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
    <div className="min-h-screen bg-background">
      <SiteHeader title="One story a day" />

      <main className="mx-auto max-w-5xl px-6">
        <section className="pb-8 pt-12">
          <h1 className="font-serif text-[34px] leading-tight text-text-strong">Token usage</h1>
          <p className="mt-2 text-[14px] text-text-dim">What your reading has cost so far</p>
        </section>

        <div className="flex flex-wrap items-baseline gap-x-5 gap-y-3 border-t border-border-card py-4">
          <label htmlFor="days-select" className="text-[12px] text-text-dim">
            Period
          </label>
          <div className="flex flex-wrap items-baseline" id="days-select">
            {[7, 30, 90, 365].map((option) => (
              <button
                key={option}
                type="button"
                disabled={loading}
                aria-pressed={days === option}
                onClick={() => handleDaysChange(option)}
                className={`border-b-2 px-1.5 pb-0.5 text-[13px] tabular-nums transition-colors disabled:opacity-40 ${
                  days === option
                    ? 'border-accent font-medium text-foreground'
                    : 'border-transparent text-text-dim hover:text-foreground'
                }`}
              >
                {option} days
              </button>
            ))}
          </div>
        </div>

        <ErrorAlert error={error} onRetry={createFetchWithAbort} />

        {loading && !hasData && (
          <p className="border-t border-border-card py-10 text-[14px] text-text-dim">Loading usage data…</p>
        )}

        {!loading && !error && !hasData && (
          <EmptyState
            title="Nothing to report yet."
            description="Generate an article or look up a word, and the token cost will show up here."
            action={{
              label: 'Go to articles',
              onClick: () => router.push('/articles'),
            }}
          />
        )}

        {!error && hasData && summary && (
          <div className={`border-t border-border-card pt-8 ${loading ? 'opacity-50' : ''}`}>
            <UsageSummary summary={summary} days={days} />
          </div>
        )}

        {hasData && (
          <div className="mt-10">
            <button onClick={createFetchWithAbort} disabled={loading} className="btn-outline">
              {loading ? 'Refreshing…' : 'Refresh'}
            </button>
          </div>
        )}

        <footer className="mt-14 border-t border-border-card py-6 text-[12px] text-text-dim">
          One story a day
        </footer>
      </main>
    </div>
  )
}
