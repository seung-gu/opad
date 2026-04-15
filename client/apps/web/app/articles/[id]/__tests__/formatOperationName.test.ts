/* eslint-disable @typescript-eslint/no-explicit-any, sonarjs/no-duplicate-string */
/**
 * Unit tests for formatOperationName function and token usage aggregation logic.
 *
 * Tests for:
 * - formatOperationName with various inputs (with/without agentName)
 * - Default snake_case to Title Case conversion
 * - Agent name priority over operation name
 * - Edge cases: empty strings, special characters, null/undefined
 * - Aggregation logic: dictionary_search aggregated, article_generation separate
 * - Type validation for agent_name (string vs non-string)
 */

import { describe, test, expect } from 'vitest'

/**
 * Extract agent name from metadata with proper type checking and fallback.
 */
function extractAgentName(metadata?: { agent_name?: unknown; agent_role?: unknown }): string | undefined {
  const rawAgentName = metadata?.agent_name
  if (typeof rawAgentName === 'string' && rawAgentName) {
    return rawAgentName
  }
  const rawAgentRole = metadata?.agent_role
  if (typeof rawAgentRole === 'string' && rawAgentRole) {
    return rawAgentRole
  }
  return undefined
}

// Since formatOperationName is defined in page.tsx, we'll test it as a pure function
// We extract the logic here for testing

function formatOperationName(operation: string, agentName?: string): string {
  // Use agent name if available (e.g., "Article Search", "Article Selection", "Article Rewrite")
  if (agentName) {
    return agentName
  }
  // Default: convert snake_case to Title Case
  return operation.replaceAll('_', ' ').replaceAll(/\b\w/g, c => c.toUpperCase())
}

describe('formatOperationName', () => {
  describe('with agentName provided', () => {
    test('should return agentName when provided', () => {
      expect(formatOperationName('article_generation', 'Article Search')).toBe('Article Search')
    })

    test('should return agentName with special characters', () => {
      expect(formatOperationName('dictionary_search', 'Quality Check #2')).toBe('Quality Check #2')
    })

    test('should return agentName with numbers', () => {
      expect(formatOperationName('article_generation', 'Article Rewrite V2')).toBe('Article Rewrite V2')
    })

    test('should return agentName with hyphens', () => {
      expect(formatOperationName('dictionary_search', 'Content-Analyzer')).toBe('Content-Analyzer')
    })

    test('should return agentName with parentheses', () => {
      expect(formatOperationName('article_generation', 'Review (Advanced)')).toBe('Review (Advanced)')
    })

    test('should prioritize agentName over snake_case conversion', () => {
      // Even though the operation could be converted, agentName takes priority
      expect(formatOperationName('some_operation', 'Display Name')).toBe('Display Name')
    })
  })

  describe('without agentName (undefined or falsy)', () => {
    test('should convert snake_case to Title Case for article_generation', () => {
      expect(formatOperationName('article_generation')).toBe('Article Generation')
    })

    test('should convert snake_case to Title Case for dictionary_search', () => {
      expect(formatOperationName('dictionary_search')).toBe('Dictionary Search')
    })

    test('should convert snake_case to Title Case for custom_operation', () => {
      expect(formatOperationName('custom_operation')).toBe('Custom Operation')
    })

    test('should handle multiple underscores', () => {
      expect(formatOperationName('very_long_operation_name')).toBe('Very Long Operation Name')
    })

    test('should handle single word operation', () => {
      expect(formatOperationName('generation')).toBe('Generation')
    })

    test('should not convert when no underscores present', () => {
      expect(formatOperationName('generation')).toBe('Generation')
    })

    test('should return empty string as-is', () => {
      // Edge case: empty operation name
      expect(formatOperationName('')).toBe('')
    })
  })

  describe('with falsy agentName values', () => {
    test('should convert operation when agentName is empty string', () => {
      expect(formatOperationName('article_generation', '')).toBe('Article Generation')
    })

    test('should convert operation when agentName is undefined', () => {
      expect(formatOperationName('dictionary_search', undefined)).toBe('Dictionary Search')
    })

    test('should convert operation when agentName is null', () => {
      expect(formatOperationName('article_generation', null as any)).toBe('Article Generation')
    })

    test('should convert operation when agentName is false', () => {
      expect(formatOperationName('dictionary_search', false as any)).toBe('Dictionary Search')
    })

    test('should convert operation when agentName is 0', () => {
      expect(formatOperationName('article_generation', 0 as any)).toBe('Article Generation')
    })
  })

  describe('type validation and edge cases', () => {
    test('should handle agentName that is not a string but truthy', () => {
      // Testing with a non-string truthy value (number converted to string context)
      const agentName = 123 as any
      // In JavaScript, this would be truthy, but in practice agentName should be a string
      expect(formatOperationName('article_generation', agentName?.toString())).toBe('123')
    })

    test('should preserve case in agentName', () => {
      expect(formatOperationName('article_generation', 'MixedCaseAgent')).toBe('MixedCaseAgent')
    })

    test('should preserve whitespace in agentName', () => {
      expect(formatOperationName('article_generation', '  spaced name  ')).toBe('  spaced name  ')
    })

    test('should handle very long agentName', () => {
      const longName = 'A'.repeat(100)
      expect(formatOperationName('article_generation', longName)).toBe(longName)
    })

    test('should handle unicode characters in agentName', () => {
      expect(formatOperationName('article_generation', 'Recherche 📰')).toBe('Recherche 📰')
    })
  })
})

// Test aggregation logic
interface TokenUsageRecord {
  id: string
  operation: string
  model: string
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  estimated_cost: number
  metadata?: {
    agent_name?: string
    agent_role?: string
    [key: string]: any
  }
}

interface AggregatedUsage {
  operation: string
  model: string
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  estimated_cost: number
  agent_name?: string
}

function aggregateTokenUsage(records: TokenUsageRecord[]): AggregatedUsage[] {
  const aggregatedMap = new Map<string, AggregatedUsage>()

  for (const record of records) {
    const agentName = extractAgentName(record.metadata)

    // dictionary_search: aggregate by operation+model
    // article_generation: keep separate using record id
    const key = record.operation === 'dictionary_search'
      ? `op:dictionary_search:${record.model}`
      : `id:${record.id}`

    const existing = aggregatedMap.get(key)
    if (existing) {
      existing.prompt_tokens += record.prompt_tokens
      existing.completion_tokens += record.completion_tokens
      existing.total_tokens += record.total_tokens
      existing.estimated_cost += record.estimated_cost
    } else {
      aggregatedMap.set(key, {
        operation: record.operation,
        model: record.model,
        prompt_tokens: record.prompt_tokens,
        completion_tokens: record.completion_tokens,
        total_tokens: record.total_tokens,
        estimated_cost: record.estimated_cost,
        agent_name: agentName
      })
    }
  }

  return Array.from(aggregatedMap.values())
}

describe('aggregateTokenUsage', () => {
  describe('empty and edge cases', () => {
    test('should handle empty records array', () => {
      expect(aggregateTokenUsage([])).toEqual([])
    })

    test('should handle null metadata', () => {
      const records: TokenUsageRecord[] = [
        {
          id: '1',
          operation: 'article_generation',
          model: 'gpt-4',
          prompt_tokens: 100,
          completion_tokens: 50,
          total_tokens: 150,
          estimated_cost: 0.01,
          metadata: undefined
        }
      ]

      const result = aggregateTokenUsage(records)
      expect(result).toHaveLength(1)
      expect(result[0].agent_name).toBeUndefined()
    })
  })

  describe('dictionary_search aggregation', () => {
    test('should aggregate multiple dictionary_search records with same model', () => {
      const records: TokenUsageRecord[] = [
        {
          id: '1',
          operation: 'dictionary_search',
          model: 'gpt-4.1-mini',
          prompt_tokens: 100,
          completion_tokens: 50,
          total_tokens: 150,
          estimated_cost: 0.001,
          metadata: { agent_name: 'Dict Search' }
        },
        {
          id: '2',
          operation: 'dictionary_search',
          model: 'gpt-4.1-mini',
          prompt_tokens: 150,
          completion_tokens: 75,
          total_tokens: 225,
          estimated_cost: 0.0015,
          metadata: { agent_name: 'Dict Search' }
        }
      ]

      const result = aggregateTokenUsage(records)

      expect(result).toHaveLength(1)
      expect(result[0].operation).toBe('dictionary_search')
      expect(result[0].model).toBe('gpt-4.1-mini')
      expect(result[0].prompt_tokens).toBe(250) // 100 + 150
      expect(result[0].completion_tokens).toBe(125) // 50 + 75
      expect(result[0].total_tokens).toBe(375) // 150 + 225
      expect(result[0].estimated_cost).toBe(0.0025) // 0.001 + 0.0015
      expect(result[0].agent_name).toBe('Dict Search')
    })

    test('should NOT aggregate dictionary_search with different models', () => {
      const records: TokenUsageRecord[] = [
        {
          id: '1',
          operation: 'dictionary_search',
          model: 'gpt-4.1-mini',
          prompt_tokens: 100,
          completion_tokens: 50,
          total_tokens: 150,
          estimated_cost: 0.001,
          metadata: { agent_name: 'Search 1' }
        },
        {
          id: '2',
          operation: 'dictionary_search',
          model: 'gpt-4',
          prompt_tokens: 150,
          completion_tokens: 75,
          total_tokens: 225,
          estimated_cost: 0.01,
          metadata: { agent_name: 'Search 2' }
        }
      ]

      const result = aggregateTokenUsage(records)

      expect(result).toHaveLength(2)
      // First record
      expect(result[0].model).toBe('gpt-4.1-mini')
      expect(result[0].total_tokens).toBe(150)
      // Second record
      expect(result[1].model).toBe('gpt-4')
      expect(result[1].total_tokens).toBe(225)
    })
  })

  describe('article_generation separation', () => {
    test('should keep article_generation records separate (not aggregated)', () => {
      const records: TokenUsageRecord[] = [
        {
          id: '1',
          operation: 'article_generation',
          model: 'gpt-4',
          prompt_tokens: 500,
          completion_tokens: 250,
          total_tokens: 750,
          estimated_cost: 0.05,
          metadata: { agent_name: 'Article Search' }
        },
        {
          id: '2',
          operation: 'article_generation',
          model: 'gpt-4',
          prompt_tokens: 600,
          completion_tokens: 300,
          total_tokens: 900,
          estimated_cost: 0.06,
          metadata: { agent_name: 'Article Selection' }
        }
      ]

      const result = aggregateTokenUsage(records)

      // Should have 2 separate records (not aggregated)
      expect(result).toHaveLength(2)
      expect(result[0].total_tokens).toBe(750)
      expect(result[1].total_tokens).toBe(900)
      expect(result[0].agent_name).toBe('Article Search')
      expect(result[1].agent_name).toBe('Article Selection')
    })
  })

  describe('mixed operations', () => {
    test('should handle mix of dictionary_search and article_generation', () => {
      const records: TokenUsageRecord[] = [
        {
          id: '1',
          operation: 'dictionary_search',
          model: 'gpt-4.1-mini',
          prompt_tokens: 100,
          completion_tokens: 50,
          total_tokens: 150,
          estimated_cost: 0.001,
          metadata: { agent_name: undefined }
        },
        {
          id: '2',
          operation: 'article_generation',
          model: 'gpt-4',
          prompt_tokens: 500,
          completion_tokens: 250,
          total_tokens: 750,
          estimated_cost: 0.05,
          metadata: { agent_name: 'Article Search' }
        },
        {
          id: '3',
          operation: 'dictionary_search',
          model: 'gpt-4.1-mini',
          prompt_tokens: 200,
          completion_tokens: 100,
          total_tokens: 300,
          estimated_cost: 0.002,
          metadata: {}
        },
        {
          id: '4',
          operation: 'article_generation',
          model: 'gpt-4',
          prompt_tokens: 600,
          completion_tokens: 300,
          total_tokens: 900,
          estimated_cost: 0.06,
          metadata: { agent_name: 'Article Selection' }
        }
      ]

      const result = aggregateTokenUsage(records)

      expect(result).toHaveLength(3)

      // Find aggregated dictionary_search
      const dictSearch = result.find(r => r.operation === 'dictionary_search')
      expect(dictSearch).toBeDefined()
      expect(dictSearch!.prompt_tokens).toBe(300) // 100 + 200
      expect(dictSearch!.completion_tokens).toBe(150) // 50 + 100
      expect(dictSearch!.total_tokens).toBe(450)

      // Verify article_generation records are separate
      const articles = result.filter(r => r.operation === 'article_generation')
      expect(articles).toHaveLength(2)
    })
  })

  describe('agent_name handling', () => {
    test('should extract agent_name from metadata when present', () => {
      const records: TokenUsageRecord[] = [
        {
          id: '1',
          operation: 'article_generation',
          model: 'gpt-4',
          prompt_tokens: 500,
          completion_tokens: 250,
          total_tokens: 750,
          estimated_cost: 0.05,
          metadata: { agent_name: 'Article Search' }
        }
      ]

      const result = aggregateTokenUsage(records)

      expect(result[0].agent_name).toBe('Article Search')
    })

    test('should fallback to agent_role when agent_name not present', () => {
      const records: TokenUsageRecord[] = [
        {
          id: '1',
          operation: 'article_generation',
          model: 'gpt-4',
          prompt_tokens: 500,
          completion_tokens: 250,
          total_tokens: 750,
          estimated_cost: 0.05,
          metadata: { agent_role: 'News Researcher' }
        }
      ]

      const result = aggregateTokenUsage(records)

      expect(result[0].agent_name).toBe('News Researcher')
    })

    test('should prefer agent_name over agent_role', () => {
      const records: TokenUsageRecord[] = [
        {
          id: '1',
          operation: 'article_generation',
          model: 'gpt-4',
          prompt_tokens: 500,
          completion_tokens: 250,
          total_tokens: 750,
          estimated_cost: 0.05,
          metadata: { agent_name: 'Article Search', agent_role: 'News Researcher' }
        }
      ]

      const result = aggregateTokenUsage(records)

      expect(result[0].agent_name).toBe('Article Search')
    })

    test('should handle non-string agent_name values', () => {
      const records: TokenUsageRecord[] = [
        {
          id: '1',
          operation: 'article_generation',
          model: 'gpt-4',
          prompt_tokens: 500,
          completion_tokens: 250,
          total_tokens: 750,
          estimated_cost: 0.05,
          metadata: { agent_name: 123 as any, agent_role: 'Researcher' }
        }
      ]

      const result = aggregateTokenUsage(records)

      // Non-string agent_name should be ignored, fallback to agent_role
      expect(result[0].agent_name).toBe('Researcher')
    })

    test('should handle null agent_name', () => {
      const records: TokenUsageRecord[] = [
        {
          id: '1',
          operation: 'article_generation',
          model: 'gpt-4',
          prompt_tokens: 500,
          completion_tokens: 250,
          total_tokens: 750,
          estimated_cost: 0.05,
          metadata: { agent_name: null as any, agent_role: 'Researcher' }
        }
      ]

      const result = aggregateTokenUsage(records)

      // Null agent_name should be ignored, fallback to agent_role
      expect(result[0].agent_name).toBe('Researcher')
    })

    test('should handle empty string agent_name', () => {
      const records: TokenUsageRecord[] = [
        {
          id: '1',
          operation: 'article_generation',
          model: 'gpt-4',
          prompt_tokens: 500,
          completion_tokens: 250,
          total_tokens: 750,
          estimated_cost: 0.05,
          metadata: { agent_name: '' }
        }
      ]

      const result = aggregateTokenUsage(records)

      // Empty string is falsy, should not be set (undefined)
      expect(result[0].agent_name).toBeUndefined()
    })

    test('should preserve agent_name with special characters', () => {
      const records: TokenUsageRecord[] = [
        {
          id: '1',
          operation: 'article_generation',
          model: 'gpt-4',
          prompt_tokens: 500,
          completion_tokens: 250,
          total_tokens: 750,
          estimated_cost: 0.05,
          metadata: { agent_name: 'Article Search & Selection' }
        }
      ]

      const result = aggregateTokenUsage(records)

      expect(result[0].agent_name).toBe('Article Search & Selection')
    })
  })

  describe('malformed metadata', () => {
    test('should handle missing metadata gracefully', () => {
      const records: TokenUsageRecord[] = [
        {
          id: '1',
          operation: 'article_generation',
          model: 'gpt-4',
          prompt_tokens: 500,
          completion_tokens: 250,
          total_tokens: 750,
          estimated_cost: 0.05
        }
      ]

      const result = aggregateTokenUsage(records)

      expect(result).toHaveLength(1)
      expect(result[0].agent_name).toBeUndefined()
    })

    test('should handle metadata with additional fields', () => {
      const records: TokenUsageRecord[] = [
        {
          id: '1',
          operation: 'article_generation',
          model: 'gpt-4',
          prompt_tokens: 500,
          completion_tokens: 250,
          total_tokens: 750,
          estimated_cost: 0.05,
          metadata: {
            agent_name: 'Article Search',
            job_id: 'job-123',
            extra_field: 'extra_value'
          }
        }
      ]

      const result = aggregateTokenUsage(records)

      expect(result[0].agent_name).toBe('Article Search')
    })

    test('should handle metadata with null values', () => {
      const records: TokenUsageRecord[] = [
        {
          id: '1',
          operation: 'article_generation',
          model: 'gpt-4',
          prompt_tokens: 500,
          completion_tokens: 250,
          total_tokens: 750,
          estimated_cost: 0.05,
          metadata: { agent_name: null as any, agent_role: null as any }
        }
      ]

      const result = aggregateTokenUsage(records)

      expect(result[0].agent_name).toBeUndefined()
    })
  })

  describe('token count aggregation accuracy', () => {
    test('should accurately sum multiple dictionary_search records', () => {
      const records: TokenUsageRecord[] = [
        {
          id: '1',
          operation: 'dictionary_search',
          model: 'gpt-4.1-mini',
          prompt_tokens: 10,
          completion_tokens: 5,
          total_tokens: 15,
          estimated_cost: 0.0001
        },
        {
          id: '2',
          operation: 'dictionary_search',
          model: 'gpt-4.1-mini',
          prompt_tokens: 20,
          completion_tokens: 10,
          total_tokens: 30,
          estimated_cost: 0.0002
        },
        {
          id: '3',
          operation: 'dictionary_search',
          model: 'gpt-4.1-mini',
          prompt_tokens: 30,
          completion_tokens: 15,
          total_tokens: 45,
          estimated_cost: 0.0003
        }
      ]

      const result = aggregateTokenUsage(records)

      expect(result).toHaveLength(1)
      expect(result[0].prompt_tokens).toBe(60) // 10 + 20 + 30
      expect(result[0].completion_tokens).toBe(30) // 5 + 10 + 15
      expect(result[0].total_tokens).toBe(90) // 15 + 30 + 45
      expect(result[0].estimated_cost).toBeCloseTo(0.0006, 6)
    })

    test('should handle zero token records', () => {
      const records: TokenUsageRecord[] = [
        {
          id: '1',
          operation: 'dictionary_search',
          model: 'gpt-4.1-mini',
          prompt_tokens: 0,
          completion_tokens: 0,
          total_tokens: 0,
          estimated_cost: 0
        },
        {
          id: '2',
          operation: 'dictionary_search',
          model: 'gpt-4.1-mini',
          prompt_tokens: 100,
          completion_tokens: 50,
          total_tokens: 150,
          estimated_cost: 0.001
        }
      ]

      const result = aggregateTokenUsage(records)

      expect(result).toHaveLength(1)
      expect(result[0].total_tokens).toBe(150)
      expect(result[0].estimated_cost).toBeCloseTo(0.001, 6)
    })

    test('should handle large token counts', () => {
      const records: TokenUsageRecord[] = [
        {
          id: '1',
          operation: 'article_generation',
          model: 'gpt-4',
          prompt_tokens: 100000,
          completion_tokens: 50000,
          total_tokens: 150000,
          estimated_cost: 1.5
        },
        {
          id: '2',
          operation: 'article_generation',
          model: 'gpt-4',
          prompt_tokens: 200000,
          completion_tokens: 100000,
          total_tokens: 300000,
          estimated_cost: 3.0
        }
      ]

      const result = aggregateTokenUsage(records)

      expect(result).toHaveLength(2) // Kept separate
      expect(result[0].total_tokens).toBe(150000)
      expect(result[1].total_tokens).toBe(300000)
    })
  })
})
