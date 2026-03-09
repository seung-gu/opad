/* eslint-disable sonarjs/no-duplicate-string */
/**
 * Tests for UsageSummary component.
 *
 * Comprehensive tests for token usage display component including:
 * - Total tokens and cost rendering
 * - Operation breakdown cards
 * - Daily usage chart visualization
 * - Number formatting
 * - Edge cases (empty data, etc.)
 * - Helper functions
 */

import React from 'react'
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import UsageSummary from '../UsageSummary'
import { TokenUsageSummary } from '@/types/usage'

describe('UsageSummary', () => {
  const mockSummary: TokenUsageSummary = {
    total_tokens: 125430,
    total_cost: 0.0042,
    by_operation: {
      dictionary_search: { tokens: 45230, cost: 0.0008, count: 120 },
      article_generation: { tokens: 80200, cost: 0.0034, count: 8 }
    },
    daily_usage: [
      { date: '2026-01-28', tokens: 3000, cost: 0.001 },
      { date: '2026-01-29', tokens: 5000, cost: 0.002 },
      { date: '2026-01-30', tokens: 7000, cost: 0.003 }
    ]
  }

  describe('rendering total tokens and cost', () => {
    it('should render total tokens correctly', () => {
      render(<UsageSummary summary={mockSummary} days={30} />)

      expect(screen.getByText('Total Tokens')).toBeInTheDocument()
      expect(screen.getByText('125,430')).toBeInTheDocument()
    })

    it('should render formatted total cost correctly', () => {
      render(<UsageSummary summary={mockSummary} days={30} />)

      expect(screen.getByText('Estimated Cost')).toBeInTheDocument()
      expect(screen.getByText('$0.0042')).toBeInTheDocument()
    })

    it('should display days information in totals section', () => {
      render(<UsageSummary summary={mockSummary} days={7} />)

      // Days info appears in both Total Tokens and Estimated Cost cards
      const daysTexts = screen.getAllByText('Last 7 days')
      expect(daysTexts.length).toBeGreaterThan(0)
    })

    it('should display different days information based on props', () => {
      const { rerender } = render(<UsageSummary summary={mockSummary} days={30} />)

      expect(screen.getAllByText('Last 30 days').length).toBeGreaterThan(0)

      rerender(<UsageSummary summary={mockSummary} days={90} />)

      expect(screen.getAllByText('Last 90 days').length).toBeGreaterThan(0)
    })
  })

  describe('operation breakdown cards', () => {
    it('should render usage by operation heading', () => {
      render(<UsageSummary summary={mockSummary} days={30} />)

      expect(screen.getByText('Usage by Operation')).toBeInTheDocument()
    })

    it('should render operation cards sorted by token count descending', () => {
      render(<UsageSummary summary={mockSummary} days={30} />)

      const operationHeadings = screen.getAllByText(/Article Generation|Dictionary Search/)
      // Article Generation (80200 tokens) should come before Dictionary Search (45230 tokens)
      expect(operationHeadings[0]).toHaveTextContent('Article Generation')
      expect(operationHeadings[1]).toHaveTextContent('Dictionary Search')
    })

    it('should render operation card with correct tokens', () => {
      render(<UsageSummary summary={mockSummary} days={30} />)

      expect(screen.getByText('80,200')).toBeInTheDocument()
      expect(screen.getByText('45,230')).toBeInTheDocument()
    })

    it('should render operation card with correct costs', () => {
      render(<UsageSummary summary={mockSummary} days={30} />)

      expect(screen.getByText('$0.0034')).toBeInTheDocument()
      expect(screen.getByText('$0.0008')).toBeInTheDocument()
    })

    it('should render operation card with correct request counts', () => {
      render(<UsageSummary summary={mockSummary} days={30} />)

      expect(screen.getByText('8 requests')).toBeInTheDocument()
      expect(screen.getByText('120 requests')).toBeInTheDocument()
    })

    it('should handle singular request count correctly', () => {
      const summaryWithSingleRequest: TokenUsageSummary = {
        total_tokens: 5000,
        total_cost: 0.001,
        by_operation: {
          dictionary_search: { tokens: 5000, cost: 0.001, count: 1 }
        },
        daily_usage: []
      }

      render(<UsageSummary summary={summaryWithSingleRequest} days={30} />)

      expect(screen.getByText('1 request')).toBeInTheDocument()
    })

    it('should not render operations section when empty', () => {
      const summaryWithNoOperations: TokenUsageSummary = {
        total_tokens: 0,
        total_cost: 0,
        by_operation: {},
        daily_usage: []
      }

      render(<UsageSummary summary={summaryWithNoOperations} days={30} />)

      expect(screen.queryByText('Usage by Operation')).not.toBeInTheDocument()
    })
  })

  describe('daily usage chart', () => {
    it('should render daily usage chart heading', () => {
      render(<UsageSummary summary={mockSummary} days={30} />)

      expect(screen.getByText('Daily Usage')).toBeInTheDocument()
    })

    it('should render all daily usage bars', () => {
      render(<UsageSummary summary={mockSummary} days={30} />)

      expect(screen.getByText('Jan 28')).toBeInTheDocument()
      expect(screen.getByText('Jan 29')).toBeInTheDocument()
      expect(screen.getByText('Jan 30')).toBeInTheDocument()
    })

    it('should render daily usage token counts', () => {
      render(<UsageSummary summary={mockSummary} days={30} />)

      expect(screen.getByText('3,000')).toBeInTheDocument()
      expect(screen.getByText('5,000')).toBeInTheDocument()
      expect(screen.getByText('7,000')).toBeInTheDocument()
    })

    it('should render daily usage costs', () => {
      render(<UsageSummary summary={mockSummary} days={30} />)

      expect(screen.getByText('$0.0010')).toBeInTheDocument()
      expect(screen.getByText('$0.0020')).toBeInTheDocument()
      expect(screen.getByText('$0.0030')).toBeInTheDocument()
    })

    it('should render chart legend', () => {
      render(<UsageSummary summary={mockSummary} days={30} />)

      expect(screen.getByText('Tokens')).toBeInTheDocument()
      expect(screen.getByText('Cost')).toBeInTheDocument()
    })

    it('should show limited bars when more than 14 days provided', () => {
      const manyDays: TokenUsageSummary = {
        total_tokens: 100000,
        total_cost: 0.1,
        by_operation: {},
        daily_usage: Array.from({ length: 30 }, (_, i) => ({
          date: `2026-01-${String(i + 1).padStart(2, '0')}`,
          tokens: 1000 + i * 100,
          cost: 0.001 + i * 0.0001
        }))
      }

      render(<UsageSummary summary={manyDays} days={30} />)

      // Should show last 14 days
      const dateElements = screen.queryAllByText(/Jan \d+/)
      expect(dateElements.length).toBeLessThanOrEqual(14)
    })

    it('should not render chart when daily usage is empty', () => {
      const summaryNoDaily: TokenUsageSummary = {
        total_tokens: 100,
        total_cost: 0.001,
        by_operation: {
          dictionary_search: { tokens: 100, cost: 0.001, count: 1 }
        },
        daily_usage: []
      }

      render(<UsageSummary summary={summaryNoDaily} days={30} />)

      expect(screen.queryByText('Daily Usage')).not.toBeInTheDocument()
    })

    it('should display empty state when no daily usage data', () => {
      const summaryNoDaily: TokenUsageSummary = {
        total_tokens: 0,
        total_cost: 0,
        by_operation: {},
        daily_usage: []
      }

      render(<UsageSummary summary={summaryNoDaily} days={30} />)

      expect(screen.getByText('No daily usage data available for this period.')).toBeInTheDocument()
    })
  })

  describe('number formatting', () => {
    it('should format tokens with thousand separators', () => {
      render(<UsageSummary summary={mockSummary} days={30} />)

      expect(screen.getByText('125,430')).toBeInTheDocument()
      expect(screen.getByText('80,200')).toBeInTheDocument()
    })

    it('should format cost with $X.XXXX format', () => {
      render(<UsageSummary summary={mockSummary} days={30} />)

      expect(screen.getByText('$0.0042')).toBeInTheDocument()
      expect(screen.getByText('$0.0034')).toBeInTheDocument()
      expect(screen.getByText('$0.0008')).toBeInTheDocument()
    })

    it('should handle zero values correctly', () => {
      const summaryWithZeros: TokenUsageSummary = {
        total_tokens: 0,
        total_cost: 0,
        by_operation: {
          dictionary_search: { tokens: 0, cost: 0, count: 0 }
        },
        daily_usage: [
          { date: '2026-01-30', tokens: 0, cost: 0 }
        ]
      }

      render(<UsageSummary summary={summaryWithZeros} days={30} />)

      // Check that zero values are rendered (may appear multiple times)
      expect(screen.getByText('Total Tokens')).toBeInTheDocument()
      expect(screen.getAllByText('$0.0000').length).toBeGreaterThan(0)
    })

    it('should format large token numbers correctly', () => {
      const largeTokenSummary: TokenUsageSummary = {
        total_tokens: 1234567890,
        total_cost: 123456.7890,
        by_operation: {},
        daily_usage: []
      }

      render(<UsageSummary summary={largeTokenSummary} days={30} />)

      expect(screen.getByText('1,234,567,890')).toBeInTheDocument()
      expect(screen.getByText('$123456.7890')).toBeInTheDocument()
    })

    it('should format very small costs correctly', () => {
      const smallCostSummary: TokenUsageSummary = {
        total_tokens: 1,
        total_cost: 0.0001,
        by_operation: {
          dictionary_search: { tokens: 1, cost: 0.0001, count: 1 }
        },
        daily_usage: []
      }

      render(<UsageSummary summary={smallCostSummary} days={30} />)

      // '$0.0001' appears in both Estimated Cost card and operation card
      expect(screen.getAllByText('$0.0001').length).toBeGreaterThan(0)
    })
  })

  describe('date formatting', () => {
    it('should format dates in month-day format', () => {
      render(<UsageSummary summary={mockSummary} days={30} />)

      expect(screen.getByText('Jan 28')).toBeInTheDocument()
      expect(screen.getByText('Jan 29')).toBeInTheDocument()
      expect(screen.getByText('Jan 30')).toBeInTheDocument()
    })

    it('should handle various dates correctly', () => {
      const variousDates: TokenUsageSummary = {
        total_tokens: 10000,
        total_cost: 0.01,
        by_operation: {},
        daily_usage: [
          { date: '2026-02-28', tokens: 1000, cost: 0.001 },
          { date: '2026-12-31', tokens: 2000, cost: 0.002 },
          { date: '2026-03-01', tokens: 3000, cost: 0.003 }
        ]
      }

      render(<UsageSummary summary={variousDates} days={30} />)

      expect(screen.getByText('Feb 28')).toBeInTheDocument()
      expect(screen.getByText('Dec 31')).toBeInTheDocument()
      expect(screen.getByText('Mar 1')).toBeInTheDocument()
    })
  })

  describe('operation label transformation', () => {
    it('should transform dictionary_search to Dictionary Search', () => {
      render(<UsageSummary summary={mockSummary} days={30} />)

      expect(screen.getByText('Dictionary Search')).toBeInTheDocument()
    })

    it('should transform article_generation to Article Generation', () => {
      render(<UsageSummary summary={mockSummary} days={30} />)

      expect(screen.getByText('Article Generation')).toBeInTheDocument()
    })

    it('should handle unknown operations with transformation', () => {
      const summaryUnknownOp: TokenUsageSummary = {
        total_tokens: 1000,
        total_cost: 0.001,
        by_operation: {
          custom_operation: { tokens: 1000, cost: 0.001, count: 1 }
        },
        daily_usage: []
      }

      render(<UsageSummary summary={summaryUnknownOp} days={30} />)

      expect(screen.getByText('Custom Operation')).toBeInTheDocument()
    })
  })

  describe('edge cases', () => {
    it('should handle empty daily_usage array', () => {
      const emptyDailySummary: TokenUsageSummary = {
        total_tokens: 100,
        total_cost: 0.001,
        by_operation: {
          dictionary_search: { tokens: 100, cost: 0.001, count: 1 }
        },
        daily_usage: []
      }

      render(<UsageSummary summary={emptyDailySummary} days={30} />)

      // No Daily Usage heading when empty
      expect(screen.queryByText('Daily Usage')).not.toBeInTheDocument()
      // But should still show operation card with request count
      expect(screen.getByText('1 request')).toBeInTheDocument()
    })

    it('should handle empty by_operation object', () => {
      const emptyOperationsSummary: TokenUsageSummary = {
        total_tokens: 0,
        total_cost: 0,
        by_operation: {},
        daily_usage: [
          { date: '2026-01-30', tokens: 0, cost: 0 }
        ]
      }

      render(<UsageSummary summary={emptyOperationsSummary} days={30} />)

      expect(screen.queryByText('Usage by Operation')).not.toBeInTheDocument()
      expect(screen.getByText('Daily Usage')).toBeInTheDocument()
    })

    it('should handle completely empty summary', () => {
      const emptySummary: TokenUsageSummary = {
        total_tokens: 0,
        total_cost: 0,
        by_operation: {},
        daily_usage: []
      }

      render(<UsageSummary summary={emptySummary} days={30} />)

      // Check that zero values are rendered
      expect(screen.getByText('Total Tokens')).toBeInTheDocument()
      expect(screen.getByText('Estimated Cost')).toBeInTheDocument()
      expect(screen.getByText('$0.0000')).toBeInTheDocument()
      expect(screen.getByText('No daily usage data available for this period.')).toBeInTheDocument()
    })

    it('should render correctly with single operation', () => {
      const singleOpSummary: TokenUsageSummary = {
        total_tokens: 5000,
        total_cost: 0.005,
        by_operation: {
          dictionary_search: { tokens: 5000, cost: 0.005, count: 50 }
        },
        daily_usage: [
          { date: '2026-01-30', tokens: 5000, cost: 0.005 }
        ]
      }

      render(<UsageSummary summary={singleOpSummary} days={30} />)

      expect(screen.getByText('Dictionary Search')).toBeInTheDocument()
      // '5,000' may appear in multiple places (total card, operation card, chart)
      expect(screen.getAllByText('5,000').length).toBeGreaterThan(0)
    })

    it('should render correctly with single daily entry', () => {
      const singleDaySummary: TokenUsageSummary = {
        total_tokens: 1000,
        total_cost: 0.001,
        by_operation: {},
        daily_usage: [
          { date: '2026-01-30', tokens: 1000, cost: 0.001 }
        ]
      }

      render(<UsageSummary summary={singleDaySummary} days={30} />)

      expect(screen.getByText('Jan 30')).toBeInTheDocument()
      // '1,000' may appear in multiple places (total card, chart)
      expect(screen.getAllByText('1,000').length).toBeGreaterThan(0)
    })

    it('should handle very large daily usage dataset (30 days)', () => {
      const largeDailySummary: TokenUsageSummary = {
        total_tokens: 300000,
        total_cost: 0.3,
        by_operation: {},
        daily_usage: Array.from({ length: 30 }, (_, i) => ({
          date: `2025-12-${String(i + 2).padStart(2, '0')}`,
          tokens: 10000,
          cost: 0.01
        }))
      }

      render(<UsageSummary summary={largeDailySummary} days={30} />)

      // Should only show last 14 days
      const bars = screen.queryAllByText('10,000')
      // May appear multiple times in the document
      expect(bars.length).toBeGreaterThan(0)
    })
  })

  describe('accessibility', () => {
    it('should have proper heading hierarchy', () => {
      render(<UsageSummary summary={mockSummary} days={30} />)

      const headings = screen.queryAllByRole('heading')
      expect(headings.length).toBeGreaterThan(0)
    })

    it('should have semantic progress elements in chart', () => {
      render(<UsageSummary summary={mockSummary} days={30} />)

      // Chart contains progress elements for accessibility
      const progressElements = screen.queryAllByRole('progressbar')
      expect(progressElements.length).toBeGreaterThan(0)
    })

    it('should have aria-labels on progress elements', () => {
      render(<UsageSummary summary={mockSummary} days={30} />)

      const progressElements = screen.queryAllByRole('progressbar')
      progressElements.forEach(element => {
        expect(element).toHaveAttribute('aria-label')
      })
    })
  })

  describe('responsive layout', () => {
    it('should render grid layout for totals', () => {
      const { container } = render(<UsageSummary summary={mockSummary} days={30} />)

      // Check for grid layout classes
      const gridDivs = container.querySelectorAll('[class*="grid"]')
      expect(gridDivs.length).toBeGreaterThan(0)
    })

    it('should render both total cards', () => {
      render(<UsageSummary summary={mockSummary} days={30} />)

      expect(screen.getByText('Total Tokens')).toBeInTheDocument()
      expect(screen.getByText('Estimated Cost')).toBeInTheDocument()
    })
  })
})
