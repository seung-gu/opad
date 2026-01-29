'use client'

import { useState, useEffect, useCallback } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { VocabularyCount } from '@/types/article'
import { fetchWithAuth } from '@/lib/api'
import { useAuth } from '@/contexts/AuthContext'
import { useVocabularyDelete } from '@/hooks/useVocabularyDelete'

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
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.error || errorData.detail || 'Failed to load vocabularies')
      }

      const data: VocabularyCount[] = await response.json()
      setVocabularies(data)
    } catch (err: any) {
      setError(err.message || 'Failed to load vocabularies')
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
    } catch (err: any) {
      console.error('Failed to delete vocabulary:', err)
      setError(err.message || 'Failed to delete vocabulary')
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
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <h1 className="text-3xl font-bold text-gray-900">My Vocabulary</h1>
            <Link
              href="/articles"
              className="text-xl font-medium text-gray-700 hover:text-gray-900 transition-colors"
              title="Go to Articles"
            >
              ◀ Articles
            </Link>
          </div>
          <p className="text-gray-600">
            {loading ? 'Loading...' : `${totalCount} saved (${uniqueCount} unique)`}
          </p>
        </div>

        {/* Error State */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-800">{error}</p>
            <button
              onClick={fetchVocabularies}
              className="mt-2 text-sm text-red-600 hover:text-red-800 underline"
            >
              Try again
            </button>
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="flex items-center justify-center py-12">
            <div className="text-lg text-gray-500">Loading vocabularies...</div>
          </div>
        )}

        {/* Empty State */}
        {!loading && vocabularies.length === 0 && !error && (
          <div className="bg-white rounded-lg shadow-lg p-8 text-center">
            <p className="text-gray-500 text-lg mb-4">No vocabulary words found.</p>
            <p className="text-gray-400">
              Click on words while reading articles to save them to your vocabulary.
            </p>
            <Link
              href="/articles"
              className="inline-block mt-4 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Go to Articles
            </Link>
          </div>
        )}

        {/* Vocabulary List by Language */}
        {!loading && Object.keys(groupsByLanguage).length > 0 && (
          <div className="space-y-6">
            {Object.entries(groupsByLanguage)
              .sort(([a], [b]) => a.localeCompare(b))
              .map(([language, groups]) => (
                <div key={language} className="bg-white rounded-lg shadow-lg overflow-hidden">
                  {/* Language Header */}
                  <div className="bg-gradient-to-r from-emerald-600 to-emerald-700 text-white p-4">
                    <h2 className="text-2xl font-semibold">{language}</h2>
                    <p className="text-emerald-100">
                      {groups.reduce((sum, g) => sum + g.count, 0)} saved ({groups.length} unique)
                    </p>
                  </div>

                  {/* Words Grid */}
                  <div className="p-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {groups.map((group) => {
                        // Helper function for CEFR level badge color
                        const getLevelColor = (level?: string) => {
                          if (!level) return 'bg-gray-100 text-gray-600'
                          if (level.startsWith('A')) return 'bg-green-100 text-green-700'
                          if (level.startsWith('B')) return 'bg-yellow-100 text-yellow-700'
                          return 'bg-red-100 text-red-700' // C1, C2
                        }

                        return (
                          <div
                            key={`${group.language}-${group.lemma}`}
                            className="bg-gray-50 rounded-lg p-4 border border-gray-200 hover:border-emerald-300 transition-colors flex flex-col"
                          >
                            {/* Header: Lemma with gender + badges */}
                            <div className="flex items-start justify-between mb-2">
                              <div className="flex items-baseline gap-1 flex-wrap">
                                {/* Gender prefix (if available) */}
                                {group.gender && (
                                  <span className="text-sm font-medium text-gray-500">{group.gender}</span>
                                )}
                                {/* Lemma */}
                                <span className="text-lg font-semibold text-gray-900">{group.lemma}</span>
                              </div>
                              <div className="flex items-center gap-2 flex-shrink-0">
                                {/* Count badge */}
                                {group.count > 1 && (
                                  <span className="text-sm font-medium text-emerald-600 bg-emerald-100 px-2 py-1 rounded">
                                    {group.count}×
                                  </span>
                                )}
                                {/* Delete button */}
                                <button
                                  onClick={() => handleDeleteVocabulary(group.id)}
                                  className="px-2 py-1 text-sm text-red-600 hover:text-red-800 hover:bg-red-50 rounded transition-colors"
                                  title="Remove from vocabulary"
                                >
                                  −
                                </button>
                              </div>
                            </div>

                            {/* Metadata badges: POS + Level */}
                            <div className="flex items-center gap-2 mb-2 flex-wrap">
                              {group.pos && (
                                <span className="text-xs font-medium bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
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
                              <p className="text-xs text-gray-500 italic mb-1">({group.word})</p>
                            )}

                            {/* Definition */}
                            <p className="text-sm text-gray-700 mb-2">{group.definition}</p>

                            {/* Conjugations (if verb) */}
                            {group.conjugations && (group.conjugations.present || group.conjugations.past || group.conjugations.perfect) && (
                              <div className="text-xs text-gray-600 mb-2 bg-gray-100 rounded p-2">
                                {[group.conjugations.present, group.conjugations.past, group.conjugations.perfect]
                                  .filter(Boolean)
                                  .join(' - ')}
                              </div>
                            )}

                            {/* Example sentence */}
                            <p className="text-xs text-gray-500 italic mb-2 line-clamp-2">
                              &ldquo;{group.sentence}&rdquo;
                            </p>

                            {/* Footer: Date + Article count */}
                            <div className="flex items-center justify-between text-xs text-gray-400 mb-2">
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
                                className="text-xs text-blue-600 hover:text-blue-800 underline"
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
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Refresh List
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
