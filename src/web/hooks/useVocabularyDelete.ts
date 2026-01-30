import { fetchWithAuth } from '@/lib/api'

/**
 * Custom hook for deleting vocabulary entries.
 *
 * Provides a reusable deleteVocabulary function that:
 * - Makes DELETE request to the vocabulary API
 * - Handles error responses with detailed messages
 * - Throws errors for the caller to handle (e.g., update UI state)
 *
 * @example
 * ```typescript
 * const { deleteVocabulary } = useVocabularyDelete()
 *
 * try {
 *   await deleteVocabulary(vocabId)
 *   // Update local state on success
 *   setVocabularies(prev => prev.filter(v => v.id !== vocabId))
 * } catch (error) {
 *   // Handle error in UI
 *   setError(error.message)
 * }
 * ```
 */
export function useVocabularyDelete() {
  /**
   * Delete a vocabulary entry by ID.
   *
   * @param vocabId - The vocabulary ID to delete
   * @throws Error with message if deletion fails
   */
  const deleteVocabulary = async (vocabId: string): Promise<void> => {
    const response = await fetchWithAuth(`/api/dictionary/vocabularies/${vocabId}`, {
      method: 'DELETE'
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.error || errorData.detail || 'Failed to delete vocabulary')
    }
  }

  return { deleteVocabulary }
}
