'use client'

import { Vocabulary } from '@/types/article'

interface VocabularyListProps {
  vocabularies: Vocabulary[]
  onDelete: (vocabId: string) => void
}

export default function VocabularyList({ vocabularies, onDelete }: VocabularyListProps) {
  if (vocabularies.length === 0) {
    return null
  }

  // Helper function for CEFR level badge color
  const getLevelColor = (level?: string) => {
    if (!level) return 'bg-gray-100 text-gray-600'
    if (level.startsWith('A')) return 'bg-green-100 text-green-700'
    if (level.startsWith('B')) return 'bg-yellow-100 text-yellow-700'
    return 'bg-red-100 text-red-700' // C1, C2
  }

  return (
    <div className="mt-8 bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <h2 className="text-2xl font-bold text-gray-900 mb-4">Vocabulary</h2>
      <div className="space-y-3">
        {vocabularies.map((vocab) => (
          <div
            key={vocab.id}
            className="flex items-start justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
          >
            <div className="flex-1">
              {/* Lemma with gender */}
              <div className="flex items-baseline gap-2 mb-1 flex-wrap">
                {vocab.gender && (
                  <span className="text-sm font-medium text-gray-500">{vocab.gender}</span>
                )}
                <span className="font-semibold text-gray-900 text-lg">{vocab.lemma}</span>
                {vocab.word.toLowerCase() !== vocab.lemma.toLowerCase() && (
                  <span className="text-sm text-gray-500">({vocab.word})</span>
                )}
              </div>

              {/* Metadata badges: POS + Level */}
              <div className="flex items-center gap-2 mb-1 flex-wrap">
                {vocab.pos && (
                  <span className="text-xs font-medium bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
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
              <p className="text-gray-700 text-sm mb-1">{vocab.definition}</p>

              {/* Conjugations (if verb) */}
              {vocab.conjugations && (vocab.conjugations.present || vocab.conjugations.past || vocab.conjugations.perfect) && (
                <div className="text-xs text-gray-600 mb-1 bg-gray-100 rounded p-2">
                  {[vocab.conjugations.present, vocab.conjugations.past, vocab.conjugations.perfect]
                    .filter(Boolean)
                    .join(' - ')}
                </div>
              )}

              {/* Example sentence */}
              <p className="text-xs text-gray-500 italic">"{vocab.sentence}"</p>
            </div>
            <button
              onClick={() => onDelete(vocab.id)}
              className="ml-4 px-2 py-1 text-sm text-red-600 hover:text-red-800 hover:bg-red-50 rounded transition-colors flex-shrink-0"
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
