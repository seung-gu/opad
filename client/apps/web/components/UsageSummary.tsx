/**
 * Token usage metrics: totals, a breakdown by operation, and a daily bar list.
 */

import { TokenUsageSummary, OperationUsage, getOperationLabel, formatTokens, formatCost } from '@opad/libs'

interface UsageSummaryProps {
  summary: TokenUsageSummary
  days: number
}

function formatChartDate(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

export default function UsageSummary({ summary, days }: Readonly<UsageSummaryProps>) {
  const { total_tokens, total_cost, by_operation, daily_usage } = summary

  const maxDailyTokens = Math.max(...daily_usage.map(d => d.tokens), 1)

  const sortedOperations = Object.entries(by_operation).sort(
    ([, a], [, b]) => b.tokens - a.tokens
  )

  return (
    <div className="space-y-12">
      <div className="flex flex-wrap gap-x-16 gap-y-4">
        <div>
          <div className="font-serif text-[40px] leading-none tabular-nums text-text-strong">
            {formatTokens(total_tokens)}
          </div>
          <div className="mt-2 text-[12px] text-text-dim">Total tokens</div>
          <div className="text-[12px] text-text-dim">Last {days} days</div>
        </div>
        <div>
          <div className="font-serif text-[40px] leading-none tabular-nums text-text-strong">
            {formatCost(total_cost)}
          </div>
          <div className="mt-2 text-[12px] text-text-dim">Estimated cost</div>
          <div className="text-[12px] text-text-dim">Last {days} days</div>
        </div>
      </div>

      {sortedOperations.length > 0 && (
        <section className="border-t border-border-card pt-6">
          <h3 className="font-serif text-[19px] italic text-text-strong">By operation</h3>
          <ul className="mt-2">
            {sortedOperations.map(([operation, usage]) => (
              <OperationRow key={operation} operation={operation} usage={usage} />
            ))}
          </ul>
        </section>
      )}

      {daily_usage.length > 0 ? (
        <section className="border-t border-border-card pt-6">
          <h3 className="font-serif text-[19px] italic text-text-strong">Daily</h3>
          <div className="mt-4">
            <DailyUsageChart dailyUsage={daily_usage} maxTokens={maxDailyTokens} />
          </div>
        </section>
      ) : (
        <section className="border-t border-border-card pt-6">
          <p className="text-[13px] text-text-dim">No daily usage data available for this period.</p>
        </section>
      )}
    </div>
  )
}

interface OperationRowProps {
  operation: string
  usage: OperationUsage
}

function OperationRow({ operation, usage }: Readonly<OperationRowProps>) {
  const label = getOperationLabel(operation)

  return (
    <li className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1 border-b border-border-card py-3 last:border-b-0">
      <span className="text-[14px] text-foreground">{label}</span>
      <span className="flex items-baseline gap-6 text-[13px] text-text-dim">
        <span>
          <span className="tabular-nums text-foreground">{formatTokens(usage.tokens)}</span> tokens
        </span>
        <span className="tabular-nums">
          {usage.count} request{usage.count === 1 ? '' : 's'}
        </span>
        <span className="tabular-nums text-foreground">{formatCost(usage.cost)}</span>
      </span>
    </li>
  )
}

interface DailyUsageChartProps {
  dailyUsage: { date: string; tokens: number; cost: number }[]
  maxTokens: number
}

function DailyUsageChart({ dailyUsage, maxTokens }: Readonly<DailyUsageChartProps>) {
  // Last 14 days keeps the list readable
  const displayData = dailyUsage.slice(-14)

  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-4 pb-1 text-[11px] text-text-dim">
        <div className="w-16 shrink-0" />
        <div className="flex-1" />
        <div className="w-20 shrink-0 text-right">Tokens</div>
        <div className="w-16 shrink-0 text-right">Cost</div>
      </div>
      {displayData.map(({ date, tokens, cost }) => {
        const percentage = (tokens / maxTokens) * 100
        const barWidth = Math.max(percentage, 1)

        const formattedDate = formatChartDate(date)
        const ariaLabel = `${formattedDate}: ${formatTokens(tokens)} tokens, ${formatCost(cost)}`

        return (
          <div key={date} className="flex items-center gap-4 text-[12px]">
            <div className="w-16 shrink-0 text-text-dim">{formattedDate}</div>
            <div className="relative h-3 flex-1 bg-card-hover">
              <progress value={tokens} max={maxTokens} aria-label={ariaLabel} className="sr-only" />
              <div className="h-3 bg-accent" style={{ width: `${barWidth}%` }} aria-hidden="true" />
            </div>
            <div className="w-20 shrink-0 text-right tabular-nums text-foreground">{formatTokens(tokens)}</div>
            <div className="w-16 shrink-0 text-right tabular-nums text-text-dim">{formatCost(cost)}</div>
          </div>
        )
      })}
    </div>
  )
}
