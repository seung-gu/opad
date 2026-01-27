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
              <div className="flex items-baseline gap-2 mb-1">
                <span className="font-semibold text-gray-900 text-lg">{vocab.lemma}</span>
                {vocab.word.toLowerCase() !== vocab.lemma.toLowerCase() && (
                  <span className="text-sm text-gray-500">({vocab.word})</span>
                )}
              </div>
              <p className="text-gray-700 text-sm mb-1">{vocab.definition}</p>
              <p className="text-xs text-gray-500 italic">"{vocab.sentence}"</p>
            </div>
            <button
              onClick={() => onDelete(vocab.id)}
              className="ml-4 px-2 py-1 text-sm text-red-600 hover:text-red-800 hover:bg-red-50 rounded transition-colors"
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
