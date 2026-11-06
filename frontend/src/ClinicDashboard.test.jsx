import React from 'react'
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import ClinicDashboard from './ClinicDashboard.jsx'

describe('ClinicDashboard Component Tests (Vitest + RTL)', () => {
  const mockQueueData = {
    date: '2026-11-06',
    total_tokens: 4,
    waiting_count: 2,
    current_in_consult: {
      id: 101,
      number: 1,
      date: '2026-11-06',
      label: 'Demo Patient 1',
      language: 'te-IN',
      status: 'in_consult',
    },
    tokens: [
      { id: 101, number: 1, date: '2026-11-06', label: 'Demo Patient 1', language: 'te-IN', status: 'in_consult' },
      { id: 102, number: 2, date: '2026-11-06', label: 'Demo Patient 2', language: 'en-IN', status: 'waiting' },
      { id: 103, number: 3, date: '2026-11-06', label: 'Demo Patient 3', language: 'mix-IN', status: 'waiting' },
      { id: 104, number: 4, date: '2026-11-06', label: 'Demo Patient 4', language: 'te-IN', status: 'done' },
      { id: 105, number: 5, date: '2026-11-06', label: 'Demo Patient 5', language: 'en-IN', status: 'cancelled' },
    ],
  }

  const mockVoiceLogs = [
    {
      id: 1,
      time: '10:15:30',
      transcript: 'My name is [name] and phone is [masked]',
      detected_language: 'te-IN',
      intent: 'BOOK',
      token_number: 102,
      ok: true,
      error: null,
    },
    {
      id: 2,
      time: '10:18:45',
      transcript: '[masked] turn failed',
      detected_language: 'en-IN',
      intent: 'UNKNOWN',
      token_number: null,
      ok: false,
      error: 'too_quiet',
      error_code: 'too_quiet',
    },
  ]

  beforeEach(() => {
    vi.restoreAllMocks()
    window.history.pushState({}, '', '/clinic')

    global.fetch = vi.fn((url) => {
      const u = url.toString()
      if (u.includes('/queue?day=')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve(mockQueueData),
        })
      }
      if (u.includes('/voice-logs')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve(mockVoiceLogs),
        })
      }
      if (u.includes('/usage')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve({ limit: 150, real_calls_today: 12, reserve: 40 }),
        })
      }
      if (u.includes('/queue/next')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve({ id: 102, number: 2 }),
        })
      }
      if (u.includes('/done')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve({ ok: true }),
        })
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({}),
      })
    })

    // Mock WebSocket
    global.WebSocket = vi.fn().mockImplementation(() => ({
      send: vi.fn(),
      close: vi.fn(),
      onopen: null,
      onclose: null,
      onmessage: null,
      onerror: null,
    }))
  })

  it('1. Shows friendly language names (Telugu, English, Mix) instead of te-IN and en-IN', async () => {
    render(<ClinicDashboard />)

    await waitFor(() => {
      expect(screen.getByText('Demo Patient 1')).toBeInTheDocument()
    })

    // Check language labels
    expect(screen.getAllByText('Telugu').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('English').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('Mix').length).toBeGreaterThanOrEqual(1)

    // Ensure raw te-IN / en-IN are NOT rendered
    expect(screen.queryByText('te-IN')).toBeNull()
    expect(screen.queryByText('en-IN')).toBeNull()
  })

  it("2. Labels waiting rows 'Position N - Token M'", async () => {
    render(<ClinicDashboard />)

    await waitFor(() => {
      expect(screen.getByText('Position 1 - Token 2')).toBeInTheDocument()
      expect(screen.getByText('Position 2 - Token 3')).toBeInTheDocument()
    })
  })

  it('3. Displays live status indicator and last updated time', async () => {
    render(<ClinicDashboard />)

    await waitFor(() => {
      expect(screen.getByText(/Last updated:/i)).toBeInTheDocument()
    })
  })

  it('4. Renders summary counters matching the queue data', async () => {
    render(<ClinicDashboard />)

    // Wait for async queue data to load and display counter values
    await waitFor(() => {
      expect(screen.getByText('2')).toBeInTheDocument() // Waiting: 2
    })

    expect(screen.getAllByText('Waiting').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('In Consultation')).toBeInTheDocument()
    expect(screen.getByText('Done Today')).toBeInTheDocument()
    expect(screen.getByText('Cancelled')).toBeInTheDocument()

    // In Consult: 1, Done Today: 1, Cancelled: 1
    const ones = screen.getAllByText('1')
    expect(ones.length).toBeGreaterThanOrEqual(3)
  })

  it('5. In presentation mode (?present=1), hides Seed, Reset and badges, while keeping Call next', async () => {
    window.history.pushState({}, '', '/clinic?present=1')
    render(<ClinicDashboard />)

    await waitFor(() => {
      expect(screen.getByText(/Call Next Patient/i)).toBeInTheDocument()
    })

    // Seed and Reset buttons should be hidden
    expect(screen.queryByText(/Seed Demo Data/i)).toBeNull()
    expect(screen.queryByText(/Reset Demo/i)).toBeNull()
    expect(screen.queryByText(/Gnani calls:/i)).toBeNull()
  })

  it('6. Keyboard shortcuts: N calls next patient, D marks in-consult token done', async () => {
    render(<ClinicDashboard />)

    await waitFor(() => {
      expect(screen.getByText('Demo Patient 1')).toBeInTheDocument()
    })

    // Check hint line is present
    expect(screen.getByText(/Shortcuts: Press/i)).toBeInTheDocument()

    // Press N
    fireEvent.keyDown(window, { key: 'n' })
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(expect.stringContaining('/queue/next'), expect.anything())
    })

    // Press D
    fireEvent.keyDown(window, { key: 'd' })
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(expect.stringContaining('/101/done'), expect.anything())
    })
  })

  it('7. Displays friendly empty state when no patients are waiting', async () => {
    global.fetch = vi.fn((url) => {
      if (url.toString().includes('/queue')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve({ tokens: [], current_in_consult: null }),
        })
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve([]),
      })
    })

    render(<ClinicDashboard />)

    await waitFor(() => {
      expect(screen.getByText('No patients waiting.')).toBeInTheDocument()
      expect(screen.getByText('No patient currently in consultation.')).toBeInTheDocument()
    })
  })

  it('8. Voice Activity Feed shows masked transcripts and error badge for failed turns', async () => {
    render(<ClinicDashboard />)

    await waitFor(() => {
      expect(screen.getByText(/"My name is \[name\] and phone is \[masked\]"/i)).toBeInTheDocument()
      expect(screen.getByText(/too quiet/i)).toBeInTheDocument()
    })
  })
})

