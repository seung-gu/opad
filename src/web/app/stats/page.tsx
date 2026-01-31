'use client'

import { useState, useEffect } from 'react'

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

  const formatBytes = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
  }

  const formatNumber = (num: number) => {
    return num.toLocaleString()
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <div className="max-w-4xl mx-auto">
          <div className="bg-white rounded-lg shadow p-8">
            <div className="text-center">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <p className="mt-4 text-gray-600">Loading statistics...</p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <div className="max-w-4xl mx-auto">
          <div className="bg-white rounded-lg shadow p-8">
            <div className="text-center">
              <div className="text-red-600 text-xl mb-4">⚠️ Error</div>
              <p className="text-gray-700">{error}</p>
              <button
                onClick={() => globalThis.location.reload()}
                className="mt-6 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                Retry
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (!stats) {
    return null
  }

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Database Statistics</h1>
          <p className="text-gray-600">MongoDB collection statistics and storage information</p>
        </div>

        <div className="bg-white rounded-lg shadow-lg overflow-hidden">
          {/* Collection Overview */}
          <div className="bg-gradient-to-r from-blue-600 to-blue-700 text-white p-6">
            <h2 className="text-2xl font-semibold mb-2">{stats.collection}</h2>
            <p className="text-blue-100">Collection Overview</p>
          </div>

          <div className="p-6">
            {/* Document Counts */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
              <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
                <div className="text-sm text-blue-600 font-medium mb-1">Total Documents</div>
                <div className="text-3xl font-bold text-blue-900">{formatNumber(stats.total_documents)}</div>
              </div>
              <div className="bg-green-50 rounded-lg p-4 border border-green-200">
                <div className="text-sm text-green-600 font-medium mb-1">Active Documents</div>
                <div className="text-3xl font-bold text-green-900">{formatNumber(stats.active_documents)}</div>
              </div>
              <div className="bg-red-50 rounded-lg p-4 border border-red-200">
                <div className="text-sm text-red-600 font-medium mb-1">Deleted Documents</div>
                <div className="text-3xl font-bold text-red-900">{formatNumber(stats.deleted_documents)}</div>
              </div>
            </div>

            {/* Storage Information */}
            <div className="mb-8">
              <h3 className="text-xl font-semibold text-gray-900 mb-4">Storage Information</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                  <div className="text-sm text-gray-600 font-medium mb-1">Data Size</div>
                  <div className="text-2xl font-bold text-gray-900">
                    {stats.data_size_mb.toFixed(2)} MB
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    {formatBytes(stats.data_size_mb * 1024 * 1024)}
                  </div>
                </div>
                <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                  <div className="text-sm text-gray-600 font-medium mb-1">Index Size</div>
                  <div className="text-2xl font-bold text-gray-900">
                    {stats.index_size_mb.toFixed(2)} MB
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    {formatBytes(stats.index_size_mb * 1024 * 1024)}
                  </div>
                </div>
                <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                  <div className="text-sm text-gray-600 font-medium mb-1">Storage Size</div>
                  <div className="text-2xl font-bold text-gray-900">
                    {stats.storage_size_mb.toFixed(2)} MB
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    {formatBytes(stats.storage_size_mb * 1024 * 1024)}
                  </div>
                </div>
                <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                  <div className="text-sm text-gray-600 font-medium mb-1">Total Size</div>
                  <div className="text-2xl font-bold text-gray-900">
                    {stats.total_size_mb.toFixed(2)} MB
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    {formatBytes(stats.total_size_mb * 1024 * 1024)}
                  </div>
                </div>
              </div>
            </div>

            {/* Document Statistics */}
            <div className="mb-8">
              <h3 className="text-xl font-semibold text-gray-900 mb-4">Document Statistics</h3>
              <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                <div className="text-sm text-gray-600 font-medium mb-1">Average Document Size</div>
                <div className="text-2xl font-bold text-gray-900">
                  {formatBytes(stats.avg_document_size_bytes)}
                </div>
              </div>
            </div>

            {/* Index Information */}
            <div>
              <h3 className="text-xl font-semibold text-gray-900 mb-4">Indexes ({stats.indexes})</h3>
              <div className="space-y-3">
                {stats.index_details.map((index) => (
                  <div key={index.name} className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-sm font-medium text-gray-900">{index.name}</div>
                        <div className="text-xs text-gray-500 mt-1">
                          {Object.entries(index.keys)
                            .map(([key, value]) => `${key} (${value > 0 ? 'asc' : 'desc'})`)
                            .join(', ')}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Refresh Button */}
        <div className="mt-6 text-center">
          <button
            onClick={() => globalThis.location.reload()}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Refresh Statistics
          </button>
        </div>
      </div>
    </div>
  )
}
