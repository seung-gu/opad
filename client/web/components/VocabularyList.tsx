'use client'

import { Vocabulary } from '@/types/article'
import VocabularyCard from './VocabularyCard'

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
          <VocabularyCard
            key={vocab.id}
            id={vocab.id}
            lemma={vocab.lemma}
            word={vocab.word}
            definition={vocab.definition}
            sentence={vocab.sentence}
            gender={vocab.gender}
            phonetics={vocab.phonetics}
            pos={vocab.pos}
            level={vocab.level}
            conjugations={vocab.conjugations}
            examples={vocab.examples}
            variant="list"
            onDelete={onDelete}
          />
        ))}
      </div>
    </div>
  )
}
