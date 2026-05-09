/* eslint-disable unicorn/prefer-global-this, @typescript-eslint/no-explicit-any, sonarjs/no-duplicate-string */
/**
 * Tests for API client utilities.
 * Note: Using `global.fetch` for mocking is standard practice in tests
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { parseErrorResponse, fetchWithAuth } from '../api'
import { getToken } from '../auth'

// Mock the auth module
vi.mock('../auth', () => ({
  getToken: vi.fn()
}))

describe('api', () => {
  describe('parseErrorResponse', () => {
    describe('error field extraction', () => {
      it('should extract error message from error field', async () => {
        const mockResponse = {
          json: vi.fn().mockResolvedValue({
            error: 'Custom error message'
          })
        } as any

        const result = await parseErrorResponse(mockResponse)

        expect(result).toBe('Custom error message')
      })

      it('should prioritize error field over detail', async () => {
        const mockResponse = {
          json: vi.fn().mockResolvedValue({
            error: 'Error message',
            detail: 'Detail message'
          })
        } as any

        const result = await parseErrorResponse(mockResponse)

        expect(result).toBe('Error message')
      })

      it('should prioritize error field over message', async () => {
        const mockResponse = {
          json: vi.fn().mockResolvedValue({
            error: 'Error message',
            message: 'Message text'
          })
        } as any

        const result = await parseErrorResponse(mockResponse)

        expect(result).toBe('Error message')
      })
    })

    describe('detail field extraction', () => {
      it('should extract error message from detail field', async () => {
        const mockResponse = {
          json: vi.fn().mockResolvedValue({
            detail: 'Detail error message'
          })
        } as any

        const result = await parseErrorResponse(mockResponse)

        expect(result).toBe('Detail error message')
      })

      it('should prioritize detail over message', async () => {
        const mockResponse = {
          json: vi.fn().mockResolvedValue({
            detail: 'Detail message',
            message: 'Message text'
          })
        } as any

        const result = await parseErrorResponse(mockResponse)

        expect(result).toBe('Detail message')
      })
    })

    describe('message field extraction', () => {
      it('should extract error message from message field', async () => {
        const mockResponse = {
          json: vi.fn().mockResolvedValue({
            message: 'Message error'
          })
        } as any

        const result = await parseErrorResponse(mockResponse)

        expect(result).toBe('Message error')
      })
    })

    describe('default message handling', () => {
      it('should return default message when no error fields present', async () => {
        const mockResponse = {
          json: vi.fn().mockResolvedValue({
            data: 'some data'
          })
        } as any

        const result = await parseErrorResponse(mockResponse, 'Custom default')

        expect(result).toBe('Custom default')
      })

      it('should use default "An error occurred" message', async () => {
        const mockResponse = {
          json: vi.fn().mockResolvedValue({})
        } as any

        const result = await parseErrorResponse(mockResponse)

        expect(result).toBe('An error occurred')
      })

      it('should use provided default message when response body is not JSON', async () => {
        const mockResponse = {
          json: vi.fn().mockRejectedValue(new Error('Invalid JSON'))
        } as any

        const result = await parseErrorResponse(mockResponse, 'Failed to parse response')

        expect(result).toBe('Failed to parse response')
      })
    })

    describe('error handling', () => {
      it('should handle JSON parse errors gracefully', async () => {
        const mockResponse = {
          json: vi.fn().mockRejectedValue(new SyntaxError('Unexpected token'))
        } as any

        const result = await parseErrorResponse(mockResponse, 'Parse failed')

        expect(result).toBe('Parse failed')
      })

      it('should handle network errors gracefully', async () => {
        const mockResponse = {
          json: vi.fn().mockRejectedValue(new Error('Network error'))
        } as any

        const result = await parseErrorResponse(mockResponse)

        expect(result).toBe('An error occurred')
      })

      it('should handle response.json() throwing unknown errors', async () => {
        const mockResponse = {
          json: vi.fn().mockRejectedValue(new Error('Unknown error'))
        } as any

        const result = await parseErrorResponse(mockResponse, 'Custom error')

        expect(result).toBe('Custom error')
      })
    })

    describe('edge cases', () => {
      it('should handle empty error string', async () => {
        const mockResponse = {
          json: vi.fn().mockResolvedValue({
            error: ''
          })
        } as any

        const result = await parseErrorResponse(mockResponse, 'Default')

        // Empty string is falsy but should still be returned from error field
        expect(result).toBe('Default')
      })

      it('should handle null error field', async () => {
        const mockResponse = {
          json: vi.fn().mockResolvedValue({
            error: null,
            detail: 'Detail message'
          })
        } as any

        const result = await parseErrorResponse(mockResponse)

        expect(result).toBe('Detail message')
      })

      it('should handle undefined error field', async () => {
        const mockResponse = {
          json: vi.fn().mockResolvedValue({
            error: undefined,
            detail: 'Detail message'
          })
        } as any

        const result = await parseErrorResponse(mockResponse)

        expect(result).toBe('Detail message')
      })

      it('should handle error field with zero', async () => {
        const mockResponse = {
          json: vi.fn().mockResolvedValue({
            error: 0
          })
        } as any

        const result = await parseErrorResponse(mockResponse)

        // 0 is falsy, should check detail/message
        expect(result).toBe('An error occurred')
      })

      it('should handle error field with false', async () => {
        const mockResponse = {
          json: vi.fn().mockResolvedValue({
            error: false,
            detail: 'Detail'
          })
        } as any

        const result = await parseErrorResponse(mockResponse)

        // false is falsy, should check detail
        expect(result).toBe('Detail')
      })

      it('should handle error field with array', async () => {
        const mockResponse = {
          json: vi.fn().mockResolvedValue({
            error: ['error1', 'error2']
          })
        } as any

        const result = await parseErrorResponse(mockResponse)

        // Array is truthy
        expect(result).toEqual(['error1', 'error2'])
      })

      it('should handle very long error message', async () => {
        const longError = 'a'.repeat(10000)
        const mockResponse = {
          json: vi.fn().mockResolvedValue({
            error: longError
          })
        } as any

        const result = await parseErrorResponse(mockResponse)

        expect(result).toBe(longError)
      })

      it('should handle error message with special characters', async () => {
        const specialError = 'Error: "quotes" & <tags> \n newlines'
        const mockResponse = {
          json: vi.fn().mockResolvedValue({
            error: specialError
          })
        } as any

        const result = await parseErrorResponse(mockResponse)

        expect(result).toBe(specialError)
      })

      it('should handle error message with unicode', async () => {
        const unicodeError = 'Error: 你好 🚀 مرحبا'
        const mockResponse = {
          json: vi.fn().mockResolvedValue({
            error: unicodeError
          })
        } as any

        const result = await parseErrorResponse(mockResponse)

        expect(result).toBe(unicodeError)
      })

      it('should handle multiple nested fields', async () => {
        const mockResponse = {
          json: vi.fn().mockResolvedValue({
            error: null,
            detail: null,
            message: null,
            meta: {
              error: 'Nested error'
            }
          })
        } as any

        const result = await parseErrorResponse(mockResponse, 'Default message')

        expect(result).toBe('Default message')
      })

      it('should handle response with all error fields populated', async () => {
        const mockResponse = {
          json: vi.fn().mockResolvedValue({
            error: 'Error',
            detail: 'Detail',
            message: 'Message'
          })
        } as any

        const result = await parseErrorResponse(mockResponse)

        expect(result).toBe('Error')
      })
    })

    describe('return value type', () => {
      it('should always return a string', async () => {
        const testCases = [
          { error: 'string error' },
          { detail: 'string detail' },
          { message: 'string message' },
          {}
        ]

        for (const testCase of testCases) {
          const mockResponse = {
            json: vi.fn().mockResolvedValue(testCase)
          } as any

          const result = await parseErrorResponse(mockResponse, 'default')

          expect(typeof result).toBe('string')
        }
      })

      it('should handle custom default message types correctly', async () => {
        const mockResponse = {
          json: vi.fn().mockRejectedValue(new Error('Parse error'))
        } as any

        const customDefault = 'Operation failed: timeout'
        const result = await parseErrorResponse(mockResponse, customDefault)

        expect(result).toBe(customDefault)
      })
    })
  })

  describe('fetchWithAuth', () => {
    beforeEach(() => {
      vi.clearAllMocks()
      global.fetch = vi.fn()
    })

    afterEach(() => {
      vi.clearAllMocks()
    })

    it('should make fetch request with Authorization header when token exists', async () => {
      vi.mocked(getToken).mockReturnValue('test-token-123')
      global.fetch = vi.fn().mockResolvedValue({ ok: true })

      await fetchWithAuth('/api/endpoint')

      expect(global.fetch).toHaveBeenCalledWith('/api/endpoint', {
        headers: {
          'Authorization': 'Bearer test-token-123'
        }
      })
    })

    it('should make fetch request without Authorization header when token is null', async () => {
      vi.mocked(getToken).mockReturnValue(null)
      global.fetch = vi.fn().mockResolvedValue({ ok: true })

      await fetchWithAuth('/api/endpoint')

      expect(global.fetch).toHaveBeenCalledWith('/api/endpoint', {
        headers: {}
      })
    })

    it('should preserve existing headers', async () => {
      vi.mocked(getToken).mockReturnValue('test-token')
      global.fetch = vi.fn().mockResolvedValue({ ok: true })

      await fetchWithAuth('/api/endpoint', {
        headers: {
          'Content-Type': 'application/json'
        }
      })

      expect(global.fetch).toHaveBeenCalledWith('/api/endpoint', {
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer test-token'
        }
      })
    })

    it('should merge headers correctly', async () => {
      vi.mocked(getToken).mockReturnValue('my-token')
      global.fetch = vi.fn().mockResolvedValue({ ok: true })

      await fetchWithAuth('/api/test', {
        method: 'POST',
        headers: {
          'X-Custom-Header': 'custom-value'
        }
      })

      const callArgs = (global.fetch as any).mock.calls[0]
      expect(callArgs[1].headers).toEqual({
        'X-Custom-Header': 'custom-value',
        'Authorization': 'Bearer my-token'
      })
    })

    it('should preserve other request options', async () => {
      vi.mocked(getToken).mockReturnValue('token')
      global.fetch = vi.fn().mockResolvedValue({ ok: true })

      await fetchWithAuth('/api/endpoint', {
        method: 'POST',
        body: JSON.stringify({ test: 'data' })
      })

      const callArgs = (global.fetch as any).mock.calls[0]
      expect(callArgs[1].method).toBe('POST')
      expect(callArgs[1].body).toBe(JSON.stringify({ test: 'data' }))
    })

    it('should return fetch response', async () => {
      vi.mocked(getToken).mockReturnValue('token')
      const mockResponse = { ok: true, status: 200 }
      global.fetch = vi.fn().mockResolvedValue(mockResponse)

      const result = await fetchWithAuth('/api/endpoint')

      expect(result).toBe(mockResponse)
    })

    it('should work with POST requests', async () => {
      vi.mocked(getToken).mockReturnValue('test-token')
      global.fetch = vi.fn().mockResolvedValue({ ok: true })

      await fetchWithAuth('/api/endpoint', {
        method: 'POST',
        body: 'test-body'
      })

      const callArgs = (global.fetch as any).mock.calls[0]
      expect(callArgs[1].method).toBe('POST')
      expect(callArgs[1].body).toBe('test-body')
      expect(callArgs[1].headers['Authorization']).toBe('Bearer test-token')
    })

    it('should work with PUT requests', async () => {
      vi.mocked(getToken).mockReturnValue('test-token')
      global.fetch = vi.fn().mockResolvedValue({ ok: true })

      await fetchWithAuth('/api/endpoint', {
        method: 'PUT'
      })

      const callArgs = (global.fetch as any).mock.calls[0]
      expect(callArgs[1].method).toBe('PUT')
      expect(callArgs[1].headers['Authorization']).toBe('Bearer test-token')
    })

    it('should work with DELETE requests', async () => {
      vi.mocked(getToken).mockReturnValue('test-token')
      global.fetch = vi.fn().mockResolvedValue({ ok: true })

      await fetchWithAuth('/api/endpoint', {
        method: 'DELETE'
      })

      const callArgs = (global.fetch as any).mock.calls[0]
      expect(callArgs[1].method).toBe('DELETE')
    })
  })
})
