import { calculatePagination, type PaginationInput, type PaginationResult } from '@opad/libs'

export function usePagination(props: PaginationInput): PaginationResult {
  return calculatePagination(props)
}
