import React from 'react'
import { render, screen, waitFor, cleanup, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import App from './App.jsx'

describe('Patient App Component Tests (Vitest + RTL)', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()

    // Default mocked health & usage endpoints
    global.fetch = vi.fn((url) => {
      const u = url.toString()
      if (u.includes('/health')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve({ gnani_configured: true, voices_valid: true }),
        })
      }
      if (u.includes('/usage')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve({ limit: 100, real_calls_today: 5 }),
        })
      }
      if (u.includes('/tokens/')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () =>
            Promise.resolve({
              id: 42,
              number: 3,
              date: new Date().toISOString().split('T')[0],
              status: 'waiting',
              ahead_count: 2,
            }),
        })
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({}),
      })
    })
  })

  it('1. Language switch toggles between Telugu, English, and Mix with correct UI text', async () => {
    render(<App />)

    // Wait for initial render (default Telugu)
    const teBtn = screen.getByRole('button', { name: 'తెలుగు' })
    const enBtn = screen.getByRole('button', { name: 'English' })
    const mixBtn = screen.getByRole('button', { name: 'Mix' })

    expect(teBtn).toHaveClass('active')
    expect(screen.getByText(/మీరు చెప్పినది/i)).toBeInTheDocument()

    // Switch to English
    await userEvent.click(enBtn)
    expect(enBtn).toHaveClass('active')
    expect(screen.getByText(/You said/i)).toBeInTheDocument()
    expect(screen.getByText(/Clinic Reply/i)).toBeInTheDocument()

    // Switch to Mix
    await userEvent.click(mixBtn)
    expect(mixBtn).toHaveClass('active')
    expect(screen.getByText(/You said \(మీరు చెప్పినది\)/i)).toBeInTheDocument()
  })

  it('2. Token card displays waiting and in_consult states accurately', async () => {
    const todayStr = new Date().toISOString().split('T')[0]

    // Pre-populate localStorage with a waiting token reply
    localStorage.setItem(
      'vq_last_reply',
      JSON.stringify({
        transcript: 'token kavali',
        reply_text: 'Your token number is 5',
        token: { id: 10, number: 5, date: todayStr, status: 'waiting', ahead_count: 3 },
      })
    )

    render(<App />)
    const enBtn = screen.getByRole('button', { name: 'English' })
    await userEvent.click(enBtn)

    // Waiting state
    expect(screen.getByText('#5')).toBeInTheDocument()
    expect(screen.getByText(/WAITING/i)).toBeInTheDocument()
    expect(screen.getByText(/Ahead in queue:/i)).toHaveTextContent('3')

    cleanup()

    // in_consult state
    localStorage.setItem(
      'vq_last_reply',
      JSON.stringify({
        token: { id: 10, number: 5, date: todayStr, status: 'in_consult', ahead_count: 0 },
      })
    )
    render(<App />)
    const enBtn2 = screen.getByRole('button', { name: 'English' })
    await userEvent.click(enBtn2)
    expect(screen.getByText(/Doctor is seeing you now!/i)).toBeInTheDocument()
  })

  it('3. Error banners render for missing key, invalid voice, and credit limit reached', async () => {
    global.fetch = vi.fn((url) => {
      const u = url.toString()
      if (u.includes('/health')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () =>
            Promise.resolve({
              gnani_configured: false,
              voices_valid: false,
              invalid_voice: 'InvalidVoice',
            }),
        })
      }
      if (u.includes('/usage')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve({ limit: 50, real_calls_today: 50 }),
        })
      }
      return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({}) })
    })

    render(<App />)

    // Missing key banner
    await waitFor(() => {
      expect(
        screen.getByText(/Gnani API key is missing. Add GNANI_API_KEY to backend\/\.env/i)
      ).toBeInTheDocument()
    })

    // Invalid voice banner
    expect(
      screen.getByText(/Voice InvalidVoice is not supported by timbre-v2\.5\. Fix backend\/\.env/i)
    ).toBeInTheDocument()

    // Credit limit banner
    expect(
      screen.getByText(/Voice is paused to save credits\. Typing still works\./i)
    ).toBeInTheDocument()
  })

  it('4. Confirm-cancel buttons appear and send YES/NO turn requests', async () => {
    global.fetch = vi.fn((url, options) => {
      const u = url.toString()
      if (u.includes('/text/turn')) {
        const body = JSON.parse(options.body)
        if (body.text === 'cancel') {
          return Promise.resolve({
            ok: true,
            status: 200,
            json: () =>
              Promise.resolve({
                transcript: 'cancel',
                reply_text: 'Are you sure you want to cancel?',
                intent: 'CANCEL',
                pending_confirm: true,
                token: { id: 7, number: 2, status: 'waiting' },
              }),
          })
        }
        if (body.text === 'yes') {
          return Promise.resolve({
            ok: true,
            status: 200,
            json: () =>
              Promise.resolve({
                transcript: 'yes',
                reply_text: 'Token 2 has been cancelled.',
                intent: 'YES',
                pending_confirm: false,
                token: { id: 7, number: 2, status: 'cancelled' },
              }),
          })
        }
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ gnani_configured: true, voices_valid: true }),
      })
    })

    render(<App />)

    // Switch to English for deterministic button and placeholder lookups
    await userEvent.click(screen.getByRole('button', { name: 'English' }))

    // Open typing box and send 'cancel'
    const typeAccordion = screen.getByText(/Type instead of speaking/i)
    await userEvent.click(typeAccordion)

    const input = screen.getByPlaceholderText(/need a token tomorrow/i)
    const sendBtn = screen.getByRole('button', { name: /Send/i })

    await userEvent.type(input, 'cancel')
    await userEvent.click(sendBtn)

    // Confirm cancel banner should appear with YES and NO buttons
    await waitFor(() => {
      expect(screen.getByText(/Do you want to cancel your token\?/i)).toBeInTheDocument()
    })

    const yesBtn = screen.getByRole('button', { name: /Yes/i })
    await userEvent.click(yesBtn)

    // Expect cancellation confirmation
    await waitFor(() => {
      expect(screen.getByText(/Token 2 has been cancelled/i)).toBeInTheDocument()
    })
  })

  it('5. Typed input path submits text and updates reply text without speaking', async () => {
    global.fetch = vi.fn((url) => {
      const u = url.toString()
      if (u.includes('/text/turn')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () =>
            Promise.resolve({
              transcript: 'repu token kavali',
              reply_text: 'Your token for tomorrow is number 8',
              token: { id: 8, number: 8, status: 'waiting', date: '2026-11-06' },
            }),
        })
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ gnani_configured: true, voices_valid: true }),
      })
    })

    render(<App />)

    // Switch to English
    await userEvent.click(screen.getByRole('button', { name: 'English' }))

    const typeAccordion = screen.getByText(/Type instead of speaking/i)
    await userEvent.click(typeAccordion)

    const input = screen.getByPlaceholderText(/need a token tomorrow/i)
    const sendBtn = screen.getByRole('button', { name: /Send/i })

    await userEvent.type(input, 'repu token kavali')
    await userEvent.click(sendBtn)

    await waitFor(() => {
      expect(screen.getByText(/Your token for tomorrow is number 8/i)).toBeInTheDocument()
    })
  })

  it('6. Stale token handling: a 404 response clears saved token, shows notice, and stops polling', async () => {
    localStorage.setItem('vq_token_id', '999')

    global.fetch = vi.fn((url) => {
      const u = url.toString()
      if (u.includes('/tokens/999')) {
        return Promise.resolve({
          ok: false,
          status: 404,
          json: () => Promise.resolve({ detail: 'Token not found.' }),
        })
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ gnani_configured: true, voices_valid: true }),
      })
    })

    render(<App />)

    // Once 404 is processed, token should be cleared and notice displayed
    await waitFor(() => {
      expect(localStorage.getItem('vq_token_id')).toBeNull()
      expect(screen.getByText(/Your token was cleared\. Say or type a request to book a new one\./i)).toBeInTheDocument()
    })
  })

  it('7. Demo reset WebSocket event clears saved token and displays cleared notice', async () => {
    localStorage.setItem('vq_token_id', '77')

    let wsInstance = null
    class TestWebSocket {
      constructor(url) {
        this.url = url
        wsInstance = this
      }
      close() {}
    }
    const origWS = window.WebSocket
    window.WebSocket = TestWebSocket

    render(<App />)

    // Simulate receiving demo_reset from server
    await waitFor(() => {
      expect(wsInstance).not.toBeNull()
    })

    act(() => {
      wsInstance.onmessage({
        data: JSON.stringify({ type: 'demo_reset' }),
      })
    })

    await waitFor(() => {
      expect(localStorage.getItem('vq_token_id')).toBeNull()
      expect(screen.getByText(/Your token was cleared\. Say or type a request to book a new one\./i)).toBeInTheDocument()
    })

    window.WebSocket = origWS
  })

  it('7b. P3-2: Token-called WebSocket event displays alert banner on patient page without refresh', async () => {
    localStorage.setItem('vq_token_id', '42')

    let wsInstance = null
    class TestWebSocket {
      constructor(url) {
        this.url = url
        wsInstance = this
      }
      close() {}
    }
    const origWS = window.WebSocket
    window.WebSocket = TestWebSocket

    render(<App />)

    await waitFor(() => {
      expect(wsInstance).not.toBeNull()
    })

    // Simulate receiving token_called event for this token
    act(() => {
      wsInstance.onmessage({
        data: JSON.stringify({ type: 'token_called', token_id: 42, token_number: 4 }),
      })
    })

    await waitFor(() => {
      expect(
        screen.getByText(/Your token is being called\. Please go in\.|మీ టోకెన్ పిలుస్తున్నారు\. దయచేసి లోపలికి వెళ్లండి\./i)
      ).toBeInTheDocument()
    })

    window.WebSocket = origWS
  })

  it('8. Error catalog maps all 16 error codes to bilingual messages and actions', async () => {
    const { EXPECTED_ERROR_CODES, getErrorDetails } = await import('./errorCatalog.js')
    expect(EXPECTED_ERROR_CODES).toHaveLength(16)

    for (const code of EXPECTED_ERROR_CODES) {
      const teEntry = getErrorDetails(code, 'te')
      expect(teEntry.code).toBe(code)
      expect(teEntry.message.length).toBeGreaterThan(0)
      expect(teEntry.suggestedAction.length).toBeGreaterThan(0)
      expect(['try_again', 'type_instead', 'book_new']).toContain(teEntry.actionType)

      const enEntry = getErrorDetails(code, 'en')
      expect(enEntry.code).toBe(code)
      expect(enEntry.message.length).toBeGreaterThan(0)
      expect(enEntry.suggestedAction.length).toBeGreaterThan(0)

      // No emojis or raw exception names
      expect(teEntry.message).not.toContain('⚠️')
      expect(enEntry.message).not.toContain('⚠️')
      expect(enEntry.message).not.toContain('HTTP')
      expect(enEntry.message).not.toContain('Traceback')
    }
  })

  it('9. Stubbed turn error displays friendly message and action button in plain icon-free style', async () => {
    global.fetch = vi.fn((url, options) => {
      const u = url.toString()
      if (u.includes('/text/turn')) {
        return Promise.resolve({
          ok: false,
          status: 500,
          json: () => Promise.resolve({ detail: 'Internal database lock deadlock', error_code: 'server_error' }),
        })
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ gnani_configured: true, voices_valid: true }),
      })
    })

    render(<App />)

    // Switch to English
    await userEvent.click(screen.getByRole('button', { name: 'English' }))

    // Open typing and submit
    const typeToggle = screen.getByText(/Type instead of speaking/i)
    await userEvent.click(typeToggle)

    const input = screen.getByPlaceholderText(/need a token tomorrow/i)
    await userEvent.type(input, 'repu token kavali')
    await userEvent.click(screen.getByRole('button', { name: /Send/i }))

    // Error alert renders friendly message and suggested action
    await waitFor(() => {
      const alert = screen.getByRole('alert')
      expect(alert).toBeInTheDocument()
      expect(alert).toHaveTextContent(/Server encountered an unexpected issue/i)
      expect(alert).toHaveTextContent(/Try again/i)
      // Icon-free
      expect(alert.textContent).not.toContain('⚠️')
      expect(alert.textContent).not.toContain('❌')
      // No raw trace or JSON leak
      expect(alert.textContent).not.toContain('deadlock')
      expect(alert.textContent).not.toContain('500')
    })
  })

  it('10. Technical details hidden by default and only visible with ?dev=1', async () => {
    // Test with ?dev=1
    delete window.location
    window.location = new URL('http://localhost:5173/?dev=1')

    global.fetch = vi.fn((url, options) => {
      const u = url.toString()
      if (u.includes('/text/turn')) {
        return Promise.resolve({
          ok: false,
          status: 502,
          json: () => Promise.resolve({ detail: 'Gnani socket connection refused', error_code: 'gnani_error' }),
        })
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ gnani_configured: true, voices_valid: true }),
      })
    })

    render(<App />)

    // Switch to English
    await userEvent.click(screen.getByRole('button', { name: 'English' }))

    const typeToggle = screen.getByText(/Type instead of speaking/i)
    await userEvent.click(typeToggle)

    const input = screen.getByPlaceholderText(/need a token tomorrow/i)
    await userEvent.type(input, 'status')
    await userEvent.click(screen.getByRole('button', { name: /Send/i }))

    await waitFor(() => {
      expect(screen.getByText(/\[dev: gnani_error\]/i)).toBeInTheDocument()
    })
  })

  it('11. First-time visitor experience: tagline, empty token state, how-it-works, mic hint, and first-visit banner', async () => {
    render(<App />)

    // First visit banner is visible when not yet marked visited in localStorage
    expect(screen.getByText(/Click once anywhere to allow sound, then hold SPACE\./i)).toBeInTheDocument()

    // Default Telugu tagline is rendered under clinic title
    expect(screen.getByText(/క్లినిక్ టోకెన్ బుక్ చేయడానికి తెలుగు లేదా English లో మాట్లాడండి\./i)).toBeInTheDocument()

    // Empty token state card rendered when no token
    expect(screen.getByText(/ఇంకా టోకెన్ లేదు\. ఇలా చెప్పి చూడండి: రేపు టోకెన్ కావాలి/i)).toBeInTheDocument()

    // Collapsible How It Works is rendered
    expect(screen.getByText(/ఇది ఎలా పనిచేస్తుంది \(How it works\)/i)).toBeInTheDocument()
    expect(screen.getByText(/మేము అర్థం చేసుకుంటాము/i)).toBeInTheDocument()
    expect(screen.getByText(/సమాధానం వినండి/i)).toBeInTheDocument()

    // Dismiss first-visit banner by clicking anywhere (e.g. switching language to English)
    const enBtn = screen.getByRole('button', { name: 'English' })
    await userEvent.click(enBtn)

    // Banner is dismissed and localStorage is updated
    expect(screen.queryByText(/Click once anywhere to allow sound, then hold SPACE\./i)).not.toBeInTheDocument()
    expect(localStorage.getItem('vq_visited')).toBe('true')

    // Tagline in English
    expect(screen.getByText('Speak in Telugu or English to book a clinic token.')).toBeInTheDocument()

    // Empty state in English
    expect(screen.getByText('No token yet. Try saying: I need a token for tomorrow')).toBeInTheDocument()

    // ONE hint line under mic
    expect(screen.getByText('Hold SPACE to speak. Earphones with a microphone work best.')).toBeInTheDocument()
  })

  it('12. Try-saying chip sends text turn without mic and displays English translation under Telugu reply', async () => {
    let textTurnCalled = false
    let sentBody = null

    global.fetch = vi.fn((url, options) => {
      const u = url.toString()
      if (u.includes('/text/turn')) {
        textTurnCalled = true
        sentBody = JSON.parse(options.body)
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () =>
            Promise.resolve({
              transcript: 'I need a token for tomorrow',
              reply_text: 'రేపు మీకు టోకెన్ నంబర్ ఒకటి బుక్ అయింది. దయచేసి సమయానికి క్లినిక్‌కి రండి.',
              reply_audio_base64: null,
              token: {
                id: 99,
                number: 1,
                date: '2026-11-07',
                status: 'waiting',
                ahead_count: 0,
              },
            }),
        })
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ gnani_configured: true, voices_valid: true }),
      })
    })

    render(<App />)

    // Switch to English to get the English chips
    await userEvent.click(screen.getByRole('button', { name: 'English' }))

    // Click the "I need a token for tomorrow" chip
    const chipBtn = screen.getByRole('button', { name: /"I need a token for tomorrow"/i })
    await userEvent.click(chipBtn)

    // Verify /text/turn was called without touching microphone
    await waitFor(() => {
      expect(textTurnCalled).toBe(true)
      expect(sentBody.text).toBe('I need a token for tomorrow')
    })

    // Verify clinic reply text is displayed
    await waitFor(() => {
      expect(screen.getByText(/రేపు మీకు టోకెన్ నంబర్ ఒకటి బుక్ అయింది/i)).toBeInTheDocument()
    })

    // Verify small English translation is rendered under Telugu reply
    const translation = screen.getByText(/Your token for tomorrow is number 1\. Please come to the clinic on time\./i)
    expect(translation).toBeInTheDocument()
    expect(screen.getByText('EN:')).toBeInTheDocument()

    // Verify token card updated
    expect(screen.getByText('#1')).toBeInTheDocument()
  })

  it('13. P2-2: Large text and high contrast toggle toggles elder-mode and persists to localStorage', async () => {
    const { container } = render(<App />)

    // Switch to English
    await userEvent.click(screen.getByRole('button', { name: 'English' }))

    const elderCheckbox = screen.getByLabelText(/Large text and high contrast/i)
    expect(elderCheckbox).not.toBeChecked()
    expect(container.querySelector('.elder-mode')).toBeNull()

    // Toggle on
    await userEvent.click(elderCheckbox)
    expect(elderCheckbox).toBeChecked()
    expect(container.querySelector('.elder-mode')).not.toBeNull()
    expect(localStorage.getItem('vq_elder_contrast')).toBe('true')

    // Toggle off
    await userEvent.click(elderCheckbox)
    expect(elderCheckbox).not.toBeChecked()
    expect(container.querySelector('.elder-mode')).toBeNull()
    expect(localStorage.getItem('vq_elder_contrast')).toBe('false')
  })

  it('14. P2-2: Slower reply toggle persists to localStorage', async () => {
    render(<App />)

    // Switch to English
    await userEvent.click(screen.getByRole('button', { name: 'English' }))

    const slowCheckbox = screen.getByLabelText(/Slower reply/i)
    expect(slowCheckbox).not.toBeChecked()

    // Toggle on
    await userEvent.click(slowCheckbox)
    expect(slowCheckbox).toBeChecked()
    expect(localStorage.getItem('vq_slow_audio')).toBe('true')

    // Toggle off
    await userEvent.click(slowCheckbox)
    expect(slowCheckbox).not.toBeChecked()
    expect(localStorage.getItem('vq_slow_audio')).toBe('false')
  })

  it('15. P2-2: Plain "Say that again" action replays last reply without making network API calls', async () => {
    let fetchTurnCount = 0
    global.fetch = vi.fn((url) => {
      const u = url.toString()
      if (u.includes('/turn')) {
        fetchTurnCount++
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ gnani_configured: true, voices_valid: true }),
      })
    })

    // Pre-populate with saved reply
    localStorage.setItem(
      'vq_last_reply',
      JSON.stringify({
        transcript: 'token kavali',
        reply_text: 'Your token number is 5',
        reply_audio_base64: 'UklGRigAAABXQVZFZm10IBIAAAABAAEARKwAAIhYAQACABAAAABkYXRhAgAAAAEA',
      })
    )

    render(<App />)
    await userEvent.click(screen.getByRole('button', { name: 'English' }))

    // Say that again button should be present and enabled
    const sayAgainBtn = screen.getByRole('button', { name: /Say that again/i })
    expect(sayAgainBtn).toBeInTheDocument()
    expect(sayAgainBtn).not.toBeDisabled()

    // Click "Say that again"
    await userEvent.click(sayAgainBtn)

    // Verify no new /turn network calls were triggered
    expect(fetchTurnCount).toBe(0)
  })

  it('16. Demo limit displays single-language message with Type instead button and no voice-unavailable or stale-token notes', async () => {
    // Pre-populate with demo_limit reply
    localStorage.setItem(
      'vq_last_reply',
      JSON.stringify({
        transcript: '',
        reply_text: 'Voice demo limit reached for now. Please watch the demo video or try typing.',
        reply_audio_base64: '',
        token: null,
      })
    )

    render(<App />)
    const enBtn = screen.getByRole('button', { name: 'English' })
    await userEvent.click(enBtn)

    // Send a typed turn that returns demo_limit
    global.fetch = vi.fn((url) => {
      const u = url.toString()
      if (u.includes('/text/turn')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () =>
            Promise.resolve({
              transcript: 'hello',
              reply_text: 'Voice demo limit reached for now. Please watch the demo video or try typing.',
              reply_audio_base64: '',
              token: null,
              error: 'Voice demo limit reached for now. Please watch the demo video or try typing.',
              error_code: 'demo_limit',
              limit_reason: 'ip_window',
            }),
        })
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({}),
      })
    })

    const typeInputBtn = screen.getByRole('button', { name: /Type instead of speaking/i })
    await userEvent.click(typeInputBtn)

    const textInput = screen.getByPlaceholderText(/e\.g\. need a token tomorrow/i)
    await userEvent.type(textInput, 'need token{enter}')

    await waitFor(() => {
      expect(screen.getAllByText(/Voice demo limit reached for now/i).length).toBeGreaterThan(0)
    })

    // Verify "Voice reply is not available for this answer" is NOT rendered
    expect(screen.queryByText(/Voice reply is not available for this answer/i)).toBeNull()

    // Verify "Your token was cleared" is NOT rendered
    expect(screen.queryByText(/Your token was cleared/i)).toBeNull()
  })

  it('17. ?dev=1 displays [Dev Limits] diagnostic line with reason and counts', async () => {
    delete window.location
    window.location = new URL('http://localhost:5173/?dev=1')

    render(<App />)

    global.fetch = vi.fn((url) => {
      const u = url.toString()
      if (u.includes('/text/turn')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () =>
            Promise.resolve({
              transcript: 'test',
              reply_text: 'ok',
              reply_audio_base64: '',
              token: null,
              error: null,
              error_code: null,
              limit_reason: 'session_cap',
              limit_counts: {
                ip_count: 3,
                ip_limit: 6,
                sess_count: 10,
                sess_limit: 10,
                daily_count: 45,
                daily_cap: 150,
                reserve: 40,
              },
            }),
        })
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({}),
      })
    })

    const typeInputBtn = screen.getByRole('button', { name: /టైప్ చేయండి|Type instead/i })
    await userEvent.click(typeInputBtn)

    const textInput = screen.getByRole('textbox')
    await userEvent.type(textInput, 'test{enter}')

    await waitFor(() => {
      expect(screen.getByTestId('dev-limits-line')).toBeInTheDocument()
      expect(screen.getByTestId('dev-limits-line')).toHaveTextContent(/reason: session_cap/)
      expect(screen.getByTestId('dev-limits-line')).toHaveTextContent(/session: 10\/10/)
    })
  })

  it('18. ?owner=1 renders owner key configuration bar and saves key in sessionStorage', async () => {
    delete window.location
    window.location = new URL('http://localhost:5173/?owner=1')
    sessionStorage.clear()

    render(<App />)

    const ownerInput = screen.getByTestId('owner-key-input')
    expect(ownerInput).toBeInTheDocument()

    await userEvent.type(ownerInput, 'my_secret_owner_key')
    expect(sessionStorage.getItem('owner_key')).toBe('my_secret_owner_key')
  })

  it('19. Two bookings in a row update card, reply text and translation to the newest token', async () => {
    let callCount = 0
    global.fetch = vi.fn((url) => {
      const u = url.toString()
      if (u.includes('/text/turn')) {
        callCount++
        if (callCount === 1) {
          return Promise.resolve({
            ok: true,
            status: 200,
            json: () =>
              Promise.resolve({
                transcript: 'repu token kavali',
                intent: 'BOOK',
                reply_text: 'మీ టోకెన్ రేపు నంబర్ పదహారు బుక్ అయింది. దయచేసి సమయానికి క్లినిక్‌కి రండి.',
                english_translation: 'Your token for tomorrow is number 16. Please come to the clinic on time.',
                token: { id: 16, number: 16, status: 'waiting', date: '2026-11-07' },
              }),
          })
        } else {
          return Promise.resolve({
            ok: true,
            status: 200,
            json: () =>
              Promise.resolve({
                transcript: 'I need a token for tomorrow',
                intent: 'BOOK',
                reply_text: 'Your token for tomorrow is number seventeen. Please come to the clinic on time.',
                english_translation: 'Your token for tomorrow is number 17. Please come to the clinic on time.',
                token: { id: 17, number: 17, status: 'waiting', date: '2026-11-07' },
              }),
          })
        }
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ gnani_configured: true, voices_valid: true, status: 'ok' }),
      })
    })

    render(<App />)

    const typeAccordion = screen.getByText(/టైప్ చేయండి|Type instead/i)
    await userEvent.click(typeAccordion)

    const input = screen.getByRole('textbox')
    const sendBtn = screen.getByRole('button', { name: /పంపండి|Send/i })

    // Booking 1: Token 16
    await userEvent.type(input, 'repu token kavali')
    await userEvent.click(sendBtn)

    await waitFor(() => {
      expect(screen.getByText('#16')).toBeInTheDocument()
      expect(screen.getByText(/Your token for tomorrow is number 16/i)).toBeInTheDocument()
    })

    // Booking 2: Token 17
    await userEvent.clear(input)
    await userEvent.type(input, 'I need a token for tomorrow')
    await userEvent.click(sendBtn)

    await waitFor(() => {
      expect(screen.getByText('#17')).toBeInTheDocument()
      expect(screen.getByText(/seventeen/i)).toBeInTheDocument()
      expect(screen.queryByText('#16')).not.toBeInTheDocument()
    })
  })

  it('20. A late poll response for an old token does not overwrite the new card', async () => {
    let latePollResolve = null
    const latePollPromise = new Promise((resolve) => {
      latePollResolve = resolve
    })

    global.fetch = vi.fn((url) => {
      const u = url.toString()
      if (u.includes('/tokens/16')) {
        // Delayed poll for old token 16
        return latePollPromise
      }
      if (u.includes('/text/turn')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () =>
            Promise.resolve({
              transcript: 'repu token kavali',
              intent: 'BOOK',
              reply_text: 'మీ టోకెన్ రేపు నంబర్ పదిహేడు బుక్ అయింది.',
              english_translation: 'Your token for tomorrow is number 17. Please come to the clinic on time.',
              token: { id: 17, number: 17, status: 'waiting', date: '2026-11-07' },
            }),
        })
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ gnani_configured: true, voices_valid: true, status: 'ok' }),
      })
    })

    // Pre-populate old token 16 in storage
    localStorage.setItem('vq_token_id', '16')
    render(<App />)

    // A turn books token 17
    const typeAccordion = screen.getByText(/టైప్ చేయండి|Type instead/i)
    await userEvent.click(typeAccordion)

    const input = screen.getByRole('textbox')
    const sendBtn = screen.getByRole('button', { name: /పంపండి|Send/i })
    await userEvent.type(input, 'repu token kavali')
    await userEvent.click(sendBtn)

    await waitFor(() => {
      expect(screen.getByText('#17')).toBeInTheDocument()
    })

    // Now late poll for token 16 finally resolves
    latePollResolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ id: 16, number: 16, status: 'waiting', date: '2026-11-07' }),
    })

    // The card MUST still show #17, never reverting to #16
    await new Promise((r) => setTimeout(r, 50))
    expect(screen.getByText('#17')).toBeInTheDocument()
    expect(screen.queryByText('#16')).not.toBeInTheDocument()
  })

  it('21. ?dev=1 displays developer info for token id and number inside the token card', async () => {
    delete window.location
    window.location = new URL('http://localhost:5173/?dev=1')

    global.fetch = vi.fn((url) => {
      const u = url.toString()
      if (u.includes('/text/turn')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () =>
            Promise.resolve({
              transcript: 'repu token kavali',
              intent: 'BOOK',
              reply_text: 'మీ టోకెన్ రేపు నంబర్ పదిహేడు బుక్ అయింది.',
              english_translation: 'Your token for tomorrow is number 17. Please come to the clinic on time.',
              token: { id: 17, number: 17, status: 'waiting', date: '2026-11-07' },
            }),
        })
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ gnani_configured: true, voices_valid: true, status: 'ok' }),
      })
    })

    render(<App />)

    const typeAccordion = screen.getByText(/టైప్ చేయండి|Type instead/i)
    await userEvent.click(typeAccordion)

    const input = screen.getByRole('textbox')
    const sendBtn = screen.getByRole('button', { name: /పంపండి|Send/i })
    await userEvent.type(input, 'repu token kavali')
    await userEvent.click(sendBtn)

    await waitFor(() => {
      expect(screen.getByTestId('dev-token-info')).toBeInTheDocument()
      expect(screen.getByTestId('dev-token-info')).toHaveTextContent(/dev: token_id=17, token_number=17/)
    })
  })

  it('22. Telugu reply with పదిహేడు translates to number 17 (never number 10)', async () => {
    global.fetch = vi.fn((url) => {
      const u = url.toString()
      if (u.includes('/text/turn')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () =>
            Promise.resolve({
              transcript: 'repu token kavali',
              intent: 'BOOK',
              reply_text: 'మీ టోకెన్ రేపు నంబర్ పదిహేడు బుక్ అయింది. దయచేసి సమయానికి క్లినిక్‌కి రండి.',
              // serverTranslation omitted to test fallback logic
              english_translation: null,
              token: { id: 25, number: 17, status: 'waiting', date: '2026-11-08' },
            }),
        })
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ gnani_configured: true, voices_valid: true, status: 'ok' }),
      })
    })

    render(<App />)

    const typeAccordion = screen.getByText(/టైప్ చేయండి|Type instead/i)
    await userEvent.click(typeAccordion)

    const input = screen.getByRole('textbox')
    const sendBtn = screen.getByRole('button', { name: /పంపండి|Send/i })
    await userEvent.type(input, 'repu token kavali')
    await userEvent.click(sendBtn)

    await waitFor(() => {
      expect(screen.getByText(/Your token for tomorrow is number 17/i)).toBeInTheDocument()
      expect(screen.queryByText(/number 10/i)).not.toBeInTheDocument()
    })
  })
})
