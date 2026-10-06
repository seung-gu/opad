'use client'

import { Vocabulary } from '@opad/libs'
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
    <section className="border-t border-border-card pt-8">
      <div className="flex items-baseline justify-between">
        <h2 className="font-serif text-[19px] italic text-text-strong">Vocabulary</h2>
        <span className="text-[12px] text-text-dim">
          {vocabularies.length} {vocabularies.length === 1 ? 'word' : 'words'} from this article
        </span>
      </div>
      <ul className="mt-2">
        {vocabularies.map((vocab) => (
          <li key={vocab.id} className="border-b border-border-card last:border-b-0">
            <VocabularyCard
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
          </li>
        ))}
      </ul>
    </section>
  )
}
