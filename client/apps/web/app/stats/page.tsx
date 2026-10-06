'use client'

import { useState, useEffect } from 'react'
import { formatBytes, formatNumber } from '@opad/libs'
import SiteHeader from '@/components/SiteHeader'

interface DatabaseStats {
  collection: string
  total_documents: number
  active_documents: number
  deleted_documents: number
  data_size_mb: number
  index_size_mb: number
  storage_size_mb: number
  total_size_mb: number
  avg_document_size_bytes: number
  indexes: number
  index_details: Array<{
    name: string
    keys: Record<string, number>
  }>
}

export default function StatsPage() {
  const [stats, setStats] = useState<DatabaseStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchStats = async () => {
      try {
        setLoading(true)
        setError(null)
        const response = await fetch('/api/stats')
        
        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}))
          throw new Error(errorData.error || 'Failed to fetch statistics')
        }
        
        const data = await response.json()
        setStats(data)
      } catch (error_: unknown) {
        const message = error_ instanceof Error ? error_.message : 'Failed to load statistics'
        setError(message)
      } finally {
        setLoading(false)
      }
    }

    fetchStats()
  }, [])


  if (loading) {
    return (
      <div className="min-h-screen bg-background">
        <SiteHeader title="One story a day" />
        <main className="mx-auto max-w-4xl px-6 pt-12">
          <p className="text-[14px] text-text-dim">Loading statistics…</p>
        </main>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-background">
        <SiteHeader title="One story a day" />
        <main className="mx-auto max-w-4xl px-6 pt-12">
          <div className="border-l-2 border-accent-danger pl-4">
            <p className="text-[12px] font-medium text-accent-danger">Error</p>
            <p className="mt-0.5 text-[15px] text-foreground">{error}</p>
            <button onClick={() => globalThis.location.reload()} className="btn-outline mt-4">
              Retry
            </button>
          </div>
        </main>
      </div>
    )
  }

  if (!stats) {
    return null
  }

  const storage = [
    { label: 'Data', mb: stats.data_size_mb },
    { label: 'Index', mb: stats.index_size_mb },
    { label: 'Storage', mb: stats.storage_size_mb },
    { label: 'Total', mb: stats.total_size_mb },
  ]

  const counts = [
    { label: 'Total documents', value: stats.total_documents },
    { label: 'Active', value: stats.active_documents },
    { label: 'Deleted', value: stats.deleted_documents },
  ]

  return (
    <div className="min-h-screen bg-background">
      <SiteHeader title="One story a day" />

      <main className="mx-auto max-w-4xl px-6">
        <section className="pb-8 pt-12">
          <h1 className="font-serif text-[34px] leading-tight text-text-strong">Database</h1>
          <p className="mt-2 text-[14px] text-text-dim">
            MongoDB collection <span className="font-mono text-[13px]">{stats.collection}</span>
          </p>
        </section>

        <section className="border-t border-border-card pt-8">
          <div className="flex flex-wrap gap-x-16 gap-y-4">
            {counts.map((item) => (
              <div key={item.label}>
                <div className="font-serif text-[34px] leading-none tabular-nums text-text-strong">
                  {formatNumber(item.value)}
                </div>
                <div className="mt-2 text-[12px] text-text-dim">{item.label}</div>
              </div>
            ))}
          </div>
        </section>

        <section className="mt-12 border-t border-border-card pt-6">
          <h2 className="font-serif text-[19px] italic text-text-strong">Storage</h2>
          <ul className="mt-2">
            {storage.map((item) => (
              <li
                key={item.label}
                className="flex items-baseline justify-between gap-6 border-b border-border-card py-3 text-[14px] last:border-b-0"
              >
                <span className="text-foreground">{item.label}</span>
                <span className="flex items-baseline gap-6 text-text-dim">
                  <span className="tabular-nums">{item.mb.toFixed(2)} MB</span>
                  <span className="tabular-nums">{formatBytes(item.mb * 1024 * 1024)}</span>
                </span>
              </li>
            ))}
            <li className="flex items-baseline justify-between gap-6 border-b border-border-card py-3 text-[14px] last:border-b-0">
              <span className="text-foreground">Average document</span>
              <span className="tabular-nums text-text-dim">{formatBytes(stats.avg_document_size_bytes)}</span>
            </li>
          </ul>
        </section>

        <section className="mt-12 border-t border-border-card pt-6">
          <div className="flex items-baseline justify-between">
            <h2 className="font-serif text-[19px] italic text-text-strong">Indexes</h2>
            <span className="text-[12px] text-text-dim">{stats.indexes}</span>
          </div>
          <ul className="mt-2">
            {stats.index_details.map((index) => (
              <li
                key={index.name}
                className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1 border-b border-border-card py-3 last:border-b-0"
              >
                <span className="text-[14px] text-foreground">{index.name}</span>
                <span className="font-mono text-[12px] text-text-dim">
                  {Object.entries(index.keys)
                    .map(([key, value]) => `${key} ${value > 0 ? 'asc' : 'desc'}`)
                    .join(', ')}
                </span>
              </li>
            ))}
          </ul>
        </section>

        <div className="mt-10">
          <button onClick={() => globalThis.location.reload()} className="btn-outline">
            Refresh
          </button>
        </div>

        <footer className="mt-14 border-t border-border-card py-6 text-[12px] text-text-dim">
          One story a day
        </footer>
      </main>
    </div>
  )
}
