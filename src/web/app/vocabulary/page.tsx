'use client'

import { useState, useEffect, useCallback } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Vocabulary } from '@/types/article'
import { fetchWithAuth } from '@/lib/api'
import { useAuth } from '@/contexts/AuthContext'

/**
 * Vocabulary list page.
 *
 * Features:
 * - Display vocabulary words grouped by language
 * - Show word count and definition
 * - Link to article where word was saved
 * - Requires authentication
 */
export default function VocabularyPage() {
  const router = useRouter()
  const { isAuthenticated } = useAuth()
  const [vocabularies, setVocabularies] = useState<Vocabulary[]>([])
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

      const data: Vocabulary[] = await response.json()
      setVocabularies(data)
    } catch (err: any) {
      setError(err.message || 'Failed to load vocabularies')
      console.error('Error fetching vocabularies:', err)
    } finally {
      setLoading(false)
    }
  }, [router])

  useEffect(() => {
    // Redirect to login if not authenticated
    // Note: AuthProvider already handles loading state before rendering children
    if (!isAuthenticated) {
      router.push('/login')
      return
    }

    fetchVocabularies()
  }, [isAuthenticated, router, fetchVocabularies])

  // Group vocabularies by language
  const vocabulariesByLanguage = vocabularies.reduce((acc, vocab) => {
    const lang = vocab.language
    if (!acc[lang]) {
      acc[lang] = []
    }
    acc[lang].push(vocab)
    return acc
  }, {} as Record<string, Vocabulary[]>)

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
            {loading ? 'Loading...' : `${vocabularies.length} word${vocabularies.length !== 1 ? 's' : ''} saved`}
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
        {!loading && Object.keys(vocabulariesByLanguage).length > 0 && (
          <div className="space-y-6">
            {Object.entries(vocabulariesByLanguage)
              .sort(([a], [b]) => a.localeCompare(b))
              .map(([language, words]) => (
                <div key={language} className="bg-white rounded-lg shadow-lg overflow-hidden">
                  {/* Language Header */}
                  <div className="bg-gradient-to-r from-emerald-600 to-emerald-700 text-white p-4">
                    <h2 className="text-2xl font-semibold">{language}</h2>
                    <p className="text-emerald-100">{words.length} word{words.length !== 1 ? 's' : ''}</p>
                  </div>

                  {/* Words Grid */}
                  <div className="p-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {words.map((vocab) => (
                        <div
                          key={vocab.id}
                          className="bg-gray-50 rounded-lg p-4 border border-gray-200 hover:border-emerald-300 transition-colors"
                        >
                          <div className="flex items-start justify-between mb-2">
                            <span className="text-lg font-semibold text-gray-900">{vocab.lemma}</span>
                            {vocab.word !== vocab.lemma && (
                              <span className="text-sm text-gray-500 italic">({vocab.word})</span>
                            )}
                          </div>
                          <p className="text-sm text-gray-700 mb-2">{vocab.definition}</p>
                          <p className="text-xs text-gray-500 italic mb-2 line-clamp-2">
                            &ldquo;{vocab.sentence}&rdquo;
                          </p>
                          <div className="flex items-center justify-between text-xs text-gray-400">
                            <Link
                              href={`/articles/${vocab.article_id}`}
                              className="text-blue-600 hover:text-blue-800 underline"
                            >
                              View Article
                            </Link>
                            <span>
                              {new Date(vocab.created_at).toLocaleDateString()}
                            </span>
                          </div>
                        </div>
                      ))}
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
