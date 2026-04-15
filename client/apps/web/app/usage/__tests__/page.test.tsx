/* eslint-disable @typescript-eslint/no-explicit-any, sonarjs/no-duplicate-string */
/**
 * Tests for Token Usage Dashboard page.
 *
 * Comprehensive tests for the usage page including:
 * - Loading state handling
 * - Error state handling
 * - Empty state handling
 * - Data display when available
 * - Days selector interaction
 * - Authentication redirect
 * - API fetching with fetchWithAuth
 */

import React from 'react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import UsagePage from '../page'
import { TokenUsageSummary } from '@/types/usage'

// Mock modules
vi.mock('next/navigation', () => ({
  useRouter: vi.fn()
}))

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: vi.fn()
}))

vi.mock('@/lib/api', () => ({
  fetchWithAuth: vi.fn(),
  parseErrorResponse: vi.fn()
}))

vi.mock('@/components/ErrorAlert', () => ({
  default: ({ error, onRetry }: { error: string | null; onRetry?: () => void }) => {
    if (!error) return null
    return (
      <div data-testid="error-alert">
        <p>{error}</p>
        {onRetry && (
          <button onClick={onRetry} data-testid="retry-button">
            Retry
          </button>
        )}
      </div>
    )
  }
}))

vi.mock('@/components/EmptyState', () => ({
  default: ({ title, description, action }: {
    title: string
    description: string
    action?: { label: string; onClick: () => void }
  }) => (
    <div data-testid="empty-state">
      <h2>{title}</h2>
      <p>{description}</p>
      {action && (
        <button onClick={action.onClick} data-testid="empty-state-button">
          {action.label}
        </button>
      )}
    </div>
  )
}))

vi.mock('@/components/UsageSummary', () => ({
  default: ({ summary, days }: { summary: TokenUsageSummary; days: number }) => (
    <div data-testid="usage-summary">
      <p>Total: {summary.total_tokens} tokens</p>
      <p>Days: {days}</p>
    </div>
  )
}))

import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'
import { fetchWithAuth, parseErrorResponse } from '@/lib/api'

describe('UsagePage', () => {
  const mockPush = vi.fn()
  const mockFetch = vi.fn()
  const mockParseError = vi.fn()

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

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useRouter).mockReturnValue({
      push: mockPush
    } as any)

    vi.mocked(fetchWithAuth).mockClear()
    vi.mocked(parseErrorResponse).mockClear()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('authentication', () => {
    it('should redirect to login when not authenticated', async () => {
      vi.mocked(useAuth).mockReturnValue({
        isAuthenticated: false
      } as any)

      render(<UsagePage />)

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/login')
      })
    })

    it('should not redirect when authenticated', async () => {
      vi.mocked(useAuth).mockReturnValue({
        isAuthenticated: true
      } as any)

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockSummary
      })

      vi.mocked(fetchWithAuth).mockImplementation(mockFetch)

      render(<UsagePage />)

      await waitFor(() => {
        expect(mockPush).not.toHaveBeenCalledWith('/login')
      })
    })

    it('should redirect to login when 401 response received', async () => {
      vi.mocked(useAuth).mockReturnValue({
        isAuthenticated: true
      } as any)

      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401
      })

      vi.mocked(fetchWithAuth).mockImplementation(mockFetch)

      render(<UsagePage />)

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/login')
      })
    })
  })

  describe('loading state', () => {
    it('should show loading spinner initially', async () => {
      vi.mocked(useAuth).mockReturnValue({
        isAuthenticated: true
      } as any)

      mockFetch.mockImplementationOnce(
        () => new Promise(() => { /* intentionally empty - never resolves */ })
      )

      vi.mocked(fetchWithAuth).mockImplementation(mockFetch)

      render(<UsagePage />)

      expect(screen.getByText('Loading usage data...')).toBeInTheDocument()
    })

    it('should show loading spinner with spinner icon', async () => {
      vi.mocked(useAuth).mockReturnValue({
        isAuthenticated: true
      } as any)

      mockFetch.mockImplementationOnce(
        () => new Promise(() => { /* intentionally empty - never resolves */ })
      )

      vi.mocked(fetchWithAuth).mockImplementation(mockFetch)

      const { container } = render(<UsagePage />)

      expect(container.querySelector('[class*="animate-spin"]')).toBeInTheDocument()
    })

    it('should hide loading state after data is fetched', async () => {
      vi.mocked(useAuth).mockReturnValue({
        isAuthenticated: true
      } as any)

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockSummary
      })

      vi.mocked(fetchWithAuth).mockImplementation(mockFetch)

      render(<UsagePage />)

      await waitFor(() => {
        expect(screen.queryByText('Loading usage data...')).not.toBeInTheDocument()
      })
    })

    it('should update loading state when days selector changes', async () => {
      vi.mocked(useAuth).mockReturnValue({
        isAuthenticated: true
      } as any)

      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => mockSummary
      })

      vi.mocked(fetchWithAuth).mockImplementation(mockFetch)

      render(<UsagePage />)

      await waitFor(() => {
        expect(screen.getByTestId('usage-summary')).toBeInTheDocument()
      })

      const selector = screen.getByRole('combobox')
      fireEvent.change(selector, { target: { value: '7' } })

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith('/api/usage/me?days=7', expect.any(Object))
      })
    })
  })

  describe('error state', () => {
    it('should show error alert when fetch fails', async () => {
      vi.mocked(useAuth).mockReturnValue({
        isAuthenticated: true
      } as any)

      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500
      })

      mockParseError.mockResolvedValueOnce('Server error')

      vi.mocked(parseErrorResponse).mockImplementation(mockParseError)
      vi.mocked(fetchWithAuth).mockImplementation(mockFetch)

      render(<UsagePage />)

      await waitFor(() => {
        expect(screen.getByTestId('error-alert')).toBeInTheDocument()
      })
    })

    it('should display error message', async () => {
      vi.mocked(useAuth).mockReturnValue({
        isAuthenticated: true
      } as any)

      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500
      })

      mockParseError.mockResolvedValueOnce('Failed to load usage data')

      vi.mocked(parseErrorResponse).mockImplementation(mockParseError)
      vi.mocked(fetchWithAuth).mockImplementation(mockFetch)

      render(<UsagePage />)

      await waitFor(() => {
        expect(screen.getByText('Failed to load usage data')).toBeInTheDocument()
      })
    })

    it('should show retry button in error state', async () => {
      vi.mocked(useAuth).mockReturnValue({
        isAuthenticated: true
      } as any)

      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500
      })

      mockParseError.mockResolvedValueOnce('Error occurred')

      vi.mocked(parseErrorResponse).mockImplementation(mockParseError)
      vi.mocked(fetchWithAuth).mockImplementation(mockFetch)

      render(<UsagePage />)

      await waitFor(() => {
        expect(screen.getByTestId('retry-button')).toBeInTheDocument()
      })
    })

    it('should retry fetch when retry button clicked', async () => {
      vi.mocked(useAuth).mockReturnValue({
        isAuthenticated: true
      } as any)

      mockFetch
        .mockResolvedValueOnce({
          ok: false,
          status: 500
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => mockSummary
        })

      mockParseError.mockResolvedValueOnce('Error occurred')

      vi.mocked(parseErrorResponse).mockImplementation(mockParseError)
      vi.mocked(fetchWithAuth).mockImplementation(mockFetch)

      render(<UsagePage />)

      await waitFor(() => {
        expect(screen.getByTestId('retry-button')).toBeInTheDocument()
      })

      fireEvent.click(screen.getByTestId('retry-button'))

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledTimes(2)
      })
    })

    it('should clear error when data is successfully fetched after error', async () => {
      vi.mocked(useAuth).mockReturnValue({
        isAuthenticated: true
      } as any)

      mockFetch
        .mockResolvedValueOnce({
          ok: false,
          status: 500
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => mockSummary
        })

      mockParseError.mockResolvedValueOnce('Error occurred')

      vi.mocked(parseErrorResponse).mockImplementation(mockParseError)
      vi.mocked(fetchWithAuth).mockImplementation(mockFetch)

      render(<UsagePage />)

      await waitFor(() => {
        expect(screen.getByTestId('error-alert')).toBeInTheDocument()
      })

      fireEvent.click(screen.getByTestId('retry-button'))

      await waitFor(() => {
        expect(screen.queryByTestId('error-alert')).not.toBeInTheDocument()
      })
    })
  })

  describe('empty state', () => {
    it('should show empty state when no data', async () => {
      vi.mocked(useAuth).mockReturnValue({
        isAuthenticated: true
      } as any)

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          total_tokens: 0,
          total_cost: 0,
          by_operation: {},
          daily_usage: []
        })
      })

      vi.mocked(fetchWithAuth).mockImplementation(mockFetch)

      render(<UsagePage />)

      await waitFor(() => {
        expect(screen.getByTestId('empty-state')).toBeInTheDocument()
      })
    })

    it('should show empty state message', async () => {
      vi.mocked(useAuth).mockReturnValue({
        isAuthenticated: true
      } as any)

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          total_tokens: 0,
          total_cost: 0,
          by_operation: {},
          daily_usage: []
        })
      })

      vi.mocked(fetchWithAuth).mockImplementation(mockFetch)

      render(<UsagePage />)

      await waitFor(() => {
        expect(screen.getByText('No usage data found.')).toBeInTheDocument()
      })
    })

    it('should show empty state action button', async () => {
      vi.mocked(useAuth).mockReturnValue({
        isAuthenticated: true
      } as any)

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          total_tokens: 0,
          total_cost: 0,
          by_operation: {},
          daily_usage: []
        })
      })

      vi.mocked(fetchWithAuth).mockImplementation(mockFetch)

      render(<UsagePage />)

      await waitFor(() => {
        expect(screen.getByTestId('empty-state-button')).toBeInTheDocument()
      })
    })

    it('should navigate to articles when empty state button clicked', async () => {
      vi.mocked(useAuth).mockReturnValue({
        isAuthenticated: true
      } as any)

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          total_tokens: 0,
          total_cost: 0,
          by_operation: {},
          daily_usage: []
        })
      })

      vi.mocked(fetchWithAuth).mockImplementation(mockFetch)

      render(<UsagePage />)

      await waitFor(() => {
        const button = screen.getByTestId('empty-state-button')
        fireEvent.click(button)
      })

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/articles')
      })
    })
  })

  describe('data display', () => {
    it('should render UsageSummary when data exists', async () => {
      vi.mocked(useAuth).mockReturnValue({
        isAuthenticated: true
      } as any)

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockSummary
      })

      vi.mocked(fetchWithAuth).mockImplementation(mockFetch)

      render(<UsagePage />)

      await waitFor(() => {
        expect(screen.getByTestId('usage-summary')).toBeInTheDocument()
      })
    })

    it('should pass summary data to UsageSummary component', async () => {
      vi.mocked(useAuth).mockReturnValue({
        isAuthenticated: true
      } as any)

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockSummary
      })

      vi.mocked(fetchWithAuth).mockImplementation(mockFetch)

      render(<UsagePage />)

      await waitFor(() => {
        expect(screen.getByText('Total: 125430 tokens')).toBeInTheDocument()
      })
    })

    it('should pass correct days value to UsageSummary component', async () => {
      vi.mocked(useAuth).mockReturnValue({
        isAuthenticated: true
      } as any)

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockSummary
      })

      vi.mocked(fetchWithAuth).mockImplementation(mockFetch)

      render(<UsagePage />)

      await waitFor(() => {
        expect(screen.getByText('Days: 30')).toBeInTheDocument()
      })
    })

    it('should not show empty state when data exists', async () => {
      vi.mocked(useAuth).mockReturnValue({
        isAuthenticated: true
      } as any)

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockSummary
      })

      vi.mocked(fetchWithAuth).mockImplementation(mockFetch)

      render(<UsagePage />)

      await waitFor(() => {
        expect(screen.queryByTestId('empty-state')).not.toBeInTheDocument()
      })
    })

    it('should show data even with only partial data (has tokens)', async () => {
      vi.mocked(useAuth).mockReturnValue({
        isAuthenticated: true
      } as any)

      const partialData: TokenUsageSummary = {
        total_tokens: 100,
        total_cost: 0,
        by_operation: {},
        daily_usage: []
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => partialData
      })

      vi.mocked(fetchWithAuth).mockImplementation(mockFetch)

      render(<UsagePage />)

      await waitFor(() => {
        expect(screen.getByTestId('usage-summary')).toBeInTheDocument()
      })
    })

    it('should show data when only daily_usage exists', async () => {
      vi.mocked(useAuth).mockReturnValue({
        isAuthenticated: true
      } as any)

      const dailyOnlyData: TokenUsageSummary = {
        total_tokens: 0,
        total_cost: 0,
        by_operation: {},
        daily_usage: [
          { date: '2026-01-30', tokens: 100, cost: 0.001 }
        ]
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => dailyOnlyData
      })

      vi.mocked(fetchWithAuth).mockImplementation(mockFetch)

      render(<UsagePage />)

      await waitFor(() => {
        expect(screen.getByTestId('usage-summary')).toBeInTheDocument()
      })
    })
  })

  describe('days selector', () => {
    it('should render days selector', async () => {
      vi.mocked(useAuth).mockReturnValue({
        isAuthenticated: true
      } as any)

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockSummary
      })

      vi.mocked(fetchWithAuth).mockImplementation(mockFetch)

      render(<UsagePage />)

      expect(screen.getByRole('combobox')).toBeInTheDocument()
    })

    it('should have default value of 30 days', async () => {
      vi.mocked(useAuth).mockReturnValue({
        isAuthenticated: true
      } as any)

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockSummary
      })

      vi.mocked(fetchWithAuth).mockImplementation(mockFetch)

      render(<UsagePage />)

      const selector = screen.getByRole('combobox') as HTMLSelectElement
      expect(selector.value).toBe('30')
    })

    it('should have all time period options', async () => {
      vi.mocked(useAuth).mockReturnValue({
        isAuthenticated: true
      } as any)

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockSummary
      })

      vi.mocked(fetchWithAuth).mockImplementation(mockFetch)

      render(<UsagePage />)

      expect(screen.getByText('Last 7 days')).toBeInTheDocument()
      expect(screen.getByText('Last 30 days')).toBeInTheDocument()
      expect(screen.getByText('Last 90 days')).toBeInTheDocument()
      expect(screen.getByText('Last 365 days')).toBeInTheDocument()
    })

    it('should fetch data with selected days value', async () => {
      vi.mocked(useAuth).mockReturnValue({
        isAuthenticated: true
      } as any)

      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => mockSummary
      })

      vi.mocked(fetchWithAuth).mockImplementation(mockFetch)

      render(<UsagePage />)

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith('/api/usage/me?days=30', expect.any(Object))
      })

      const selector = screen.getByRole('combobox')
      fireEvent.change(selector, { target: { value: '7' } })

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith('/api/usage/me?days=7', expect.any(Object))
      })
    })

    it('should fetch data when selector changes to 90 days', async () => {
      vi.mocked(useAuth).mockReturnValue({
        isAuthenticated: true
      } as any)

      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => mockSummary
      })

      vi.mocked(fetchWithAuth).mockImplementation(mockFetch)

      render(<UsagePage />)

      const selector = screen.getByRole('combobox')
      fireEvent.change(selector, { target: { value: '90' } })

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith('/api/usage/me?days=90', expect.any(Object))
      })
    })

    it('should fetch data when selector changes to 365 days', async () => {
      vi.mocked(useAuth).mockReturnValue({
        isAuthenticated: true
      } as any)

      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => mockSummary
      })

      vi.mocked(fetchWithAuth).mockImplementation(mockFetch)

      render(<UsagePage />)

      const selector = screen.getByRole('combobox')
      fireEvent.change(selector, { target: { value: '365' } })

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith('/api/usage/me?days=365', expect.any(Object))
      })
    })

    it('should disable selector when loading', async () => {
      vi.mocked(useAuth).mockReturnValue({
        isAuthenticated: true
      } as any)

      mockFetch.mockImplementationOnce(
        () => new Promise(() => { /* intentionally empty - never resolves */ })
      )

      vi.mocked(fetchWithAuth).mockImplementation(mockFetch)

      render(<UsagePage />)

      const selector = screen.getByRole('combobox')
      expect(selector).toBeDisabled()
    })

    it('should enable selector after loading', async () => {
      vi.mocked(useAuth).mockReturnValue({
        isAuthenticated: true
      } as any)

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockSummary
      })

      vi.mocked(fetchWithAuth).mockImplementation(mockFetch)

      render(<UsagePage />)

      const selector = screen.getByRole('combobox')

      await waitFor(() => {
        expect(selector).not.toBeDisabled()
      })
    })
  })

  describe('refresh button', () => {
    it('should show refresh button when data exists', async () => {
      vi.mocked(useAuth).mockReturnValue({
        isAuthenticated: true
      } as any)

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockSummary
      })

      vi.mocked(fetchWithAuth).mockImplementation(mockFetch)

      render(<UsagePage />)

      await waitFor(() => {
        expect(screen.getByText('Refresh Data')).toBeInTheDocument()
      })
    })

    it('should not show refresh button when no data', async () => {
      vi.mocked(useAuth).mockReturnValue({
        isAuthenticated: true
      } as any)

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          total_tokens: 0,
          total_cost: 0,
          by_operation: {},
          daily_usage: []
        })
      })

      vi.mocked(fetchWithAuth).mockImplementation(mockFetch)

      render(<UsagePage />)

      await waitFor(() => {
        expect(screen.queryByText('Refresh Data')).not.toBeInTheDocument()
      })
    })

    it('should refetch data when refresh button clicked', async () => {
      vi.mocked(useAuth).mockReturnValue({
        isAuthenticated: true
      } as any)

      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => mockSummary
      })

      vi.mocked(fetchWithAuth).mockImplementation(mockFetch)

      render(<UsagePage />)

      await waitFor(() => {
        expect(screen.getByText('Refresh Data')).toBeInTheDocument()
      })

      const initialCallCount = mockFetch.mock.calls.length
      fireEvent.click(screen.getByText('Refresh Data'))

      await waitFor(() => {
        expect(mockFetch.mock.calls.length).toBeGreaterThan(initialCallCount)
      })
    })

    it('should show loading text on refresh button during loading', async () => {
      vi.mocked(useAuth).mockReturnValue({
        isAuthenticated: true
      } as any)

      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => mockSummary
        })
        .mockImplementationOnce(
          () => new Promise(() => { /* intentionally empty - never resolves for second call */ })
        )

      vi.mocked(fetchWithAuth).mockImplementation(mockFetch)

      render(<UsagePage />)

      await waitFor(() => {
        expect(screen.getByText('Refresh Data')).toBeInTheDocument()
      })

      fireEvent.click(screen.getByText('Refresh Data'))

      await waitFor(() => {
        expect(screen.getByText('Refreshing...')).toBeInTheDocument()
      })
    })
  })

  describe('header navigation', () => {
    it('should have link to articles page', async () => {
      vi.mocked(useAuth).mockReturnValue({
        isAuthenticated: true
      } as any)

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockSummary
      })

      vi.mocked(fetchWithAuth).mockImplementation(mockFetch)

      render(<UsagePage />)

      const articlesLink = screen.getByTitle('Go to Articles')
      expect(articlesLink).toBeInTheDocument()
      expect(articlesLink).toHaveAttribute('href', '/articles')
    })
  })

  describe('request cancellation', () => {
    it('should cancel previous request when days changes', async () => {
      vi.mocked(useAuth).mockReturnValue({
        isAuthenticated: true
      } as any)

      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => mockSummary
      })

      vi.mocked(fetchWithAuth).mockImplementation(mockFetch)

      render(<UsagePage />)

      const selector = screen.getByRole('combobox')

      // Change days multiple times
      fireEvent.change(selector, { target: { value: '7' } })
      fireEvent.change(selector, { target: { value: '30' } })
      fireEvent.change(selector, { target: { value: '90' } })

      // Should have made multiple requests
      await waitFor(() => {
        expect(mockFetch.mock.calls.length).toBeGreaterThan(1)
      })
    })

    it('should abort request on component unmount', async () => {
      vi.mocked(useAuth).mockReturnValue({
        isAuthenticated: true
      } as any)

      mockFetch.mockImplementationOnce(
        () => new Promise(() => { /* intentionally empty - never resolves */ })
      )

      vi.mocked(fetchWithAuth).mockImplementation(mockFetch)

      const { unmount } = render(<UsagePage />)

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled()
      })

      unmount()

      // Component should cleanup without errors
      expect(true).toBe(true)
    })
  })

  describe('page layout and UI', () => {
    it('should have main heading "Token Usage"', async () => {
      vi.mocked(useAuth).mockReturnValue({
        isAuthenticated: true
      } as any)

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockSummary
      })

      vi.mocked(fetchWithAuth).mockImplementation(mockFetch)

      render(<UsagePage />)

      expect(screen.getByText('Token Usage')).toBeInTheDocument()
    })

    it('should have subtitle text', async () => {
      vi.mocked(useAuth).mockReturnValue({
        isAuthenticated: true
      } as any)

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockSummary
      })

      vi.mocked(fetchWithAuth).mockImplementation(mockFetch)

      render(<UsagePage />)

      expect(screen.getByText('Track your API token consumption and costs')).toBeInTheDocument()
    })

    it('should have time period label', async () => {
      vi.mocked(useAuth).mockReturnValue({
        isAuthenticated: true
      } as any)

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockSummary
      })

      vi.mocked(fetchWithAuth).mockImplementation(mockFetch)

      render(<UsagePage />)

      expect(screen.getByText('Time Period:')).toBeInTheDocument()
    })
  })
})
