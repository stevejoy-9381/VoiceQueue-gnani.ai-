import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import AboutPage from './AboutPage.jsx'

describe('AboutPage Component Tests (Phase P2-6)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('1. Displays "Reviewed by a native speaker" line when reviewed.json covers all strings', async () => {
    globalThis.fetch = vi.fn().mockImplementation((url) => {
      if (url.includes('/health')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            status: 'ok',
            telugu_reviewed: true,
            groq_configured: false,
          }),
        })
      }
      if (url.includes('/telugu-review-status')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            all_reviewed: true,
            reviewed_by_native_speaker: true,
          }),
        })
      }
      if (url.includes('/voice-tests/summary')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve({ total_trials: 0, breakdown: [] }) })
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) })
    })

    render(<AboutPage onNavigate={vi.fn()} />)

    await waitFor(() => {
      const line = screen.getByTestId('telugu-reviewed-line')
      expect(line).toBeInTheDocument()
      expect(line.textContent).toMatch(/reviewed by a native speaker/i)
    })
  })

  it('2. Shows NOTHING when reviewed.json does not cover all strings', async () => {
    globalThis.fetch = vi.fn().mockImplementation((url) => {
      if (url.includes('/health')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            status: 'ok',
            telugu_reviewed: false,
            groq_configured: false,
          }),
        })
      }
      if (url.includes('/telugu-review-status')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            all_reviewed: false,
            reviewed_by_native_speaker: false,
          }),
        })
      }
      if (url.includes('/voice-tests/summary')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve({ total_trials: 0, breakdown: [] }) })
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) })
    })

    render(<AboutPage onNavigate={vi.fn()} />)

    // Wait for fetch calls to complete
    await waitFor(() => {
      expect(screen.queryByTestId('telugu-reviewed-line')).not.toBeInTheDocument()
    })
    expect(screen.queryByText(/reviewed by a native speaker/i)).not.toBeInTheDocument()
  })
})

