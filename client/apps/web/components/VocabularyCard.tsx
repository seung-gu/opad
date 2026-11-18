'use client'

import { useState } from 'react'
import Link from 'next/link'
import { getLevelColor } from '@/lib/styleHelpers'
import { Conjugations } from '@opad/libs'

export interface VocabularyCardProps {
  id: string
  lemma: string
  word: string
  definition: string
  sentence: string
  gender?: string | null
  phonetics?: string | null
  pos?: string | null
  level?: string | null
  conjugations?: Conjugations | null
  examples?: string[] | null
  // Optional fields for VocabularyCount
  count?: number
  articleId?: string
  createdAt?: string
  // Display options
  variant?: 'list' | 'card'
  showArticleLink?: boolean
  onDelete?: (id: string) => void
}

export default function VocabularyCard({
  id,
  lemma,
  word,
  definition,
  sentence,
  gender,
  phonetics,
  pos,
  level,
  conjugations,
  examples,
  count,
  articleId,
  createdAt,
  variant = 'list',
  showArticleLink = false,
  onDelete,
}: Readonly<VocabularyCardProps>) {
  const [examplesExpanded, setExamplesExpanded] = useState(false)

  const hasConjugations = conjugations && (
    conjugations.present || conjugations.past || conjugations.participle ||
    conjugations.genitive || conjugations.plural
  )
  const isVerb = conjugations?.present || conjugations?.past || conjugations?.participle

  const toggleExamples = () => setExamplesExpanded(prev => !prev)

  const headword = (
    <div className="flex items-baseline gap-2 flex-wrap">
      {gender && <span className="text-[13px] text-text-dim">{gender}</span>}
      <span className="font-serif text-[19px] text-text-strong">{lemma}</span>
      {phonetics && <span className="font-mono text-[12px] text-text-dim">{phonetics}</span>}
      {variant === 'list' && word.toLowerCase() !== lemma.toLowerCase() && (
        <span className="text-[13px] text-text-dim">({word})</span>
      )}
    </div>
  )

  const tags = (
    <div className="mt-0.5 flex flex-wrap items-baseline gap-2 text-[12px] text-text-dim">
      {pos && <span>{pos}</span>}
      {level && <span className={`px-1 ${getLevelColor(level)}`}>{level}</span>}
      {(count ?? 0) > 1 && <span className="text-accent">×{count}</span>}
    </div>
  )

  const details = (
    <>
      <p className="text-[14px] text-foreground">{definition}</p>

      {hasConjugations && (
        <p className="mt-1 text-[12px] text-text-dim">
          {isVerb ? (
            <>
              {[conjugations?.present, conjugations?.past, conjugations?.participle]
                .filter(Boolean)
                .join(' · ')}
              {conjugations?.auxiliary && ` (${conjugations.auxiliary})`}
            </>
          ) : (
            [
              conjugations?.genitive && `Gen. ${conjugations.genitive}`,
              conjugations?.plural && `Pl. ${conjugations.plural}`
            ]
              .filter(Boolean)
              .join(' · ')
          )}
        </p>
      )}

      <div className="mt-1.5">
        <button
          type="button"
          className="text-[12px] text-accent hover:opacity-80"
          onClick={toggleExamples}
        >
          Examples {examplesExpanded ? '−' : '+'}
        </button>
        {examplesExpanded && (
          <div className="mt-1 space-y-0.5">
            <p className="font-serif text-[14px] italic leading-relaxed text-text-dim">{sentence}</p>
            {examples?.slice(0, 3).map((example) => (
              <p key={example} className="font-serif text-[14px] italic leading-relaxed text-text-dim">
                {example}
              </p>
            ))}
          </div>
        )}
      </div>

      {showArticleLink && articleId && (
        <div className="mt-3 flex items-baseline justify-between gap-3 text-[12px]">
          <Link href={`/articles/${articleId}`} className="text-accent">
            View in article
          </Link>
          {createdAt && <span className="text-text-dim">{new Date(createdAt).toLocaleDateString()}</span>}
        </div>
      )}
    </>
  )

  const removeButton = onDelete && (
    <button
      onClick={() => onDelete(id)}
      className="btn-remove text-[16px] leading-none"
      title="Remove from vocabulary"
      type="button"
    >
      −
    </button>
  )

  // Grid variant used on the vocabulary page
  if (variant === 'card') {
    return (
      <div className="flex flex-col border border-border-card bg-card p-5 transition-colors hover:border-accent">
        <div className="flex items-start justify-between gap-2">
          <div>
            {headword}
            {tags}
          </div>
          {removeButton}
        </div>
        <div className="mt-3">{details}</div>
      </div>
    )
  }

  // List variant used under an article: headword left, meaning right
  return (
    <div className="grid gap-x-6 gap-y-2 py-4 sm:grid-cols-[14rem_1fr]">
      <div className="flex items-start justify-between gap-2">
        <div>
          {headword}
          {tags}
        </div>
        <span className="sm:hidden">{removeButton}</span>
      </div>
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">{details}</div>
        <span className="hidden sm:block">{removeButton}</span>
      </div>
    </div>
  )
}
