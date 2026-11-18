/**
 * Tests for vocabulary ordering.
 */

import { describe, it, expect } from 'vitest'
import { VocabularyCount } from '@opad/libs'
import { sortVocabularies } from '../vocabularySort'

function entry(lemma: string, count: number, created_at: string): VocabularyCount {
  return {
    id: lemma,
    article_id: 'a1',
    article_ids: ['a1'],
    word: lemma,
    lemma,
    definition: 'd',
    sentence: 's',
    language: 'German',
    created_at,
    count,
  } as VocabularyCount
}

const ENTRIES: VocabularyCount[] = [
  entry('Zeitung', 1, '2026-01-03T00:00:00Z'),
  entry('Abend', 5, '2026-01-01T00:00:00Z'),
  entry('Übung', 5, '2026-01-02T00:00:00Z'),
]

describe('sortVocabularies', () => {
  describe('alphabetical', () => {
    it('sorts by lemma', () => {
      const result = sortVocabularies(ENTRIES, 'alphabetical').map(e => e.lemma)

      expect(result).toEqual(['Abend', 'Übung', 'Zeitung'])
    })

    it('sorts umlauts with their base letter, not after z', () => {
      const result = sortVocabularies(
        [entry('Zebra', 1, '2026-01-01T00:00:00Z'), entry('Übung', 1, '2026-01-01T00:00:00Z')],
        'alphabetical'
      ).map(e => e.lemma)

      expect(result).toEqual(['Übung', 'Zebra'])
    })
  })

  describe('recent', () => {
    it('puts the most recently saved first', () => {
      const result = sortVocabularies(ENTRIES, 'recent').map(e => e.lemma)

      expect(result).toEqual(['Zeitung', 'Übung', 'Abend'])
    })

    it('falls back to lemma order when timestamps are identical', () => {
      const same = '2026-01-01T00:00:00Z'
      const result = sortVocabularies(
        [entry('beta', 1, same), entry('alpha', 1, same)],
        'recent'
      ).map(e => e.lemma)

      expect(result).toEqual(['alpha', 'beta'])
    })

    it('does not drop entries with an unparseable timestamp', () => {
      const result = sortVocabularies(
        [entry('beta', 1, 'not-a-date'), entry('alpha', 1, '2026-01-01T00:00:00Z')],
        'recent'
      ).map(e => e.lemma)

      expect(result).toHaveLength(2)
      expect(result).toContain('alpha')
      expect(result).toContain('beta')
    })
  })

  describe('frequency', () => {
    it('puts the most saved first', () => {
      const result = sortVocabularies(ENTRIES, 'frequency').map(e => e.lemma)

      expect(result[0]).not.toBe('Zeitung')
      expect(result[2]).toBe('Zeitung')
    })

    it('breaks ties alphabetically', () => {
      const result = sortVocabularies(ENTRIES, 'frequency').map(e => e.lemma)

      expect(result).toEqual(['Abend', 'Übung', 'Zeitung'])
    })
  })

  it('leaves the input array untouched', () => {
    const input = [...ENTRIES]
    const before = input.map(e => e.lemma)

    sortVocabularies(input, 'alphabetical')

    expect(input.map(e => e.lemma)).toEqual(before)
  })
})
