'use client'

import { useState } from 'react'
import Link from 'next/link'
import { getLevelColor } from '@/lib/styleHelpers'
import { Conjugations } from '@/types/article'

export interface VocabularyCardProps {
  id: string
  lemma: string
  word: string
  definition: string
  sentence: string
  gender?: string
  phonetics?: string
  pos?: string
  level?: string
  conjugations?: Conjugations
  examples?: string[]
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

  // Common content - same for both variants
  const renderContent = () => (
    <>
      {/* Header: Lemma with gender and phonetics */}
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-baseline gap-2 flex-wrap">
          {gender && (
            <span className="text-sm font-medium text-text-dim">{gender}</span>
          )}
          <span className="text-lg font-semibold text-foreground">{lemma}</span>
          {phonetics && (
            <span className="text-sm text-text-dim font-mono">{phonetics}</span>
          )}
          {variant === 'list' && word.toLowerCase() !== lemma.toLowerCase() && (
            <span className="text-sm text-text-dim">({word})</span>
          )}
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {(count ?? 0) > 1 && (
            <span className="text-sm font-medium text-vocab bg-vocab/20 px-2 py-1 rounded">
              x{count}
            </span>
          )}
          {onDelete && (
            <button
              onClick={() => onDelete(id)}
              className="btn-remove"
              title="Remove from vocabulary"
            >
              −
            </button>
          )}
        </div>
      </div>

      {/* Metadata badges: POS + Level */}
      <div className="flex items-center gap-2 mb-2 flex-wrap">
        {pos && (
          <span className="text-xs font-medium bg-accent/20 text-accent px-1 py-0.5 rounded">
            {pos}
          </span>
        )}
        {level && (
          <span className={`text-xs font-medium px-0.5 py-0.5 rounded ${getLevelColor(level)}`}>
            {level}
          </span>
        )}
      </div>

      {/* Definition */}
      <p className="text-sm text-foreground mb-2">{definition}</p>

      {/* Conjugations (verbs) or Declensions (nouns) */}
      {hasConjugations && (
        <div className="text-xs text-text-dim mb-2 bg-card-hover rounded p-2">
          {isVerb ? (
            <>
              {[conjugations?.present, conjugations?.past, conjugations?.participle]
                .filter(Boolean)
                .join(' - ')}
              {conjugations?.auxiliary && ` (${conjugations.auxiliary})`}
            </>
          ) : (
            [
              conjugations?.genitive && `Gen: ${conjugations.genitive}`,
              conjugations?.plural && `Pl: ${conjugations.plural}`
            ]
              .filter(Boolean)
              .join(' | ')
          )}
        </div>
      )}

      {/* Examples - always collapsible */}
      <div className={`text-xs text-text-dim pt-2 ${variant === 'card' ? 'mb-4' : 'mb-1'}`}>
        <button
          type="button"
          className="font-medium text-accent cursor-pointer hover:underline bg-transparent border-none p-1 text-xs"
          onClick={toggleExamples}
        >
          Examples <span className="text-[0.5rem]">{examplesExpanded ? '▼' : '▶'}</span>
        </button>
        {examplesExpanded && (
          <div className="mt-1 space-y-0.5">
            <div className="italic">• {sentence}</div>
            {examples?.slice(0, 3).map((example, idx) => (
              <div key={idx} className="italic">• {example}</div>
            ))}
          </div>
        )}
      </div>

      {/* Footer: Article link + Date */}
      {showArticleLink && articleId && (
        <div className="mt-auto pt-2 flex items-center justify-between text-xs">
          <Link
            href={`/articles/${articleId}`}
            className="text-accent hover:text-accent/80 underline"
          >
            View in Article
          </Link>
          {createdAt && (
            <span className="text-text-dim">
              {new Date(createdAt).toLocaleDateString()}
            </span>
          )}
        </div>
      )}
    </>
  )

  // Container varies by variant
  if (variant === 'card') {
    return (
      <div className="bg-background rounded-lg p-5 border border-border-card hover:border-vocab/50 transition-colors flex flex-col">
        {renderContent()}
      </div>
    )
  }

  // List variant
  return (
    <div className="p-4 bg-background rounded-lg">
      {renderContent()}
    </div>
  )
}
