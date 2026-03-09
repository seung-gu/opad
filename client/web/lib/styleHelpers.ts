/**
 * Style and CSS utility functions.
 */

/**
 * Get Tailwind CSS classes for CEFR level badge.
 *
 * Returns color classes based on CEFR level using CSS variables:
 * - A levels (A1, A2): Green (good) - beginner
 * - B levels (B1, B2): Yellow (warn) - intermediate
 * - C levels (C1, C2): Red (danger) - advanced
 * - No level: Gray (text-dim) - unknown
 *
 * @param level - CEFR level string (e.g., 'A1', 'B2', 'C1')
 * @returns Tailwind CSS class string for background and text color
 *
 * @example
 * ```typescript
 * getLevelColor('A1')  // => 'bg-good/20 text-good'
 * getLevelColor('B2')  // => 'bg-accent-warn/20 text-accent-warn'
 * getLevelColor('C1')  // => 'bg-accent-danger/20 text-accent-danger'
 * getLevelColor()      // => 'bg-card text-text-dim'
 * ```
 */
export function getLevelColor(level?: string): string {
  if (!level) return 'bg-card text-text-dim'
  if (level.startsWith('A')) return 'bg-good/20 text-good'
  if (level.startsWith('B')) return 'bg-accent-warn/20 text-accent-warn'
  return 'bg-accent-danger/20 text-accent-danger' // C1, C2
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
