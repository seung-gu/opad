/* eslint-disable unicorn/prefer-global-this */
/**
 * Test setup and global configuration for Vitest
 * Note: Using `window` directly for mocking is intentional in test setup
 */

import { afterEach, vi } from 'vitest'

/**
 * Clean up after each test
 */
afterEach(() => {
  vi.clearAllMocks()
})

/**
 * Mock window.matchMedia for responsive design tests
 */
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

/**
 * Mock localStorage for tests
 */
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
}

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
})

/**
 * Mock sessionStorage for tests
 */
const sessionStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
}

Object.defineProperty(window, 'sessionStorage', {
  value: sessionStorageMock,
})

