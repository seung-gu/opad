/**
 * Token usage type definitions.
 *
 * These types match the FastAPI TokenUsageSummary response model
 * from GET /usage/me endpoint.
 */

/**
 * Usage statistics for a single operation type.
 */
export interface OperationUsage {
  /** Total tokens consumed by this operation */
  tokens: number
  /** Estimated cost in USD */
  cost: number
  /** Number of times this operation was performed */
  count: number
}

/**
 * Daily aggregated usage statistics.
 */
export interface DailyUsage {
  /** Date in YYYY-MM-DD format */
  date: string
  /** Total tokens consumed on this date */
  tokens: number
  /** Estimated cost in USD for this date */
  cost: number
}

/**
 * Complete token usage summary for a user.
 *
 * Provides aggregated statistics across a specified time period,
 * broken down by operation type and daily usage.
 */
export interface TokenUsageSummary {
  /** Total tokens consumed across all operations */
  total_tokens: number
  /** Total estimated cost in USD */
  total_cost: number
  /** Usage breakdown by operation type (dictionary_search, article_generation) */
  by_operation: Record<string, OperationUsage>
  /** Daily usage history for charting */
  daily_usage: DailyUsage[]
}

/**
 * Single token usage record for an API call.
 *
 * Represents one API call's token consumption, typically returned
 * from GET /usage/articles/{article_id} endpoint.
 */
export interface TokenUsageRecord {
  /** Usage record ID */
  id: string
  /** User ID who incurred the usage */
  user_id: string
  /** Operation type: dictionary_search or article_generation */
  operation: string
  /** Model name used (e.g., claude-3-5-haiku-20241022) */
  model: string
  /** Number of input tokens */
  prompt_tokens: number
  /** Number of output tokens */
  completion_tokens: number
  /** Total tokens (prompt + completion) */
  total_tokens: number
  /** Estimated cost in USD */
  estimated_cost: number
  /** Additional metadata (e.g., article_id) */
  metadata: Record<string, unknown>
  /** Timestamp of the API call */
  created_at: string
}
