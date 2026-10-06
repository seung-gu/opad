'use client'

import { useState, useEffect, useCallback, useMemo } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { VocabularyCount } from '@opad/libs'
import { fetchWithAuth, parseErrorResponse } from '@/lib/api'
import { useAuth } from '@/contexts/AuthContext'
import { useVocabularyDelete } from '@/hooks/useVocabularyDelete'
import VocabularyCard from '@/components/VocabularyCard'
import ErrorAlert from '@/components/ErrorAlert'
import EmptyState from '@/components/EmptyState'
import SiteHeader from '@/components/SiteHeader'
import { sortVocabularies, VOCABULARY_SORTS, type VocabularySort } from '@/lib/vocabularySort'

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
  // Frequency matches the order the API already returns, so the default is a no-op
  const [sort, setSort] = useState<VocabularySort>('frequency')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchVocabularies = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const response = await fetchWithAuth('/api/dictionary/vocabularies?limit=1000')

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

  // Group by language for display (data is already aggregated by backend),
  // then order each group by the chosen sort.
  const groupsByLanguage = useMemo(() => {
    const groups = vocabularies.reduce((acc, vocab) => {
      if (!acc[vocab.language]) {
        acc[vocab.language] = []
      }
      acc[vocab.language].push(vocab)
      return acc
    }, {} as Record<string, VocabularyCount[]>)

    for (const language of Object.keys(groups)) {
      groups[language] = sortVocabularies(groups[language], sort)
    }
    return groups
  }, [vocabularies, sort])

  // Calculate total and unique counts from pre-aggregated data
  const totalCount = vocabularies.reduce((sum, v) => sum + v.count, 0)
  const uniqueCount = vocabularies.length

  return (
    <div className="min-h-screen bg-background">
      <SiteHeader title="One story a day" />

      <main className="mx-auto max-w-5xl px-6">
        <section className="pb-8 pt-12">
          <h1 className="font-serif text-[34px] leading-tight text-text-strong">Vocabulary</h1>
          <p className="mt-2 text-[14px] text-text-dim">
            {loading ? 'Loading…' : `${totalCount} saved · ${uniqueCount} unique`}
          </p>
        </section>

        {!loading && vocabularies.length > 0 && (
          <div className="flex flex-wrap items-baseline gap-x-5 gap-y-3 border-t border-border-card py-4">
            <span className="text-[12px] text-text-dim">Sort</span>
            <div className="flex flex-wrap items-baseline">
              {VOCABULARY_SORTS.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  aria-pressed={sort === option.value}
                  onClick={() => setSort(option.value)}
                  className={`border-b-2 px-1.5 pb-0.5 text-[13px] transition-colors ${
                    sort === option.value
                      ? 'border-accent font-medium text-foreground'
                      : 'border-transparent text-text-dim hover:text-foreground'
                  }`}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>
        )}

        <ErrorAlert error={error} onRetry={fetchVocabularies} />

        {loading && <p className="border-t border-border-card py-10 text-[14px] text-text-dim">Loading…</p>}

        {!loading && vocabularies.length === 0 && !error && (
          <EmptyState
            title="No words saved yet."
            description="Click a word while reading an article to look it up and save it here."
            action={{
              label: 'Go to articles',
              onClick: () => router.push('/articles'),
            }}
          />
        )}

        {!loading && Object.keys(groupsByLanguage).length > 0 && (
          <div className="space-y-12">
            {Object.entries(groupsByLanguage)
              .sort(([a], [b]) => a.localeCompare(b))
              .map(([language, groups]) => (
                <section key={language} className="border-t border-border-card pt-6">
                  <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
                    <h2 className="font-serif text-[22px] text-text-strong">{language}</h2>
                    <span className="text-[12px] text-text-dim">
                      {groups.reduce((sum, g) => sum + g.count, 0)} saved · {groups.length} unique
                    </span>
                  </div>

                  <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {groups.map((group) => (
                      <VocabularyCard
                        key={`${group.language}-${group.lemma}`}
                        id={group.id}
                        lemma={group.lemma}
                        word={group.word}
                        definition={group.definition}
                        sentence={group.sentence}
                        gender={group.gender}
                        phonetics={group.phonetics}
                        pos={group.pos}
                        level={group.level}
                        conjugations={group.conjugations}
                        examples={group.examples}
                        count={group.count}
                        articleId={group.article_id}
                        createdAt={group.created_at}
                        variant="card"
                        showArticleLink
                        onDelete={handleDeleteVocabulary}
                      />
                    ))}
                  </div>
                </section>
              ))}
          </div>
        )}

        {!loading && vocabularies.length > 0 && (
          <div className="mt-10">
            <button onClick={fetchVocabularies} className="btn-outline">
              Refresh
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
