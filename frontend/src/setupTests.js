import '@testing-library/jest-dom'
import { afterEach, vi } from 'vitest'
import { cleanup } from '@testing-library/react'

// Automatically clean up rendered DOM after each test
afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

// Mock window.HTMLMediaElement.prototype methods (play, pause, etc.) which jsdom doesn't implement
window.HTMLMediaElement.prototype.load = () => {}
window.HTMLMediaElement.prototype.play = () => Promise.resolve()
window.HTMLMediaElement.prototype.pause = () => {}

// Mock scrollTo
window.scrollTo = vi.fn()

// Mock matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query) => ({
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

// Mock WebSocket for happy-dom/jsdom if not present
if (typeof window.WebSocket === 'undefined') {
  class MockWebSocket {
    constructor(url) {
      this.url = url
      this.readyState = 1
      setTimeout(() => {
        if (this.onopen) this.onopen()
      }, 0)
    }
    send() {}
    close() {
      if (this.onclose) this.onclose()
    }
  }
  window.WebSocket = MockWebSocket
}

