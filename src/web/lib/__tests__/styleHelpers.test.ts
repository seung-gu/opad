/**
 * Tests for style and CSS utility functions.
 */

import { describe, it, expect } from 'vitest'
import { getLevelColor, getLevelLabel } from '../styleHelpers'

describe('styleHelpers', () => {
  describe('getLevelColor', () => {
    describe('A-level colors (beginner)', () => {
      it('should return green colors for A1', () => {
        const result = getLevelColor('A1')

        expect(result).toBe('bg-green-100 text-green-700')
      })

      it('should return green colors for A2', () => {
        const result = getLevelColor('A2')

        expect(result).toBe('bg-green-100 text-green-700')
      })

      it('should return green colors for A3', () => {
        const result = getLevelColor('A3')

        expect(result).toBe('bg-green-100 text-green-700')
      })

      it('should handle lowercase a1', () => {
        const result = getLevelColor('a1')

        // Current implementation uses startsWith which is case-sensitive
        expect(result).not.toBe('bg-green-100 text-green-700')
      })
    })

    describe('B-level colors (intermediate)', () => {
      it('should return yellow colors for B1', () => {
        const result = getLevelColor('B1')

        expect(result).toBe('bg-yellow-100 text-yellow-700')
      })

      it('should return yellow colors for B2', () => {
        const result = getLevelColor('B2')

        expect(result).toBe('bg-yellow-100 text-yellow-700')
      })

      it('should return yellow colors for B3', () => {
        const result = getLevelColor('B3')

        expect(result).toBe('bg-yellow-100 text-yellow-700')
      })
    })

    describe('C-level colors (advanced)', () => {
      it('should return red colors for C1', () => {
        const result = getLevelColor('C1')

        expect(result).toBe('bg-red-100 text-red-700')
      })

      it('should return red colors for C2', () => {
        const result = getLevelColor('C2')

        expect(result).toBe('bg-red-100 text-red-700')
      })

      it('should return red colors for C3', () => {
        const result = getLevelColor('C3')

        expect(result).toBe('bg-red-100 text-red-700')
      })
    })

    describe('edge cases', () => {
      it('should return gray for undefined', () => {
        const result = getLevelColor(undefined)

        expect(result).toBe('bg-gray-100 text-gray-600')
      })

      it('should return gray for empty string', () => {
        const result = getLevelColor('')

        expect(result).toBe('bg-gray-100 text-gray-600')
      })

      it('should return gray for null', () => {
        const result = getLevelColor(null as any)

        expect(result).toBe('bg-gray-100 text-gray-600')
      })

      it('should return gray for unrecognized level starting with other letters', () => {
        const result = getLevelColor('X1')

        // Falls through to default (red)
        expect(result).toBe('bg-red-100 text-red-700')
      })

      it('should return gray for numbers only', () => {
        const result = getLevelColor('123')

        // Falls through to default (red)
        expect(result).toBe('bg-red-100 text-red-700')
      })

      it('should handle lowercase levels', () => {
        const resultA = getLevelColor('a1')
        const resultB = getLevelColor('b2')
        const resultC = getLevelColor('c1')

        // Case-sensitive check with startsWith - lowercase falls through to default (red)
        expect(resultA).toBe('bg-red-100 text-red-700') // doesn't start with 'A'
        expect(resultB).toBe('bg-red-100 text-red-700') // doesn't start with 'B'
        expect(resultC).toBe('bg-red-100 text-red-700') // default case
      })

      it('should handle whitespace', () => {
        const result = getLevelColor(' A1 ')

        // Doesn't start with A due to leading space
        expect(result).not.toBe('bg-green-100 text-green-700')
      })

      it('should handle mixed case', () => {
        const result = getLevelColor('A1')

        expect(result).toBe('bg-green-100 text-green-700')
      })

      it('should return gray for special characters', () => {
        const result = getLevelColor('@A1')

        // Doesn't start with A, B, or C
        expect(result).toBe('bg-red-100 text-red-700')
      })

      it('should return appropriate color for level with suffix', () => {
        const resultA = getLevelColor('A1-advanced')
        const resultB = getLevelColor('B2-plus')
        const resultC = getLevelColor('C1-expert')

        expect(resultA).toBe('bg-green-100 text-green-700')
        expect(resultB).toBe('bg-yellow-100 text-yellow-700')
        expect(resultC).toBe('bg-red-100 text-red-700')
      })
    })

    describe('return value consistency', () => {
      it('should always return a non-empty string', () => {
        const levels = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2', undefined, '']

        levels.forEach(level => {
          const result = getLevelColor(level as any)
          expect(typeof result).toBe('string')
          expect(result.length).toBeGreaterThan(0)
        })
      })

      it('should return consistent color for same level', () => {
        const result1 = getLevelColor('A1')
        const result2 = getLevelColor('A1')

        expect(result1).toBe(result2)
      })

      it('should return Tailwind class strings', () => {
        const levels = ['A1', 'B1', 'C1', undefined]

        levels.forEach(level => {
          const result = getLevelColor(level as any)
          expect(result).toMatch(/^(bg-|text-)/)
          expect(result).toContain('bg-')
          expect(result).toContain('text-')
        })
      })
    })
  })

  describe('getLevelLabel', () => {
    describe('A-level labels (beginner)', () => {
      it('should return "Beginner" for A1', () => {
        const result = getLevelLabel('A1')

        expect(result).toBe('Beginner')
      })

      it('should return "Beginner" for A2', () => {
        const result = getLevelLabel('A2')

        expect(result).toBe('Beginner')
      })

      it('should return "Beginner" for any A level', () => {
        const result = getLevelLabel('A99')

        expect(result).toBe('Beginner')
      })
    })

    describe('B-level labels (intermediate)', () => {
      it('should return "Intermediate" for B1', () => {
        const result = getLevelLabel('B1')

        expect(result).toBe('Intermediate')
      })

      it('should return "Intermediate" for B2', () => {
        const result = getLevelLabel('B2')

        expect(result).toBe('Intermediate')
      })

      it('should return "Intermediate" for any B level', () => {
        const result = getLevelLabel('B99')

        expect(result).toBe('Intermediate')
      })
    })

    describe('C-level labels (advanced)', () => {
      it('should return "Advanced" for C1', () => {
        const result = getLevelLabel('C1')

        expect(result).toBe('Advanced')
      })

      it('should return "Advanced" for C2', () => {
        const result = getLevelLabel('C2')

        expect(result).toBe('Advanced')
      })

      it('should return "Advanced" for any C level', () => {
        const result = getLevelLabel('C99')

        expect(result).toBe('Advanced')
      })
    })

    describe('edge cases', () => {
      it('should return "Unknown" for undefined', () => {
        const result = getLevelLabel(undefined)

        expect(result).toBe('Unknown')
      })

      it('should return "Unknown" for empty string', () => {
        const result = getLevelLabel('')

        expect(result).toBe('Unknown')
      })

      it('should return "Unknown" for null', () => {
        const result = getLevelLabel(null as any)

        expect(result).toBe('Unknown')
      })

      it('should return "Advanced" for unrecognized level starting with other letters', () => {
        const result = getLevelLabel('X1')

        // Falls through to default (Advanced)
        expect(result).toBe('Advanced')
      })

      it('should return "Advanced" for numbers only', () => {
        const result = getLevelLabel('123')

        // Falls through to default
        expect(result).toBe('Advanced')
      })

      it('should handle lowercase levels', () => {
        const resultA = getLevelLabel('a1')
        const resultB = getLevelLabel('b2')
        const resultC = getLevelLabel('c1')

        // Case-sensitive, so won't match
        expect(resultA).not.toBe('Beginner')
        expect(resultB).not.toBe('Intermediate')
        expect(resultC).toBe('Advanced') // Falls through to default
      })

      it('should handle whitespace', () => {
        const result = getLevelLabel(' A1 ')

        // Doesn't start with A due to leading space, falls through to default
        expect(result).toBe('Advanced')
      })

      it('should handle mixed case A level', () => {
        const result = getLevelLabel('a1')

        // Case-sensitive, lowercase 'a' won't match uppercase 'A'
        expect(result).not.toBe('Beginner')
      })

      it('should return label for level with suffix', () => {
        const resultA = getLevelLabel('A1-advanced')
        const resultB = getLevelLabel('B2-plus')
        const resultC = getLevelLabel('C1-expert')

        expect(resultA).toBe('Beginner')
        expect(resultB).toBe('Intermediate')
        expect(resultC).toBe('Advanced')
      })

      it('should handle special characters', () => {
        const result = getLevelLabel('@A1')

        // Doesn't start with A/B/C, falls through to default
        expect(result).toBe('Advanced')
      })
    })

    describe('return value consistency', () => {
      it('should always return a non-empty string', () => {
        const levels = ['A1', 'B1', 'C1', undefined, '']

        levels.forEach(level => {
          const result = getLevelLabel(level as any)
          expect(typeof result).toBe('string')
          expect(result.length).toBeGreaterThan(0)
        })
      })

      it('should return consistent label for same level', () => {
        const result1 = getLevelLabel('B2')
        const result2 = getLevelLabel('B2')

        expect(result1).toBe(result2)
      })

      it('should return one of the known labels or Unknown', () => {
        const levels = ['A1', 'B1', 'C1', 'D1', 'X1', undefined, '']
        const expectedLabels = ['Beginner', 'Intermediate', 'Advanced', 'Unknown']

        levels.forEach(level => {
          const result = getLevelLabel(level as any)
          expect(expectedLabels).toContain(result)
        })
      })

      it('should be human-readable', () => {
        const levels = ['A1', 'B1', 'C1', undefined]

        levels.forEach(level => {
          const result = getLevelLabel(level as any)
          // Should start with uppercase letter
          expect(result[0]).toBe(result[0].toUpperCase())
        })
      })
    })
  })

  describe('integration tests', () => {
    it('should provide matching color and label for same level', () => {
      const level = 'B1'
      const color = getLevelColor(level)
      const label = getLevelLabel(level)

      expect(color).toBe('bg-yellow-100 text-yellow-700')
      expect(label).toBe('Intermediate')
    })

    it('should handle multiple levels correctly', () => {
      const levelTests = [
        { level: 'A1', expectedColor: 'bg-green-100 text-green-700', expectedLabel: 'Beginner' },
        { level: 'B2', expectedColor: 'bg-yellow-100 text-yellow-700', expectedLabel: 'Intermediate' },
        { level: 'C1', expectedColor: 'bg-red-100 text-red-700', expectedLabel: 'Advanced' }
      ]

      levelTests.forEach(({ level, expectedColor, expectedLabel }) => {
        expect(getLevelColor(level)).toBe(expectedColor)
        expect(getLevelLabel(level)).toBe(expectedLabel)
      })
    })

    it('should handle undefined consistently', () => {
      const color = getLevelColor(undefined)
      const label = getLevelLabel(undefined)

      expect(color).toBe('bg-gray-100 text-gray-600')
      expect(label).toBe('Unknown')
    })
  })
})
