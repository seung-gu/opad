/**
 * Reusable component for displaying token usage metrics.
 *
 * Features:
 * - Total tokens and cost display
 * - Breakdown by operation type
 * - Pure CSS bar chart for daily usage
 * - Responsive grid layout
 */

import { TokenUsageSummary, OperationUsage } from '@/types/usage'

interface UsageSummaryProps {
  summary: TokenUsageSummary
  days: number
}

/**
 * Maps operation keys to human-readable labels.
 */
const OPERATION_LABELS: Record<string, string> = {
  dictionary_search: 'Dictionary Search',
  article_generation: 'Article Generation',
}

/**
 * Get display label for an operation key.
 */
function getOperationLabel(key: string): string {
  return OPERATION_LABELS[key] || key.replaceAll('_', ' ').replaceAll(/\b\w/g, c => c.toUpperCase())
}

/**
 * Format token count with locale-aware formatting.
 */
function formatTokens(tokens: number): string {
  return tokens.toLocaleString()
}

/**
 * Format cost in USD with 4 decimal places.
 */
function formatCost(cost: number): string {
  return `$${cost.toFixed(4)}`
}

/**
 * Format date for display in chart.
 */
function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

export default function UsageSummary({ summary, days }: Readonly<UsageSummaryProps>) {
  const { total_tokens, total_cost, by_operation, daily_usage } = summary

  // Calculate max tokens for bar chart scaling
  const maxDailyTokens = Math.max(...daily_usage.map(d => d.tokens), 1)

  // Sort operations by token count descending
  const sortedOperations = Object.entries(by_operation).sort(
    ([, a], [, b]) => b.tokens - a.tokens
  )

  return (
    <div className="space-y-6">
      {/* Totals Section */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-blue-50 rounded-lg p-6 border border-blue-200">
          <div className="text-sm text-blue-600 font-medium mb-1">Total Tokens</div>
          <div className="text-4xl font-bold text-blue-900">{formatTokens(total_tokens)}</div>
          <div className="text-sm text-blue-600 mt-1">Last {days} days</div>
        </div>
        <div className="bg-green-50 rounded-lg p-6 border border-green-200">
          <div className="text-sm text-green-600 font-medium mb-1">Estimated Cost</div>
          <div className="text-4xl font-bold text-green-900">{formatCost(total_cost)}</div>
          <div className="text-sm text-green-600 mt-1">Last {days} days</div>
        </div>
      </div>

      {/* Operations Breakdown */}
      {sortedOperations.length > 0 && (
        <div>
          <h3 className="text-xl font-semibold text-gray-900 mb-4">Usage by Operation</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {sortedOperations.map(([operation, usage]) => (
              <OperationCard
                key={operation}
                operation={operation}
                usage={usage}
              />
            ))}
          </div>
        </div>
      )}

      {/* Daily Usage Chart */}
      {daily_usage.length > 0 && (
        <div>
          <h3 className="text-xl font-semibold text-gray-900 mb-4">Daily Usage</h3>
          <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
            <DailyUsageChart
              dailyUsage={daily_usage}
              maxTokens={maxDailyTokens}
            />
          </div>
        </div>
      )}

      {/* Empty state for daily usage */}
      {daily_usage.length === 0 && (
        <div className="bg-gray-50 rounded-lg p-8 border border-gray-200 text-center">
          <p className="text-gray-500">No daily usage data available for this period.</p>
        </div>
      )}
    </div>
  )
}

/**
 * Card component for displaying individual operation statistics.
 */
interface OperationCardProps {
  operation: string
  usage: OperationUsage
}

function OperationCard({ operation, usage }: Readonly<OperationCardProps>) {
  const label = getOperationLabel(operation)

  return (
    <div className="bg-white rounded-lg p-4 border border-gray-200 shadow-sm">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-sm font-medium text-gray-600 mb-1">{label}</div>
          <div className="text-2xl font-bold text-gray-900">{formatTokens(usage.tokens)}</div>
          <div className="text-sm text-gray-500 mt-1">tokens</div>
        </div>
        <div className="text-right">
          <div className="text-lg font-semibold text-green-700">{formatCost(usage.cost)}</div>
          <div className="text-xs text-gray-500 mt-1">{usage.count} request{usage.count === 1 ? '' : 's'}</div>
        </div>
      </div>
    </div>
  )
}

/**
 * Pure CSS bar chart for daily usage visualization.
 */
interface DailyUsageChartProps {
  dailyUsage: { date: string; tokens: number; cost: number }[]
  maxTokens: number
}

function DailyUsageChart({ dailyUsage, maxTokens }: Readonly<DailyUsageChartProps>) {
  // Show last 14 days max for readability, or all if fewer
  const displayData = dailyUsage.slice(-14)

  return (
    <div className="space-y-2">
      {displayData.map(({ date, tokens, cost }) => {
        const percentage = (tokens / maxTokens) * 100
        const barWidth = Math.max(percentage, 2) // Minimum 2% for visibility

        const formattedDate = formatDate(date)
        const ariaLabel = `${formattedDate}: ${formatTokens(tokens)} tokens, ${formatCost(cost)}`

        return (
          <div key={date} className="flex items-center gap-3">
            <div className="w-20 text-xs text-gray-600 flex-shrink-0">
              {formattedDate}
            </div>
            <div className="flex-1 h-6 bg-gray-200 rounded-full overflow-hidden relative">
              {/* Semantic progress element for accessibility (visually hidden) */}
              <progress
                value={tokens}
                max={maxTokens}
                aria-label={ariaLabel}
                className="sr-only"
              />
              {/* Visual bar (decorative, hidden from screen readers) */}
              <div
                className="h-full bg-gradient-to-r from-blue-500 to-blue-600 rounded-full transition-all duration-300"
                style={{ width: `${barWidth}%` }}
                aria-hidden="true"
              />
            </div>
            <div className="w-24 text-xs text-gray-700 text-right flex-shrink-0">
              {formatTokens(tokens)}
            </div>
            <div className="w-16 text-xs text-green-600 text-right flex-shrink-0">
              {formatCost(cost)}
            </div>
          </div>
        )
      })}

      {/* Legend */}
      <div className="flex justify-end gap-4 mt-4 pt-4 border-t border-gray-200">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-gradient-to-r from-blue-500 to-blue-600 rounded" />
          <span className="text-xs text-gray-600">Tokens</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-green-600 font-medium">$</span>
          <span className="text-xs text-gray-600">Cost</span>
        </div>
      </div>
    </div>
  )
}
