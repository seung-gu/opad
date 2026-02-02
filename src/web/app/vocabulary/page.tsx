'use client'

import { useState, useEffect, useCallback } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { VocabularyCount } from '@/types/article'
import { fetchWithAuth, parseErrorResponse } from '@/lib/api'
import { useAuth } from '@/contexts/AuthContext'
import { useVocabularyDelete } from '@/hooks/useVocabularyDelete'
import { getLevelColor } from '@/lib/styleHelpers'
import ErrorAlert from '@/components/ErrorAlert'
import EmptyState from '@/components/EmptyState'

/**
 * Vocabulary list page.
 *
 * Features:
 * - Display vocabulary words grouped by language and lemma
 * - Show word count for each lemma
 * - Display definition and sentence from most recent entry
 * - Link to all articles where word was saved
 * - Requires authentication
 */
export default function VocabularyPage() {
  const router = useRouter()
  const { isAuthenticated } = useAuth()
  const { deleteVocabulary } = useVocabularyDelete()
  const [vocabularies, setVocabularies] = useState<VocabularyCount[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchVocabularies = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const response = await fetchWithAuth('/api/dictionary/vocabularies')

      if (!response.ok) {
        if (response.status === 401) {
          router.push('/login')
          return
        }
        const errorMsg = await parseErrorResponse(response, 'Failed to load vocabularies')
        throw new Error(errorMsg)
      }

      const data: VocabularyCount[] = await response.json()
      setVocabularies(data)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to load vocabularies'
      setError(message)
      console.error('Error fetching vocabularies:', err)
    } finally {
      setLoading(false)
    }
  }, [router])

  const handleDeleteVocabulary = async (vocabId: string) => {
    try {
      await deleteVocabulary(vocabId)
      // Remove from state on success
      setVocabularies(prev => prev.filter(v => v.id !== vocabId))
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to delete vocabulary'
      console.error('Failed to delete vocabulary:', err)
      setError(message)
    }
  }

  useEffect(() => {
    // Redirect to login if not authenticated
    // Note: AuthProvider already handles loading state before rendering children
    if (!isAuthenticated) {
      router.push('/login')
      return
    }

    fetchVocabularies()
  }, [isAuthenticated, router, fetchVocabularies])

  // Group by language for display (data is already aggregated by backend)
  const groupsByLanguage = vocabularies.reduce((acc, vocab) => {
    if (!acc[vocab.language]) {
      acc[vocab.language] = []
    }
    acc[vocab.language].push(vocab)
    return acc
  }, {} as Record<string, VocabularyCount[]>)

  // Calculate total and unique counts from pre-aggregated data
  const totalCount = vocabularies.reduce((sum, v) => sum + v.count, 0)
  const uniqueCount = vocabularies.length

  return (
    <div className="min-h-screen bg-background py-8">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <h1 className="text-3xl font-bold font-mono text-vocab">My Vocabulary</h1>
            <Link
              href="/articles"
              className="text-xl font-medium text-foreground hover:text-foreground/80 transition-colors"
              title="Go to Articles"
            >
              ◀ Articles
            </Link>
          </div>
          <p className="text-text-dim">
            {loading ? 'Loading...' : `${totalCount} saved (${uniqueCount} unique)`}
          </p>
        </div>

        {/* Error State */}
        <ErrorAlert error={error} onRetry={fetchVocabularies} />

        {/* Loading State */}
        {loading && (
          <div className="flex items-center justify-center py-12">
            <div className="text-lg text-text-dim">Loading vocabularies...</div>
          </div>
        )}

        {/* Empty State */}
        {!loading && vocabularies.length === 0 && !error && (
          <EmptyState
            title="No vocabulary words found."
            description="Click on words while reading articles to save them to your vocabulary."
            action={{
              label: 'Go to Articles',
              onClick: () => router.push('/articles')
            }}
          />
        )}

        {/* Vocabulary List by Language */}
        {!loading && Object.keys(groupsByLanguage).length > 0 && (
          <div className="space-y-6">
            {Object.entries(groupsByLanguage)
              .sort(([a], [b]) => a.localeCompare(b))
              .map(([language, groups]) => (
                <div key={language} className="bg-card rounded-lg shadow-lg overflow-hidden hover:border-accent/50 transition-colors border border-transparent">
                  {/* Language Header */}
                  <div className="bg-gradient-to-r from-vocab to-vocab/80 p-4">
                    <h2 className="text-sm font-semibold font-mono text-white tracking-wide uppercase">📚 {language}</h2>
                    <p className="text-white/80">
                      {groups.reduce((sum, g) => sum + g.count, 0)} saved ({groups.length} unique)
                    </p>
                  </div>

                  {/* Words Grid */}
                  <div className="p-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {groups.map((group) => {
                        return (
                          <div
                            key={`${group.language}-${group.lemma}`}
                            className="bg-background rounded-lg p-4 border border-border-card hover:border-vocab/50 transition-colors flex flex-col"
                          >
                            {/* Header: Lemma with gender + badges */}
                            <div className="flex items-start justify-between mb-2">
                              <div className="flex items-baseline gap-1 flex-wrap">
                                {/* Gender prefix (if available) */}
                                {group.gender && (
                                  <span className="text-sm font-medium text-text-dim">{group.gender}</span>
                                )}
                                {/* Lemma */}
                                <span className="text-lg font-semibold text-foreground">{group.lemma}</span>
                              </div>
                              <div className="flex items-center gap-2 flex-shrink-0">
                                {/* Count badge */}
                                {group.count > 1 && (
                                  <span className="text-sm font-medium text-vocab bg-vocab/20 px-2 py-1 rounded">
                                    x{group.count}
                                  </span>
                                )}
                                {/* Delete button */}
                                <button
                                  onClick={() => handleDeleteVocabulary(group.id)}
                                  className="btn-remove"
                                  title="Remove from vocabulary"
                                >
                                  −
                                </button>
                              </div>
                            </div>

                            {/* Metadata badges: POS + Level */}
                            <div className="flex items-center gap-2 mb-2 flex-wrap">
                              {group.pos && (
                                <span className="text-xs font-medium bg-accent/20 text-accent px-2 py-0.5 rounded">
                                  {group.pos}
                                </span>
                              )}
                              {group.level && (
                                <span className={`text-xs font-medium px-2 py-0.5 rounded ${getLevelColor(group.level)}`}>
                                  {group.level}
                                </span>
                              )}
                            </div>

                            {/* Original word form (if different from lemma) */}
                            {group.word !== group.lemma && (
                              <p className="text-xs text-text-dim italic mb-1">({group.word})</p>
                            )}

                            {/* Definition */}
                            <p className="text-sm text-foreground mb-2">{group.definition}</p>

                            {/* Conjugations (if verb) */}
                            {group.conjugations && (group.conjugations.present || group.conjugations.past || group.conjugations.perfect) && (
                              <div className="text-xs text-text-dim mb-2 bg-card-hover rounded p-2">
                                {[group.conjugations.present, group.conjugations.past, group.conjugations.perfect]
                                  .filter(Boolean)
                                  .join(' - ')}
                              </div>
                            )}

                            {/* Example sentence */}
                            <p className="text-xs text-text-dim italic mb-2 line-clamp-2">
                              &ldquo;{group.sentence}&rdquo;
                            </p>

                            {/* Footer: Date + Article count */}
                            <div className="flex items-center justify-between text-xs text-text-dim mb-2">
                              <span>
                                {new Date(group.created_at).toLocaleDateString()}
                              </span>
                              <span>
                                {group.article_ids.length} article{group.article_ids.length !== 1 ? 's' : ''}
                              </span>
                            </div>

                            {/* Article link - most recent only, fixed at bottom */}
                            <div className="mt-auto">
                              <Link
                                href={`/articles/${group.article_id}`}
                                className="text-xs text-accent hover:text-accent/80 underline"
                              >
                                View in Article
                              </Link>
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                </div>
              ))}
          </div>
        )}

        {/* Refresh Button */}
        {!loading && vocabularies.length > 0 && (
          <div className="mt-6 text-center">
            <button
              onClick={fetchVocabularies}
              className="btn-outline"
            >
              Refresh List
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
