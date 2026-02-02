'use client'

import { Vocabulary } from '@/types/article'
import { getLevelColor } from '@/lib/styleHelpers'

interface VocabularyListProps {
  vocabularies: Vocabulary[]
  onDelete: (vocabId: string) => void
}

export default function VocabularyList({ vocabularies, onDelete }: VocabularyListProps) {
  if (vocabularies.length === 0) {
    return null
  }

  return (
    <div className="mt-8 bg-card rounded-lg border border-border-card p-6">
      <h2 className="text-2xl font-bold text-foreground mb-4">Vocabulary</h2>
      <div className="space-y-3">
        {vocabularies.map((vocab) => (
          <div
            key={vocab.id}
            className="flex items-start justify-between p-3 bg-background rounded-lg hover:bg-card-hover transition-colors"
          >
            <div className="flex-1">
              {/* Lemma with gender */}
              <div className="flex items-baseline gap-2 mb-1 flex-wrap">
                {vocab.gender && (
                  <span className="text-sm font-medium text-text-dim">{vocab.gender}</span>
                )}
                <span className="font-semibold text-foreground text-lg">{vocab.lemma}</span>
                {vocab.word.toLowerCase() !== vocab.lemma.toLowerCase() && (
                  <span className="text-sm text-text-dim">({vocab.word})</span>
                )}
              </div>

              {/* Metadata badges: POS + Level */}
              <div className="flex items-center gap-2 mb-1 flex-wrap">
                {vocab.pos && (
                  <span className="text-xs font-medium bg-accent/20 text-accent px-2 py-0.5 rounded">
                    {vocab.pos}
                  </span>
                )}
                {vocab.level && (
                  <span className={`text-xs font-medium px-2 py-0.5 rounded ${getLevelColor(vocab.level)}`}>
                    {vocab.level}
                  </span>
                )}
              </div>

              {/* Definition */}
              <p className="text-foreground text-sm mb-1">{vocab.definition}</p>

              {/* Conjugations (if verb) */}
              {vocab.conjugations && (vocab.conjugations.present || vocab.conjugations.past || vocab.conjugations.perfect) && (
                <div className="text-xs text-text-dim mb-1 bg-card-hover rounded p-2">
                  {[vocab.conjugations.present, vocab.conjugations.past, vocab.conjugations.perfect]
                    .filter(Boolean)
                    .join(' - ')}
                </div>
              )}

              {/* Example sentence */}
              <p className="text-xs text-text-dim italic">"{vocab.sentence}"</p>
            </div>
            <button
              onClick={() => onDelete(vocab.id)}
              className="btn-remove ml-4 flex-shrink-0"
              title="Remove from vocabulary"
            >
              −
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
