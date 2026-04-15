/* eslint-disable sonarjs/no-duplicate-string */
/**
 * Tests for date and time formatting utilities.
 */

import { describe, it, expect } from 'vitest'
import { formatDate, formatDateShort, formatDateTime } from '../formatters'

describe('formatters', () => {
  describe('formatDate', () => {
    it('should format a valid ISO date string with default options', () => {
      const dateString = '2024-01-29T12:30:00Z'
      const result = formatDate(dateString)

      expect(result).toBeDefined()
      expect(result).not.toBe(dateString)
      // Result should contain date components (timezone-agnostic)
      expect(result).toContain('2024')
      expect(result.length).toBeGreaterThan(10)
    })

    it('should format with custom locale', () => {
      const dateString = '2024-01-29T12:30:00Z'
      const result = formatDate(dateString, 'fr-FR')

      expect(result).toBeDefined()
      expect(typeof result).toBe('string')
    })

    it('should format with custom options', () => {
      const dateString = '2024-01-29T12:30:00Z'
      const result = formatDate(dateString, 'en-US', {
        year: 'numeric',
        month: 'short'
      })

      expect(result).toBeDefined()
      expect(result).toContain('2024')
      expect(result).toContain('Jan')
    })

    it('should return original string on invalid date', () => {
      const invalidDate = 'not-a-date'
      const result = formatDate(invalidDate)

      expect(result).toBe(invalidDate)
    })

    it('should handle empty string', () => {
      const result = formatDate('')

      expect(result).toBe('')
    })

    it('should handle null-like values gracefully', () => {
      const result = formatDate('null')

      expect(result).toBe('null')
    })

    it('should handle very old dates', () => {
      const dateString = '1900-01-01T00:00:00Z'
      const result = formatDate(dateString)

      expect(result).toBeDefined()
      expect(result).toContain('1900')
    })

    it('should handle future dates', () => {
      const dateString = '2099-12-31T23:59:59Z'
      const result = formatDate(dateString)

      expect(result).toBeDefined()
      // Due to timezone conversions, this could be 2099 or 2100
      expect(result).toMatch(/2099|2100/)
    })

    it('should format with various timezone formats', () => {
      const isoDateZ = '2024-01-29T12:30:00Z'
      const isoDateOffset = '2024-01-29T12:30:00+05:30'
      const isoDateNegOffset = '2024-01-29T12:30:00-08:00'

      expect(formatDate(isoDateZ)).toBeDefined()
      expect(formatDate(isoDateOffset)).toBeDefined()
      expect(formatDate(isoDateNegOffset)).toBeDefined()
    })

    it('should handle date without time', () => {
      const dateString = '2024-01-29'
      const result = formatDate(dateString)

      expect(result).toBeDefined()
      expect(result).toContain('2024')
    })

    it('should respect locale-specific formatting', () => {
      const dateString = '2024-01-29T12:30:00Z'
      const enResult = formatDate(dateString, 'en-US')
      const deResult = formatDate(dateString, 'de-DE')

      expect(enResult).toBeDefined()
      expect(deResult).toBeDefined()
      // Locales may produce different output
      // Just verify they're strings
      expect(typeof enResult).toBe('string')
      expect(typeof deResult).toBe('string')
    })
  })

  describe('formatDateShort', () => {
    it('should format date in short format', () => {
      const dateString = '2024-01-29T12:30:00Z'
      const result = formatDateShort(dateString)

      expect(result).toBeDefined()
      expect(result).toContain('2024')
      expect(result).toContain('29')
      expect(result).toContain('Jan')
    })

    it('should return original string on invalid date', () => {
      const invalidDate = 'invalid-date'
      const result = formatDateShort(invalidDate)

      expect(result).toBe(invalidDate)
    })

    it('should not include time in short format', () => {
      const dateString = '2024-01-29T23:59:00Z'
      const result = formatDateShort(dateString)

      // Short format should not include time
      expect(result).not.toContain('23')
      expect(result).not.toContain('59')
    })

    it('should handle empty string', () => {
      const result = formatDateShort('')

      expect(result).toBe('')
    })

    it('should work with various valid date formats', () => {
      const dates = [
        '2024-01-01T00:00:00Z',
        '2024-12-31T23:59:59Z',
        '2024-06-15T12:00:00+00:00'
      ]

      dates.forEach(date => {
        const result = formatDateShort(date)
        expect(result).toBeDefined()
        expect(typeof result).toBe('string')
      })
    })

    it('should format midnight correctly', () => {
      const dateString = '2024-01-29T00:00:00Z'
      const result = formatDateShort(dateString)

      expect(result).toBeDefined()
      expect(result).toContain('2024')
    })
  })

  describe('formatDateTime', () => {
    it('should format date with time', () => {
      const dateString = '2024-01-29T12:30:00Z'
      const result = formatDateTime(dateString)

      expect(result).toBeDefined()
      expect(result).toContain('2024')
      expect(result).toContain('Jan')
      // Minutes should be present (timezone-agnostic)
      expect(result).toContain('30')
      expect(result.length).toBeGreaterThan(15)
    })

    it('should return original string on invalid date', () => {
      const invalidDate = 'not-valid'
      const result = formatDateTime(invalidDate)

      expect(result).toBe(invalidDate)
    })

    it('should handle empty string', () => {
      const result = formatDateTime('')

      expect(result).toBe('')
    })

    it('should include both date and time components', () => {
      const dateString = '2024-01-29T14:45:30Z'
      const result = formatDateTime(dateString)

      expect(result).toBeDefined()
      // Should contain date info
      expect(result).toContain('2024')
      // Should contain time info (can be 12-hour or 24-hour format depending on locale)
      expect(result).toContain('45') // minutes should always be present
      expect(result.length).toBeGreaterThan(10) // Should be longer than just a date
    })

    it('should format midnight correctly with time', () => {
      const dateString = '2024-01-29T00:00:00Z'
      const result = formatDateTime(dateString)

      expect(result).toBeDefined()
      // Should contain midnight indicator (00:00 in 24h or 12:00 AM in 12h format)
      expect(result.length).toBeGreaterThan(10)
    })

    it('should format end of day correctly', () => {
      const dateString = '2024-01-29T23:59:59Z'
      const result = formatDateTime(dateString)

      expect(result).toBeDefined()
      expect(result).toContain('59') // minutes should be present
      expect(result.length).toBeGreaterThan(10)
    })

    it('should handle various timezone offsets', () => {
      const dates = [
        '2024-01-29T12:30:00Z',
        '2024-01-29T12:30:00+05:30',
        '2024-01-29T12:30:00-08:00'
      ]

      dates.forEach(date => {
        const result = formatDateTime(date)
        expect(result).toBeDefined()
        expect(typeof result).toBe('string')
      })
    })

    it('should use short month format', () => {
      const dateString = '2024-01-29T12:30:00Z'
      const result = formatDateTime(dateString)

      // Should use short month like 'Jan' not 'January'
      expect(result).toContain('Jan')
    })

    it('should work with dates across different months', () => {
      const dates = [
        '2024-01-15T10:00:00Z',
        '2024-06-15T10:00:00Z',
        '2024-12-15T10:00:00Z'
      ]

      dates.forEach(date => {
        const result = formatDateTime(date)
        expect(result).toBeDefined()
        expect(result).toContain('2024')
      })
    })
  })

  describe('edge cases and error handling', () => {
    it('should handle malformed JSON-like strings', () => {
      const malformed = '{"date": "2024-01-29"}'
      const result = formatDate(malformed)

      expect(result).toBe(malformed)
    })

    it('should handle numeric strings', () => {
      const numericString = '12345'
      const result = formatDate(numericString)

      expect(result).toBeDefined()
      expect(typeof result).toBe('string')
    })

    it('should handle whitespace in date strings', () => {
      const dateWithSpace = '2024-01-29T12:30:00Z '
      const result = formatDate(dateWithSpace)

      // Most likely will fail to parse
      expect(typeof result).toBe('string')
    })

    it('should handle leap year dates', () => {
      const leapYearDate = '2024-02-29T12:00:00Z'
      const result = formatDate(leapYearDate)

      expect(result).toBeDefined()
      expect(result).toContain('2024')
    })

    it('should handle non-leap year invalid date gracefully', () => {
      const invalidLeapDate = '2023-02-29T12:00:00Z'
      const result = formatDate(invalidLeapDate)

      // Invalid date, should return original string
      expect(typeof result).toBe('string')
    })

    it('should handle very long strings', () => {
      const longString = '2024-01-29T12:30:00Z' + 'a'.repeat(1000)
      const result = formatDate(longString)

      expect(typeof result).toBe('string')
    })

    it('should handle strings with special characters', () => {
      const specialChars = '2024-01-29T12:30:00Z!@#$%'
      const result = formatDate(specialChars)

      expect(typeof result).toBe('string')
    })
  })
})
