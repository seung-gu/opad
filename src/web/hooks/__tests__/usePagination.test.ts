/**
 * Tests for pagination hook.
 */

import { describe, it, expect } from 'vitest'
import { usePagination } from '../usePagination'

describe('usePagination', () => {
  describe('currentPage calculation', () => {
    it('should calculate currentPage correctly for first page', () => {
      const result = usePagination({ total: 100, limit: 10, skip: 0 })

      expect(result.currentPage).toBe(1)
    })

    it('should calculate currentPage correctly for second page', () => {
      const result = usePagination({ total: 100, limit: 10, skip: 10 })

      expect(result.currentPage).toBe(2)
    })

    it('should calculate currentPage correctly for middle page', () => {
      const result = usePagination({ total: 100, limit: 10, skip: 40 })

      expect(result.currentPage).toBe(5)
    })

    it('should calculate currentPage correctly for last page', () => {
      const result = usePagination({ total: 100, limit: 10, skip: 90 })

      expect(result.currentPage).toBe(10)
    })

    it('should handle partial page skip values', () => {
      // skip=5 with limit=10 should round down to page 1
      const result = usePagination({ total: 100, limit: 10, skip: 5 })

      expect(result.currentPage).toBe(1)
    })

    it('should handle skip greater than total', () => {
      const result = usePagination({ total: 100, limit: 10, skip: 150 })

      expect(result.currentPage).toBe(16)
    })
  })

  describe('totalPages calculation', () => {
    it('should calculate totalPages correctly for even division', () => {
      const result = usePagination({ total: 100, limit: 10, skip: 0 })

      expect(result.totalPages).toBe(10)
    })

    it('should calculate totalPages correctly with remainder', () => {
      const result = usePagination({ total: 105, limit: 10, skip: 0 })

      expect(result.totalPages).toBe(11)
    })

    it('should calculate totalPages correctly for single page', () => {
      const result = usePagination({ total: 5, limit: 10, skip: 0 })

      expect(result.totalPages).toBe(1)
    })

    it('should calculate totalPages correctly for large dataset', () => {
      const result = usePagination({ total: 10000, limit: 25, skip: 0 })

      expect(result.totalPages).toBe(400)
    })

    it('should handle zero total', () => {
      const result = usePagination({ total: 0, limit: 10, skip: 0 })

      expect(result.totalPages).toBe(0)
    })

    it('should handle very large limit', () => {
      const result = usePagination({ total: 100, limit: 1000, skip: 0 })

      expect(result.totalPages).toBe(1)
    })
  })

  describe('hasNextPage flag', () => {
    it('should be true when more items exist', () => {
      const result = usePagination({ total: 100, limit: 10, skip: 0 })

      expect(result.hasNextPage).toBe(true)
    })

    it('should be false on last page', () => {
      const result = usePagination({ total: 100, limit: 10, skip: 90 })

      expect(result.hasNextPage).toBe(false)
    })

    it('should be false when skip + limit equals total', () => {
      const result = usePagination({ total: 100, limit: 10, skip: 90 })

      expect(result.hasNextPage).toBe(false)
    })

    it('should be false for empty result', () => {
      const result = usePagination({ total: 0, limit: 10, skip: 0 })

      expect(result.hasNextPage).toBe(false)
    })

    it('should be true when skip is in middle of range', () => {
      const result = usePagination({ total: 100, limit: 10, skip: 50 })

      expect(result.hasNextPage).toBe(true)
    })

    it('should be false when skip + limit > total', () => {
      const result = usePagination({ total: 100, limit: 10, skip: 95 })

      expect(result.hasNextPage).toBe(false)
    })
  })

  describe('hasPrevPage flag', () => {
    it('should be false on first page', () => {
      const result = usePagination({ total: 100, limit: 10, skip: 0 })

      expect(result.hasPrevPage).toBe(false)
    })

    it('should be true on second page', () => {
      const result = usePagination({ total: 100, limit: 10, skip: 10 })

      expect(result.hasPrevPage).toBe(true)
    })

    it('should be true on middle page', () => {
      const result = usePagination({ total: 100, limit: 10, skip: 50 })

      expect(result.hasPrevPage).toBe(true)
    })

    it('should be true on last page', () => {
      const result = usePagination({ total: 100, limit: 10, skip: 90 })

      expect(result.hasPrevPage).toBe(true)
    })

    it('should be false for empty result', () => {
      const result = usePagination({ total: 0, limit: 10, skip: 0 })

      expect(result.hasPrevPage).toBe(false)
    })
  })

  describe('nextSkip calculation', () => {
    it('should calculate nextSkip correctly when next page exists', () => {
      const result = usePagination({ total: 100, limit: 10, skip: 0 })

      expect(result.nextSkip).toBe(10)
    })

    it('should remain same skip when on last page', () => {
      const result = usePagination({ total: 100, limit: 10, skip: 90 })

      expect(result.nextSkip).toBe(90)
    })

    it('should increment skip by limit amount', () => {
      const result = usePagination({ total: 100, limit: 25, skip: 50 })

      expect(result.nextSkip).toBe(75)
    })

    it('should work with large limit values', () => {
      const result = usePagination({ total: 10000, limit: 500, skip: 5000 })

      expect(result.nextSkip).toBe(5500)
    })

    it('should not exceed total items', () => {
      const result = usePagination({ total: 100, limit: 10, skip: 95 })

      // Can't go past 100 items, so nextSkip stays at 95
      expect(result.nextSkip).toBe(95)
    })
  })

  describe('prevSkip calculation', () => {
    it('should be zero on first page', () => {
      const result = usePagination({ total: 100, limit: 10, skip: 0 })

      expect(result.prevSkip).toBe(0)
    })

    it('should calculate prevSkip correctly on second page', () => {
      const result = usePagination({ total: 100, limit: 10, skip: 10 })

      expect(result.prevSkip).toBe(0)
    })

    it('should calculate prevSkip correctly on third page', () => {
      const result = usePagination({ total: 100, limit: 10, skip: 20 })

      expect(result.prevSkip).toBe(10)
    })

    it('should calculate prevSkip correctly on last page', () => {
      const result = usePagination({ total: 100, limit: 10, skip: 90 })

      expect(result.prevSkip).toBe(80)
    })

    it('should decrement skip by limit amount', () => {
      const result = usePagination({ total: 100, limit: 25, skip: 75 })

      expect(result.prevSkip).toBe(50)
    })

    it('should never be negative', () => {
      const result = usePagination({ total: 100, limit: 10, skip: 5 })

      expect(result.prevSkip).toBeGreaterThanOrEqual(0)
    })
  })

  describe('getSkipForPage helper function', () => {
    it('should calculate skip for page 1', () => {
      const result = usePagination({ total: 100, limit: 10, skip: 0 })

      expect(result.getSkipForPage(1)).toBe(0)
    })

    it('should calculate skip for page 2', () => {
      const result = usePagination({ total: 100, limit: 10, skip: 0 })

      expect(result.getSkipForPage(2)).toBe(10)
    })

    it('should calculate skip for page 5', () => {
      const result = usePagination({ total: 100, limit: 10, skip: 0 })

      expect(result.getSkipForPage(5)).toBe(40)
    })

    it('should calculate skip for last page', () => {
      const result = usePagination({ total: 100, limit: 10, skip: 0 })

      expect(result.getSkipForPage(10)).toBe(90)
    })

    it('should clamp to page 1 for negative page numbers', () => {
      const result = usePagination({ total: 100, limit: 10, skip: 0 })

      expect(result.getSkipForPage(-5)).toBe(0)
    })

    it('should clamp to last page for page numbers exceeding total', () => {
      const result = usePagination({ total: 100, limit: 10, skip: 0 })

      expect(result.getSkipForPage(100)).toBe(90)
    })

    it('should clamp to last page for page 0', () => {
      const result = usePagination({ total: 100, limit: 10, skip: 0 })

      expect(result.getSkipForPage(0)).toBe(0)
    })

    it('should work with different limit values', () => {
      const result = usePagination({ total: 200, limit: 25, skip: 0 })

      expect(result.getSkipForPage(1)).toBe(0)
      expect(result.getSkipForPage(2)).toBe(25)
      expect(result.getSkipForPage(3)).toBe(50)
      expect(result.getSkipForPage(8)).toBe(175)
    })

    it('should work when total pages is 1', () => {
      const result = usePagination({ total: 5, limit: 10, skip: 0 })

      expect(result.getSkipForPage(1)).toBe(0)
      expect(result.getSkipForPage(5)).toBe(0)
    })

    it('should handle large page numbers', () => {
      const result = usePagination({ total: 10000, limit: 50, skip: 0 })

      expect(result.getSkipForPage(1000)).toBe((200 - 1) * 50) // Clamped to last page
    })
  })

  describe('invalid limit handling', () => {
    it('should return safe defaults when limit is zero', () => {
      const result = usePagination({ total: 100, limit: 0, skip: 0 })

      expect(result.currentPage).toBe(1)
      expect(result.totalPages).toBe(0)
      expect(result.hasNextPage).toBe(false)
      expect(result.hasPrevPage).toBe(false)
      expect(result.nextSkip).toBe(0)
      expect(result.prevSkip).toBe(0)
    })

    it('should return safe defaults when limit is negative', () => {
      const result = usePagination({ total: 100, limit: -10, skip: 0 })

      expect(result.currentPage).toBe(1)
      expect(result.totalPages).toBe(0)
      expect(result.hasNextPage).toBe(false)
      expect(result.hasPrevPage).toBe(false)
    })

    it('getSkipForPage should return 0 for invalid limit', () => {
      const result = usePagination({ total: 100, limit: 0, skip: 0 })

      expect(result.getSkipForPage(5)).toBe(0)
    })
  })

  describe('edge cases', () => {
    it('should handle skip equal to total', () => {
      const result = usePagination({ total: 100, limit: 10, skip: 100 })

      expect(result.currentPage).toBe(11)
      expect(result.hasNextPage).toBe(false)
      expect(result.hasPrevPage).toBe(true)
    })

    it('should handle very small limit', () => {
      const result = usePagination({ total: 100, limit: 1, skip: 0 })

      expect(result.totalPages).toBe(100)
      expect(result.currentPage).toBe(1)
      expect(result.nextSkip).toBe(1)
    })

    it('should handle limit equal to total', () => {
      const result = usePagination({ total: 100, limit: 100, skip: 0 })

      expect(result.totalPages).toBe(1)
      expect(result.currentPage).toBe(1)
      expect(result.hasNextPage).toBe(false)
    })

    it('should handle decimal skip values by flooring', () => {
      const result = usePagination({ total: 100, limit: 10, skip: 25 })

      expect(result.currentPage).toBe(3) // floor(25/10) + 1
    })

    it('should handle decimal total values by ceiling', () => {
      const result = usePagination({ total: 99.5, limit: 10, skip: 0 })

      expect(result.totalPages).toBe(10)
    })

    it('should be consistent across multiple calls', () => {
      const input = { total: 100, limit: 10, skip: 50 }

      const result1 = usePagination(input)
      const result2 = usePagination(input)

      expect(result1.currentPage).toBe(result2.currentPage)
      expect(result1.totalPages).toBe(result2.totalPages)
      expect(result1.hasNextPage).toBe(result2.hasNextPage)
      expect(result1.hasPrevPage).toBe(result2.hasPrevPage)
    })
  })

  describe('integration scenarios', () => {
    it('should navigate through all pages correctly', () => {
      let result = usePagination({ total: 100, limit: 10, skip: 0 })
      expect(result.currentPage).toBe(1)
      expect(result.hasNextPage).toBe(true)

      // Move to next page
      result = usePagination({ total: 100, limit: 10, skip: result.nextSkip })
      expect(result.currentPage).toBe(2)
      expect(result.hasNextPage).toBe(true)
      expect(result.hasPrevPage).toBe(true)

      // Move to last page
      result = usePagination({ total: 100, limit: 10, skip: 90 })
      expect(result.currentPage).toBe(10)
      expect(result.hasNextPage).toBe(false)
      expect(result.hasPrevPage).toBe(true)

      // Go back
      result = usePagination({ total: 100, limit: 10, skip: result.prevSkip })
      expect(result.currentPage).toBe(9)
    })

    it('should handle jumping to specific page', () => {
      const pagination = usePagination({ total: 100, limit: 10, skip: 0 })

      const skipForPage5 = pagination.getSkipForPage(5)
      const result = usePagination({ total: 100, limit: 10, skip: skipForPage5 })

      expect(result.currentPage).toBe(5)
    })

    it('should maintain consistency between navigation and page jumping', () => {
      const pagination = usePagination({ total: 100, limit: 10, skip: 0 })

      // Jump to page 7
      const skipPage7 = pagination.getSkipForPage(7)
      const resultJump = usePagination({ total: 100, limit: 10, skip: skipPage7 })

      // Navigate to page 7
      let result = usePagination({ total: 100, limit: 10, skip: 0 })
      for (let i = 1; i < 7; i++) {
        result = usePagination({ total: 100, limit: 10, skip: result.nextSkip })
      }

      expect(resultJump.currentPage).toBe(result.currentPage)
      expect(resultJump.currentPage).toBe(7)
    })
  })
})
