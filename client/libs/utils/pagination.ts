export interface PaginationInput {
  total: number
  limit: number
  skip: number
}

export interface PaginationResult {
  currentPage: number
  totalPages: number
  hasNextPage: boolean
  hasPrevPage: boolean
  nextSkip: number
  prevSkip: number
  getSkipForPage: (page: number) => number
}

export function calculatePagination({ total, limit, skip }: PaginationInput): PaginationResult {
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

  const currentPage = Math.floor(skip / limit) + 1
  const totalPages = Math.ceil(total / limit)
  const hasNextPage = skip + limit < total
  const hasPrevPage = skip > 0
  const nextSkip = hasNextPage ? skip + limit : skip
  const prevSkip = hasPrevPage ? Math.max(0, skip - limit) : 0

  const getSkipForPage = (page: number): number => {
    const targetPage = Math.max(1, Math.min(page, totalPages))
    return (targetPage - 1) * limit
  }

  return { currentPage, totalPages, hasNextPage, hasPrevPage, nextSkip, prevSkip, getSkipForPage }
}
