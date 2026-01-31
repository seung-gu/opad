'use client'

import { useState, useEffect, useCallback } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import MarkdownViewer from '@/components/MarkdownViewer'
import ArticleStatusBadge from '@/components/ArticleStatusBadge'
import VocabularyList from '@/components/VocabularyList'
import { Article, Vocabulary } from '@/types/article'
import { TokenUsageRecord } from '@/types/usage'
import { fetchWithAuth } from '@/lib/api'
import { useVocabularyDelete } from '@/hooks/useVocabularyDelete'
import { formatDate } from '@/lib/formatters'
import { useStatusPolling } from '@/hooks/useStatusPolling'

/**
 * Extract agent name from metadata with proper type checking and fallback.
 */
function extractAgentName(metadata?: { agent_name?: unknown; agent_role?: unknown }): string | undefined {
  const rawAgentName = metadata?.agent_name
  if (typeof rawAgentName === 'string' && rawAgentName) {
    return rawAgentName
  }
  const rawAgentRole = metadata?.agent_role
  if (typeof rawAgentRole === 'string' && rawAgentRole) {
    return rawAgentRole
  }
  return undefined
}

/**
 * Helper to format operation names for display.
 */
function formatOperationName(operation: string, agentName?: string): string {
  // Use agent name if available (e.g., "Article Search", "Article Selection", "Article Rewrite")
  if (agentName) {
    return agentName
  }
  // Default: convert snake_case to Title Case
  return operation.replaceAll('_', ' ').replaceAll(/\b\w/g, c => c.toUpperCase())
}

/**
 * Aggregated usage data for display.
 */
interface AggregatedUsage {
  operation: string
  model: string
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  estimated_cost: number
  agent_name?: string // Display name (e.g., "Article Search", "Article Selection")
}

/**
 * Token usage section component.
 * Displays loading, empty, or data states without nested ternaries.
 * Aggregates dictionary_search records into cumulative totals.
 */
function TokenUsageSection({ loading, records }: Readonly<{
  loading: boolean
  records: TokenUsageRecord[]
}>) {

  if (loading) {
    return (
      <div className="mt-6 bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <span aria-hidden="true">📊</span>
          <span>Token Usage</span>
        </h2>
        <div className="animate-pulse space-y-2">
          <div className="h-4 bg-gray-200 rounded w-1/2"></div>
          <div className="h-4 bg-gray-200 rounded w-2/3"></div>
        </div>
      </div>
    )
  }

  if (records.length === 0) {
    return (
      <div className="mt-6 bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <span aria-hidden="true">📊</span>
          <span>Token Usage</span>
        </h2>
        <p className="text-gray-500 text-sm">No token usage data available.</p>
      </div>
    )
  }

  const totalTokens = records.reduce((sum, r) => sum + r.total_tokens, 0)
  const promptTokens = records.reduce((sum, r) => sum + r.prompt_tokens, 0)
  const completionTokens = records.reduce((sum, r) => sum + r.completion_tokens, 0)
  const totalCost = records.reduce((sum, r) => sum + r.estimated_cost, 0)

  // Aggregate dictionary_search only, keep article_generation records separate
  const aggregatedMap = new Map<string, AggregatedUsage>()
  for (const record of records) {
    const agentName = extractAgentName(record.metadata)
    // dictionary_search: aggregate by operation+model
    // article_generation: keep separate using record id
    const key = record.operation === 'dictionary_search'
      ? `op:dictionary_search:${record.model}`
      : `id:${record.id}`

    const existing = aggregatedMap.get(key)
    if (existing) {
      existing.prompt_tokens += record.prompt_tokens
      existing.completion_tokens += record.completion_tokens
      existing.total_tokens += record.total_tokens
      existing.estimated_cost += record.estimated_cost
    } else {
      aggregatedMap.set(key, {
        operation: record.operation,
        model: record.model,
        prompt_tokens: record.prompt_tokens,
        completion_tokens: record.completion_tokens,
        total_tokens: record.total_tokens,
        estimated_cost: record.estimated_cost,
        agent_name: agentName
      })
    }
  }
  const aggregatedRecords = Array.from(aggregatedMap.values())

  return (
    <div className="mt-6 bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
        <span aria-hidden="true">📊</span>
        <span>Token Usage</span>
      </h2>
      <div className="space-y-4">
        {/* Summary */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 p-4 bg-gray-50 rounded-lg">
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wide">Total Tokens</p>
            <p className="text-lg font-semibold text-gray-900">{totalTokens.toLocaleString()}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wide">Prompt</p>
            <p className="text-lg font-semibold text-gray-900">{promptTokens.toLocaleString()}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wide">Completion</p>
            <p className="text-lg font-semibold text-gray-900">{completionTokens.toLocaleString()}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wide">Est. Cost</p>
            <p className="text-lg font-semibold text-green-600">${totalCost.toFixed(4)}</p>
          </div>
        </div>

        {/* Detailed Records - uncontrolled to avoid scroll on re-render */}
        <details className="group">
          <summary className="cursor-pointer text-sm text-blue-600 hover:text-blue-800 font-medium">
            View detailed breakdown ({aggregatedRecords.length} {aggregatedRecords.length === 1 ? 'operation' : 'operations'})
          </summary>
          <div className="mt-3 overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-500 uppercase tracking-wide border-b">
                  <th className="pb-2 pr-4">Operation</th>
                  <th className="pb-2 pr-4">Model</th>
                  <th className="pb-2 pr-4 text-right">Tokens</th>
                  <th className="pb-2 text-right">Cost</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {aggregatedRecords.map((record) => (
                  <tr key={`${record.operation}-${record.model}-${record.agent_name || 'default'}`} className="text-gray-700">
                    <td className="py-2 pr-4">
                      {formatOperationName(record.operation, record.agent_name)}
                    </td>
                    <td className="py-2 pr-4 font-mono text-xs text-gray-500">{record.model}</td>
                    <td className="py-2 pr-4 text-right tabular-nums">
                      {record.total_tokens.toLocaleString()}
                      <span className="text-gray-400 text-xs ml-1">
                        ({record.prompt_tokens.toLocaleString()} + {record.completion_tokens.toLocaleString()})
                      </span>
                    </td>
                    <td className="py-2 text-right tabular-nums text-green-600">
                      ${record.estimated_cost.toFixed(4)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      </div>
    </div>
  )
}

/**
 * Article detail page.
 * 
 * Displays:
 * - Article metadata
 * - Article content (markdown)
 * - Status badge
 * - Progress bar (when status is 'running')
 * - Back to list link
 */
export default function ArticleDetailPage() {
  const params = useParams()
  const articleId = params.id as string
  const { deleteVocabulary } = useVocabularyDelete()

  const [article, setArticle] = useState<Article | null>(null)
  const [content, setContent] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [currentJobId, setCurrentJobId] = useState<string | null>(null)
  const [vocabularies, setVocabularies] = useState<Vocabulary[]>([])
  const [tokenUsage, setTokenUsage] = useState<TokenUsageRecord[]>([])
  const [tokenUsageLoading, setTokenUsageLoading] = useState(false)

  // Reload article data (used by status polling on completion)
  const reloadArticleData = useCallback(async () => {
    try {
      const metadataResponse = await fetchWithAuth(`/api/articles/${articleId}`)
      if (metadataResponse.ok) {
        const articleData: Article = await metadataResponse.json()
        setArticle(articleData)
        if (articleData.job_id) {
          setCurrentJobId(articleData.job_id)
        } else {
          setCurrentJobId(null)
        }
      }

      const contentResponse = await fetchWithAuth(`/api/articles/${articleId}/content`)
      if (contentResponse.ok) {
        const contentText = await contentResponse.text()
        setContent(contentText)
      }
    } catch (error_) {
      console.error('Error reloading article:', error_)
    }
  }, [articleId])

  // Use status polling hook
  const { progress } = useStatusPolling({
    jobId: currentJobId,
    enabled: article?.status === 'running',
    onComplete: () => {
      setCurrentJobId(null)
      reloadArticleData()
    },
    onError: () => {
      setCurrentJobId(null)
      reloadArticleData()
    }
  })

  // Load article metadata and content
  useEffect(() => {
    const fetchArticle = async () => {
      try {
        setLoading(true)
        setError(null)

        // Fetch article metadata via Next.js API route
        const metadataResponse = await fetchWithAuth(`/api/articles/${articleId}`)
        if (metadataResponse.ok) {
          const articleData: Article = await metadataResponse.json()
          setArticle(articleData)
          // Set job_id for polling (same as main page)
          if (articleData.job_id) {
            setCurrentJobId(articleData.job_id)
          }
        } else if (metadataResponse.status === 404) {
          throw new Error('Article not found')
        }

        // Fetch article content
        const contentResponse = await fetchWithAuth(`/api/articles/${articleId}/content`)
        
        if (!contentResponse.ok) {
          if (contentResponse.status === 404) {
            setContent('## Article content is loading...')
            return
          }
          throw new Error('Failed to load article content')
        }

        const contentText = await contentResponse.text()
        setContent(contentText)
        
        // Load vocabularies for this article
        try {
          const vocabResponse = await fetchWithAuth(`/api/articles/${articleId}/vocabularies`)
          if (vocabResponse.ok) {
            const vocabData = await vocabResponse.json()
            setVocabularies(vocabData)
          }
        } catch (error_) {
          console.error('Error fetching vocabularies:', error_)
        }
      } catch (error_: unknown) {
        const message = error_ instanceof Error ? error_.message : 'Failed to load article'
        setError(message)
        console.error('Error fetching article:', error_)
      } finally {
        setLoading(false)
      }
    }

    if (articleId) {
      fetchArticle()
    }
  }, [articleId])
  
  // Helper to filter out a vocabulary by ID
  const removeVocabularyById = useCallback((vocabId: string) => {
    setVocabularies(prev => prev.filter(v => v.id !== vocabId))
  }, [])

  // Listen for vocabulary removal events
  useEffect(() => {
    const handleVocabularyRemoved = (event: CustomEvent) => {
      removeVocabularyById(event.detail)
    }

    globalThis.addEventListener('vocabulary-removed', handleVocabularyRemoved as EventListener)
    return () => {
      globalThis.removeEventListener('vocabulary-removed', handleVocabularyRemoved as EventListener)
    }
  }, [removeVocabularyById])

  // Fetch token usage function (reusable)
  // isRefresh: true when refreshing existing data (skip loading state to preserve UI)
  const fetchTokenUsage = useCallback(async (isRefresh = false) => {
    if (article?.status !== 'completed') return

    if (!isRefresh) {
      setTokenUsageLoading(true)
    }
    try {
      const response = await fetchWithAuth(`/api/usage/articles/${articleId}`)
      if (response.ok) {
        const usageData = await response.json()
        setTokenUsage(usageData)
      }
    } catch (error_) {
      console.error('Error fetching token usage:', error_)
      // Silent fail - token usage is not critical
    } finally {
      if (!isRefresh) {
        setTokenUsageLoading(false)
      }
    }
  }, [article?.status, articleId])

  // Fetch token usage when article is completed
  useEffect(() => {
    fetchTokenUsage()
  }, [fetchTokenUsage])
  
  // Handle vocabulary addition
  const handleAddVocabulary = (newVocab: Vocabulary) => {
    setVocabularies(prev => {
      // Check if already exists (avoid duplicates)
      if (prev.some(v => v.id === newVocab.id || v.lemma.toLowerCase() === newVocab.lemma.toLowerCase())) {
        return prev
      }
      return [...prev, newVocab]
    })
  }
  
  // Handle vocabulary deletion
  const handleDeleteVocabulary = async (vocabId: string) => {
    try {
      await deleteVocabulary(vocabId)
      setVocabularies(prev => prev.filter(v => v.id !== vocabId))
    } catch (error_) {
      console.error('Failed to delete vocabulary:', error_)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 py-8">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="animate-pulse">
            <div className="h-8 bg-gray-200 rounded w-3/4 mb-4"></div>
            <div className="h-4 bg-gray-200 rounded w-1/2 mb-8"></div>
            <div className="space-y-4">
              <div className="h-4 bg-gray-200 rounded"></div>
              <div className="h-4 bg-gray-200 rounded w-5/6"></div>
              <div className="h-4 bg-gray-200 rounded w-4/6"></div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (error || !article) {
    return (
      <div className="min-h-screen bg-gray-50 py-8">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="bg-red-50 border border-red-200 rounded-lg p-6">
            <h2 className="text-xl font-semibold text-red-900 mb-2">Error</h2>
            <p className="text-red-800 mb-4">{error || 'Article not found'}</p>
            <Link
              href="/articles"
              className="text-blue-600 hover:text-blue-800 underline"
            >
              ← Back to Articles
            </Link>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-6">
          <Link
            href="/articles"
            className="text-blue-600 hover:text-blue-800 text-sm mb-4 inline-block"
          >
            ← Back to Articles
          </Link>
          
          <div className="flex items-start justify-between gap-4 mb-4">
            <div className="flex-1">
              <h1 className="text-3xl font-bold text-gray-900 mb-2">
                {article.topic || 'Untitled Article'}
              </h1>
              <div className="flex flex-wrap items-center gap-3 text-sm text-gray-600 mb-2">
                <span className="font-medium">{article.language}</span>
                <span>•</span>
                <span>Level {article.level}</span>
                <span>•</span>
                <span>{article.length} words</span>
              </div>
              <div className="text-xs text-gray-500">
                Created: {formatDate(article.created_at)}
              </div>
            </div>
            <ArticleStatusBadge status={article.status} />
          </div>
        </div>

        {/* Progress Bar (only when running) */}
        {article.status === 'running' && currentJobId && (
          <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg shadow-sm">
            <div className="mb-2">
              <p className="text-gray-800 font-medium mb-2">
                ⏳ {progress.message || 'Generating article...'}
              </p>
              {progress.error && (
                <div className="mb-2 p-3 bg-red-50 border border-red-200 rounded-md">
                  <p className="text-red-800 text-sm font-medium">Error:</p>
                  <p className="text-red-700 text-sm">{progress.error}</p>
                </div>
              )}
              <div className="w-full bg-gray-200 rounded-full h-3">
                <div
                  className="bg-blue-600 h-3 rounded-full transition-all duration-300"
                  style={{ width: `${progress.progress}%` }}
                ></div>
              </div>
              <p className="text-sm text-blue-700 mt-2">{progress.progress}%</p>
            </div>
          </div>
        )}

        {/* Content */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          {content ? (
            /*
             * Key prop pattern forces component remount on content change.
             * Pattern: ${articleId}-${content.length}
             * - Prevents React hydration mismatches
             * - Resets data-processed attribute (MarkdownViewer.tsx:456)
             * - Clears stale event listeners
             * See: docs/ARCHITECTURE.md "React Component Remounting Pattern"
             */
            <MarkdownViewer
              key={`${articleId}-${content.length}`}
              content={content}
              language={article?.language}
              articleId={articleId}
              vocabularies={vocabularies}
              onAddVocabulary={handleAddVocabulary}
              onTokenUsageUpdate={() => fetchTokenUsage(true)}
            />
          ) : (
            <div className="text-center py-12">
              <p className="text-gray-500">
                {article.status === 'running'
                  ? 'Article is being generated. Please check back later.'
                  : 'Article content is not available.'}
              </p>
            </div>
          )}
        </div>
        
        {/* Vocabulary List */}
        <VocabularyList
          vocabularies={vocabularies}
          onDelete={handleDeleteVocabulary}
        />

        {/* Token Usage Section */}
        {article.status === 'completed' && (
          <TokenUsageSection
            loading={tokenUsageLoading}
            records={tokenUsage}
          />
        )}
      </div>
    </div>
  )
}
