/**
 * Date and time formatting utilities.
 */

/**
 * Format a date string using Intl.DateTimeFormat.
 *
 * @param dateString - ISO date string to format
 * @param locale - Locale string (default: 'en-US')
 * @param options - Intl.DateTimeFormatOptions (default: long format with time)
 * @returns Formatted date string, or original string if parsing fails
 *
 * @example
 * ```typescript
 * formatDate('2024-01-29T12:30:00Z')
 * // => "January 29, 2024, 12:30 PM"
 *
 * formatDate('2024-01-29T12:30:00Z', 'en-US', { month: 'short' })
 * // => "Jan 29, 2024, 12:30 PM"
 * ```
 */
export function formatDate(
  dateString: string,
  locale: string = 'en-US',
  options: Intl.DateTimeFormatOptions = {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  }
): string {
  try {
    const date = new Date(dateString)
    // Check if date is valid
    if (isNaN(date.getTime())) {
      return dateString
    }
    return new Intl.DateTimeFormat(locale, options).format(date)
  } catch {
    return dateString
  }
}

/**
 * Format a date string to short format (e.g., "Jan 29, 2024").
 *
 * @param dateString - ISO date string to format
 * @returns Short formatted date string
 */
export function formatDateShort(dateString: string): string {
  return formatDate(dateString, 'en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  })
}

/**
 * Format a date string to include time (e.g., "Jan 29, 2024, 12:30 PM").
 *
 * @param dateString - ISO date string to format
 * @returns Formatted date string with time
 */
export function formatDateTime(dateString: string): string {
  return formatDate(dateString, 'en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}
