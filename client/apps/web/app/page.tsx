'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import InputForm from '@/components/InputForm'
import SiteHeader from '@/components/SiteHeader'
import ErrorAlert from '@/components/ErrorAlert'
import { fetchWithAuth } from '@/lib/api'
import { useAuth } from '@/contexts/AuthContext'
import { Article, ArticleListResponse, formatDate } from '@opad/libs'

const STEPS = [
  { verb: 'Search', desc: 'Recent news and stories on the topic you gave.' },
  { verb: 'Collect', desc: 'The sources that are actually worth reading.' },
  { verb: 'Transform', desc: 'The text, rewritten to your level and length.' },
  { verb: 'Deliver', desc: 'An article whose every word you can look up.' },
]

const RECENT_LIMIT = 3

export default function Home() {
  const router = useRouter()
  const { isAuthenticated } = useAuth()
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [progress, setProgress] = useState({ progress: 0, message: '', error: null as string | null })
  const [currentJobId, setCurrentJobId] = useState<string | null>(null)
  const [currentArticleId, setCurrentArticleId] = useState<string | null>(null)
  const [recent, setRecent] = useState<Article[]>([])

  // Recent articles for the signed-in landing view
  const fetchRecent = useCallback(async () => {
    if (!isAuthenticated) {
      setRecent([])
      return
    }
    try {
      const response = await fetchWithAuth(`/api/articles?skip=0&limit=${RECENT_LIMIT}`)
      if (!response.ok) return
      const data: ArticleListResponse = await response.json()
      setRecent(data.articles)
    } catch (err) {
      // Non-critical: the landing page works without the recent list
      console.error('Failed to load recent articles:', err)
    }
  }, [isAuthenticated])

  useEffect(() => {
    fetchRecent()
  }, [fetchRecent])

  // Poll job status while generating
  useEffect(() => {
    if (!generating || !currentJobId) return

    let interval: ReturnType<typeof setInterval> | null = null

    const loadStatus = () => {
      fetchWithAuth(`/api/status?job_id=${currentJobId}`)
        .then((res) => res.json())
        .then((data) => {
          setProgress({
            progress: data.progress || 0,
            message: data.message || '',
            error: data.error || null,
          })

          if (data.status === 'completed') {
            setGenerating(false)
            setCurrentJobId(null)
            if (interval) clearInterval(interval)
            const articleId = data.article_id || currentArticleId
            if (articleId) {
              router.push(`/articles/${articleId}`)
            }
          } else if (data.status === 'error') {
            setGenerating(false)
            setCurrentJobId(null)
            setError(data.error || data.message || 'Generation failed')
            if (interval) clearInterval(interval)
          }
        })
        .catch((err) => {
          console.error('Failed to fetch status:', err)
        })
    }

    loadStatus()
    interval = setInterval(loadStatus, 5000)

    return () => {
      if (interval) clearInterval(interval)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- currentArticleId/router omitted to prevent unintended re-polls
  }, [generating, currentJobId])

  // Resume an existing job instead of starting a duplicate
  const handleUseExistingJob = useCallback(
    (job: { id: string; status: string; error?: string }, articleId?: string) => {
      if (job.status === 'completed' && articleId) {
        router.push(`/articles/${articleId}`)
        return
      }
      if (job.status === 'running' || job.status === 'queued') {
        setCurrentJobId(job.id)
        if (articleId) setCurrentArticleId(articleId)
        setGenerating(true)
        return
      }
      if (job.status === 'failed') {
        setError(job.error || 'Previous generation failed')
      }
      setGenerating(false)
    },
    [router]
  )

  const handleGenerate = async (
    inputs: { language: string; level: string; length: string; topic: string },
    force = false
  ): Promise<void> => {
    if (!isAuthenticated) {
      router.push('/login')
      return
    }

    setError(null)
    setGenerating(true)
    try {
      const response = await fetchWithAuth('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...inputs, force }),
      })

      const data = await response.json()

      // Duplicate job (409) must be handled before the generic error branch
      if (response.status === 409 || data.duplicate) {
        if (!data.existing_job) {
          const shouldRegenerate = globalThis.confirm(
            'A duplicate job was detected, but its status could not be retrieved. Generate a new article anyway?'
          )
          if (shouldRegenerate) {
            return await handleGenerate(inputs, true)
          }
          setGenerating(false)
          return
        }

        const job = data.existing_job
        const messages: Record<string, string> = {
          completed: 'A completed job exists within the last 24 hours. Generate a new one?',
          running: `A job is already running (${job.progress}%). Generate a new one?`,
          failed: `The previous job failed: ${job.error || 'Unknown error'}. Generate a new one?`,
          queued: 'A job is already queued. Generate a new one?',
        }

        if (globalThis.confirm(messages[job.status])) {
          return await handleGenerate(inputs, true)
        }

        handleUseExistingJob(job, data.article_id)
        return
      }

      if (!response.ok) {
        throw new Error(data.error || 'Failed to generate article')
      }

      if (data.job_id) setCurrentJobId(data.job_id)
      if (data.article_id) setCurrentArticleId(data.article_id)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Unknown error')
      setGenerating(false)
      setCurrentJobId(null)
    }
  }

  return (
    <div className="min-h-screen bg-background">
      <SiteHeader />

      <main className="mx-auto max-w-3xl px-6">
        <section className="pb-12 pt-14">
          <p className="font-serif text-[15px] italic text-text-dim">One story a day</p>
          <h1 className="mt-3 max-w-[18ch] font-serif text-[40px] font-normal leading-[1.06] tracking-[-0.015em] text-text-strong sm:text-[54px]">
            Read today&rsquo;s news in the language you&rsquo;re learning.
          </h1>
          <p className="mt-7 max-w-xl text-[15px] leading-[1.7] text-text-dim">
            Real news, published today, rewritten to your level. Any language, any topic, a new one each morning.
          </p>
        </section>

        <div className="space-y-12 pb-4">
          <section>
            <ErrorAlert error={error} />
            <InputForm onSubmit={handleGenerate} loading={generating} />

            {generating && (
              <div className="mt-4">
                <div className="flex items-baseline justify-between text-[13px]">
                  <span className="font-serif italic text-foreground">
                    {progress.message || 'Starting'}&hellip;
                  </span>
                  <span className="tabular-nums text-text-dim">{progress.progress}%</span>
                </div>
                <div className="mt-2 h-px w-full bg-border-card">
                  <div
                    className="h-px bg-accent transition-all duration-300"
                    style={{ width: `${progress.progress}%` }}
                  />
                </div>
                {progress.error && <p className="mt-2 text-[13px] text-accent-danger">{progress.error}</p>}
              </div>
            )}
          </section>

          <section className="border-t border-border-card pt-10">
            <div className="grid gap-x-8 gap-y-8 sm:grid-cols-2 lg:grid-cols-4">
              {STEPS.map((step, i) => (
                <div key={step.verb}>
                  <div className="font-serif text-[30px] leading-none text-accent">{i + 1}</div>
                  <h3 className="mt-3 font-serif text-[19px] font-medium text-text-strong">{step.verb}</h3>
                  <p className="mt-1.5 text-[13px] leading-[1.65] text-text-dim">{step.desc}</p>
                </div>
              ))}
            </div>
          </section>

          {isAuthenticated ? (
            <section className="border-t border-border-card pt-8">
              <div className="flex items-baseline justify-between">
                <h2 className="font-serif text-[19px] italic text-text-strong">Recent</h2>
                <Link href="/articles" className="text-[13px] text-accent">
                  All articles
                </Link>
              </div>
              {recent.length === 0 ? (
                <p className="mt-3 text-[13px] text-text-dim">
                  Nothing yet. Generate your first article above.
                </p>
              ) : (
                <ul className="mt-2">
                  {recent.map((article) => (
                    <li key={article.id} className="group border-b border-border-card last:border-b-0">
                      <Link
                        href={`/articles/${article.id}`}
                        className="flex flex-wrap items-baseline justify-between gap-x-5 gap-y-1 py-4"
                      >
                        <span className="font-serif text-[19px] leading-snug text-text-strong transition-colors group-hover:text-accent">
                          {article.topic || 'Untitled Article'}
                        </span>
                        <span className="shrink-0 text-[12px] text-text-dim">
                          {article.language} · {article.level} · {article.length} words ·{' '}
                          {formatDate(article.created_at)}
                        </span>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          ) : (
            <section className="border-t border-border-card pt-8">
              <p className="text-[14px] leading-relaxed text-text-dim">
                <Link href="/login" className="font-medium text-accent">
                  Sign in
                </Link>{' '}
                to keep your articles and the words you look up.
              </p>
            </section>
          )}
        </div>

        <footer className="mt-14 border-t border-border-card py-6 text-[12px] text-text-dim">
          One story a day
        </footer>
      </main>
    </div>
  )
}
