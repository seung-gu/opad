/**
 * Style and CSS utility functions.
 */

/**
 * Get Tailwind CSS classes for CEFR level badge.
 *
 * Returns color classes based on CEFR level:
 * - A levels (A1, A2): Green (beginner)
 * - B levels (B1, B2): Yellow (intermediate)
 * - C levels (C1, C2): Red (advanced)
 * - No level: Gray (unknown)
 *
 * @param level - CEFR level string (e.g., 'A1', 'B2', 'C1')
 * @returns Tailwind CSS class string for background and text color
 *
 * @example
 * ```typescript
 * getLevelColor('A1')  // => 'bg-green-100 text-green-700'
 * getLevelColor('B2')  // => 'bg-yellow-100 text-yellow-700'
 * getLevelColor('C1')  // => 'bg-red-100 text-red-700'
 * getLevelColor()      // => 'bg-gray-100 text-gray-600'
 * ```
 */
export function getLevelColor(level?: string): string {
  if (!level) return 'bg-gray-100 text-gray-600'
  if (level.startsWith('A')) return 'bg-green-100 text-green-700'
  if (level.startsWith('B')) return 'bg-yellow-100 text-yellow-700'
  return 'bg-red-100 text-red-700' // C1, C2
}

/**
 * Get a descriptive label for CEFR level.
 *
 * @param level - CEFR level string
 * @returns Human-readable level description
 */
export function getLevelLabel(level?: string): string {
  if (!level) return 'Unknown'
  if (level.startsWith('A')) return 'Beginner'
  if (level.startsWith('B')) return 'Intermediate'
  return 'Advanced' // C1, C2
}
