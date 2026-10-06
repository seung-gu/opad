import { VocabularyCount } from '@opad/libs'

export type VocabularySort = 'frequency' | 'recent' | 'alphabetical'

export const VOCABULARY_SORTS: { value: VocabularySort; label: string }[] = [
  { value: 'frequency', label: 'Frequency' },
  { value: 'recent', label: 'Recent' },
  { value: 'alphabetical', label: 'A–Z' },
]

/**
 * Orders vocabulary entries for display.
 *
 * - frequency: most saved first, ties broken alphabetically (mirrors the
 *   backend's own `count desc, lemma asc`, so it is the default)
 * - recent: most recently saved first. `created_at` on an aggregated entry is
 *   the latest save for that lemma, not the first one
 * - alphabetical: by lemma, accent-insensitive so German umlauts sort with
 *   their base letter rather than after z
 *
 * Returns a new array; the input is left alone.
 */
export function sortVocabularies(
  entries: VocabularyCount[],
  sort: VocabularySort
): VocabularyCount[] {
  const byLemma = (a: VocabularyCount, b: VocabularyCount) =>
    a.lemma.localeCompare(b.lemma, undefined, { sensitivity: 'base' })

  const sorted = [...entries]

  if (sort === 'alphabetical') {
    return sorted.sort(byLemma)
  }

  if (sort === 'recent') {
    return sorted.sort((a, b) => {
      const diff = Date.parse(b.created_at) - Date.parse(a.created_at)
      // Unparseable or identical timestamps fall back to a stable order
      return Number.isNaN(diff) || diff === 0 ? byLemma(a, b) : diff
    })
  }

  return sorted.sort((a, b) => b.count - a.count || byLemma(a, b))
}
