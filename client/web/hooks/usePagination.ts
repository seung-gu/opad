/**
 * Hook for pagination calculations and state management.
 *
 * Provides:
 * - Current page calculation
 * - Total pages calculation
 * - Next/previous page availability
 * - Helper functions for navigation
 *
 * @example
 * ```typescript
 * const { currentPage, totalPages, hasNextPage, hasPrevPage } = usePagination({
 *   total: 100,
 *   limit: 10,
 *   skip: 20
 * })
 * // currentPage = 3, totalPages = 10, hasNextPage = true, hasPrevPage = true
 * ```
 */

interface UsePaginationProps {
  total: number
  limit: number
  skip: number
}

interface UsePaginationResult {
  currentPage: number
  totalPages: number
  hasNextPage: boolean
  hasPrevPage: boolean
  nextSkip: number
  prevSkip: number
  getSkipForPage: (page: number) => number
}

export function usePagination({ total, limit, skip }: UsePaginationProps): UsePaginationResult {
  // Guard against invalid limit
  if (limit <= 0) {
    return {
      currentPage: 1,
      totalPages: 0,
      hasNextPage: false,
      hasPrevPage: false,
      nextSkip: 0,
      prevSkip: 0,
      getSkipForPage: () => 0
    }
  }

  // Calculate current page (1-indexed)
  const currentPage = Math.floor(skip / limit) + 1

  // Calculate total pages
  const totalPages = Math.ceil(total / limit)

  // Check if next/previous pages exist
  const hasNextPage = skip + limit < total
  const hasPrevPage = skip > 0

  // Calculate skip values for next/previous pages
  const nextSkip = hasNextPage ? skip + limit : skip
  const prevSkip = hasPrevPage ? Math.max(0, skip - limit) : 0

  // Helper function to get skip value for a specific page
  const getSkipForPage = (page: number): number => {
    const targetPage = Math.max(1, Math.min(page, totalPages))
    return (targetPage - 1) * limit
  }

  return {
    currentPage,
    totalPages,
    hasNextPage,
    hasPrevPage,
    nextSkip,
    prevSkip,
    getSkipForPage
  }
}
