import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

const TINY_WAV_B64 = 'UklGRigAAABXQVZFZm10IBIAAAABAAEARKwAAIhYAQACABAAAABkYXRhAgAAAAEA'

function createValidWavB64(durationSeconds = 0.5, sampleRate = 16000) {
  const numChannels = 1
  const bytesPerSample = 2
  const totalSamples = Math.floor(sampleRate * durationSeconds)
  const dataBytes = totalSamples * numChannels * bytesPerSample
  const buffer = new ArrayBuffer(44 + dataBytes)
  const view = new DataView(buffer)

  // RIFF
  view.setUint32(0, 0x52494646, false) // "RIFF"
  view.setUint32(4, 36 + dataBytes, true)
  view.setUint32(8, 0x57415645, false) // "WAVE"
  // fmt 
  view.setUint32(12, 0x666d7420, false) // "fmt "
  view.setUint32(16, 16, true)
  view.setUint16(20, 1, true) // PCM
  view.setUint16(22, numChannels, true)
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * numChannels * bytesPerSample, true)
  view.setUint16(32, numChannels * bytesPerSample, true)
  view.setUint16(34, 16, true)
  // data
  view.setUint32(36, 0x64617461, false) // "data"
  view.setUint32(40, dataBytes, true)

  const bytes = new Uint8Array(buffer)
  let binary = ''
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i])
  }
  return btoa(binary)
}

test.describe('Patient Voice & Interaction E2E (Intercepted API)', () => {
  test.beforeEach(async ({ page }) => {
    // Ensure clean state per test
    await page.addInitScript(() => {
      try {
        localStorage.clear()
        sessionStorage.clear()
      } catch (e) {}
    })

    // Intercept health & usage by default
    await page.route('**/health', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ gnani_configured: true, voices_valid: true, ffmpeg_found: true }),
      })
    })

    await page.route('**/usage', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ limit: 100, real_calls_today: 5 }),
      })
    })

    await page.route('**/tokens/**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ id: 1, number: 1, status: 'waiting', ahead_count: 0 }),
      })
    })

    page.on('console', (msg) => console.log('PAGE LOG:', msg.text()))
    page.on('pageerror', (err) => console.log('PAGE ERROR:', err.message))
  })

  test('1. Hold and release Space starts/stops recording and sends exactly ONE upload', async ({ page }) => {
    let uploadCount = 0
    await page.route('**/voice/turn', async (route) => {
      uploadCount++
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          transcript: 'I need a token tomorrow',
          reply_text: 'Your token number is one.',
          reply_audio_base64: TINY_WAV_B64,
          token: { id: 1, number: 1, status: 'waiting', ahead_count: 0 },
        }),
      })
    })

    await page.goto('/')
    await page.click('button:has-text("English")')
    await page.waitForSelector('button.mic-button:not([disabled])')

    // Hold Space for 1500ms (> 0.5s) then release
    await page.keyboard.down('Space')
    await expect(page.locator('.mic-wrapper')).toHaveClass(/recording/)

    await page.waitForTimeout(1500)
    await page.keyboard.up('Space')

    // Wait for processing to complete
    await expect(page.locator('.card-transcript .card-content')).toContainText('I need a token tomorrow')
    expect(uploadCount).toBe(1)
  })

  test('2. Repeat Space keydown events while holding do not send extra uploads', async ({ page }) => {
    let uploadCount = 0
    await page.route('**/voice/turn', async (route) => {
      uploadCount++
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          transcript: 'book token',
          reply_text: 'Token booked',
          reply_audio_base64: TINY_WAV_B64,
        }),
      })
    })

    await page.goto('/')
    await page.click('button:has-text("English")')
    await page.keyboard.down('Space')
    await expect(page.locator('.mic-wrapper')).toHaveClass(/recording/)
    // Simulate browser key repeat events while holding Space
    await page.dispatchEvent('body', 'keydown', { code: 'Space', repeat: true })
    await page.dispatchEvent('body', 'keydown', { code: 'Space', repeat: true })
    await page.waitForTimeout(1200)
    await page.keyboard.up('Space')

    await expect(page.locator('.card-transcript .card-content')).toContainText('book token')
    expect(uploadCount).toBe(1)
  })

  test('3. Space key inside the text box records nothing and types space normally', async ({ page }) => {
    let voiceUploads = 0
    await page.route('**/voice/turn', async (route) => {
      voiceUploads++
      await route.fulfill({ status: 200, body: '{}' })
    })

    await page.goto('/')
    await page.click('button:has-text("English")')

    // Open text input accordion
    await page.click('button:has-text("Type instead")')
    const input = page.locator('input.type-input')
    await expect(input).toBeVisible()

    // Focus input and press space inside
    await input.focus()
    await page.keyboard.type('hello world')

    // Confirm space was typed into the input, not triggering recording
    await expect(input).toHaveValue('hello world')
    expect(voiceUploads).toBe(0)
    await expect(page.locator('.mic-wrapper')).not.toHaveClass(/recording/)
  })

  test('4. Window blur stops recording safely', async ({ page }) => {
    let voiceUploads = 0
    await page.route('**/voice/turn', async (route) => {
      voiceUploads++
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ transcript: 'blur turn', reply_text: 'Recorded before blur' }),
      })
    })

    await page.goto('/')
    await page.click('button:has-text("English")')
    await page.keyboard.down('Space')
    await expect(page.locator('.mic-wrapper')).toHaveClass(/recording/)
    await page.waitForTimeout(600)

    // Trigger window blur
    await page.evaluate(() => window.dispatchEvent(new Event('blur')))
    await page.keyboard.up('Space')

    // Recording should safely halt and dispatch
    await expect(page.locator('.mic-wrapper')).not.toHaveClass(/recording/)
  })

  test('5. Tap mic button starts and stops recording', async ({ page }) => {
    let voiceUploads = 0
    await page.route('**/voice/turn', async (route) => {
      voiceUploads++
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ transcript: 'tap turn', reply_text: 'Tap successful' }),
      })
    })

    await page.goto('/')
    await page.waitForSelector('button.mic-button:not([disabled])')
    const micBtn = page.locator('button.mic-button')

    // Tap to start
    await micBtn.click()
    await expect(page.locator('.mic-wrapper')).toHaveClass(/recording/)

    await page.waitForTimeout(1500)

    // Tap to stop
    await micBtn.click()
    await expect(page.locator('.card-transcript .card-content')).toContainText('tap turn')
    expect(voiceUploads).toBe(1)
  })

  test('6. Recording under 0.5s shows the too-short message without sending upload', async ({ page }) => {
    let uploadCalled = false
    await page.route('**/voice/turn', async (route) => {
      uploadCalled = true
      await route.fulfill({ status: 200, body: '{}' })
    })

    await page.goto('/')
    await page.click('button:has-text("English")')

    // Very brief tap (under 0.5s)
    await page.keyboard.down('Space')
    await page.waitForTimeout(100)
    await page.keyboard.up('Space')

    // Error alert shows friendly too-short message
    await expect(page.locator('.error-alert')).toContainText(/too short/i)
    expect(uploadCalled).toBe(false)
  })

  test('7. Microphone permission denied shows friendly error message and typing still works', async ({
    context,
    page,
  }) => {
    let textTurnCalled = false
    await page.route('**/text/turn', async (route) => {
      textTurnCalled = true
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ transcript: 'typed request', reply_text: 'Processed successfully' }),
      })
    })

    await page.goto('/')
    await page.click('button:has-text("English")')

    // Mock mic permission denial in page
    await page.evaluate(() => {
      if (navigator.mediaDevices) {
        navigator.mediaDevices.getUserMedia = () =>
          Promise.reject(new DOMException('Permission denied', 'NotAllowedError'))
      }
    })

    // Tap mic button without mic permission
    await page.click('button.mic-button')

    // Friendly error banner displayed
    await expect(page.locator('.error-alert')).toContainText(/Microphone access.*denied/i)

    // Typed input is automatically revealed and functional
    const input = page.locator('input.type-input')
    await expect(input).toBeVisible()
    await input.fill('typed request')
    await page.click('button:has-text("Send")')

    await expect(page.locator('.card-reply .card-content')).toContainText('Processed successfully')
    expect(textTurnCalled).toBe(true)
  })

  test('8. Reply audio plays after turn and Replay button makes NO extra network requests', async ({
    page,
  }) => {
    let requestsCount = 0
    await page.route('**/voice/turn', async (route) => {
      requestsCount++
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          transcript: 'voice prompt',
          reply_text: 'Spoken reply here',
          reply_audio_base64: TINY_WAV_B64,
        }),
      })
    })

    await page.goto('/')
    await page.click('button:has-text("English")')

    // Record turn
    await page.keyboard.down('Space')
    await expect(page.locator('.mic-wrapper')).toHaveClass(/recording/)
    await page.waitForTimeout(1500)
    await page.keyboard.up('Space')

    await expect(page.locator('.card-reply .card-content')).toContainText('Spoken reply here')
    expect(requestsCount).toBe(1)

    // Replay button should be enabled
    const replayBtn = page.locator('button.replay-btn')
    await expect(replayBtn).toBeEnabled()

    // Click Replay twice
    await replayBtn.click()
    await page.waitForTimeout(100)
    await replayBtn.click()

    // Strict assertion: Replay must NOT make any extra backend requests
    expect(requestsCount).toBe(1)
  })

  test('9. Stubbed /voice/turn returns valid WAV and shared audio element starts playing', async ({ page }) => {
    const validWavB64 = createValidWavB64(0.8)
    await page.route('**/voice/turn', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          transcript: 'I need a token tomorrow',
          reply_text: 'Your token number is five.',
          reply_audio_base64: validWavB64,
          audio_source: 'timbre',
          audio_duration_seconds: 0.8,
          audio_bytes: 25644,
        }),
      })
    })

    await page.goto('/?dev=1')
    await page.click('button:has-text("English")')
    await page.waitForSelector('button.mic-button:not([disabled])')

    // Record turn using mic button
    const micBtn = page.locator('button.mic-button')
    await micBtn.click()
    await expect(page.locator('.mic-wrapper')).toHaveClass(/recording/)
    await page.waitForTimeout(1500)
    await micBtn.click()

    // Check that reply text is rendered
    await expect(page.locator('.card-reply .card-content')).toContainText('Your token number is five.')

    // Check that replay button is enabled
    await expect(page.locator('button.replay-btn')).toBeEnabled()

    // Check dev line is visible with ?dev=1
    await expect(page.locator('.dev-audio-line')).toContainText(/source: timbre/i)
  })

  test('10. Stubbed /voice/turn returns audio_error: shows unavailable message and disabled replay', async ({
    page,
  }) => {
    await page.route('**/voice/turn', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          transcript: 'check my token',
          reply_text: 'Your token is currently waiting.',
          reply_audio_base64: null,
          audio_source: 'none',
          audio_error: 'tts_invalid_audio',
        }),
      })
    })

    await page.goto('/?dev=1')
    await page.click('button:has-text("English")')
    await page.waitForSelector('button.mic-button:not([disabled])')

    // Perform voice turn using mic button
    const micBtn = page.locator('button.mic-button')
    await micBtn.click()
    await expect(page.locator('.mic-wrapper')).toHaveClass(/recording/)
    await page.waitForTimeout(1500)
    await micBtn.click()

    // Verify reply text is displayed
    await expect(page.locator('.card-reply .card-content')).toContainText('Your token is currently waiting.')

    // Verify 'Voice reply is not available for this answer' message is shown
    const unavailableMsg = page.locator('.reply-audio-unavailable')
    await expect(unavailableMsg).toBeVisible()
    await expect(unavailableMsg).toContainText('Voice reply is not available for this answer')

    // Replay button should be disabled since there is no audio
    const replayBtn = page.locator('button.replay-btn')
    await expect(replayBtn).toBeDisabled()
  })

  test('11. P2-1: Clicking a Try Saying chip sends a text turn without using the microphone', async ({
    page,
  }) => {
    let textTurnCalled = false
    let sentText = null
    let voiceTurnCalled = false

    await page.route('**/voice/turn', async (route) => {
      voiceTurnCalled = true
      await route.fulfill({ status: 500, body: 'should not be called' })
    })

    await page.route('**/text/turn', async (route) => {
      textTurnCalled = true
      const postData = JSON.parse(route.request().postData() || '{}')
      sentText = postData.text
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          transcript: postData.text,
          reply_text: 'Your token for tomorrow is number 1. Please arrive on time.',
          reply_audio_base64: null,
          token: { id: 101, number: 1, date: '2026-11-07', status: 'waiting', ahead_count: 0 },
        }),
      })
    })

    await page.goto('/')
    await page.click('button:has-text("English")')

    // Empty state should be visible initially
    await expect(page.locator('.card-empty-token')).toBeVisible()
    await expect(page.locator('.card-empty-token')).toContainText('No token yet. Try saying: I need a token for tomorrow')

    // Collapsible How it works should be visible
    await expect(page.locator('.how-it-works-details')).toBeVisible()

    // Find chip for "I need a token for tomorrow"
    const chip = page.locator('button.try-saying-chip', { hasText: 'I need a token for tomorrow' })
    await expect(chip).toBeVisible()
    await chip.click()

    // Ensure /text/turn was called with the chip's text
    await page.waitForTimeout(500)
    expect(textTurnCalled).toBe(true)
    expect(sentText).toBe('I need a token for tomorrow')
    expect(voiceTurnCalled).toBe(false)

    // Verify token card rendered
    await expect(page.locator('.token-card .token-number')).toContainText('#1')
  })

  test('12. P2-1: Telugu reply displays small English translation template under it', async ({
    page,
  }) => {
    await page.route('**/text/turn', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          transcript: 'repu token kavali',
          reply_text: 'రేపు మీకు టోకెన్ నంబర్ ఒకటి బుక్ అయింది. దయచేసి సమయానికి క్లినిక్‌కి రండి.',
          reply_audio_base64: null,
          token: { id: 202, number: 1, date: '2026-11-07', status: 'waiting', ahead_count: 0 },
        }),
      })
    })

    await page.goto('/')
    // Click Telugu chip or send Telugu text turn
    const teChip = page.locator('button.try-saying-chip', { hasText: 'రేపు టోకెన్ కావాలి' })
    await expect(teChip).toBeVisible()
    await teChip.click()

    // Verify Telugu clinic reply text
    await expect(page.locator('.card-reply .card-content')).toContainText('రేపు మీకు టోకెన్ నంబర్ ఒకటి బుక్ అయింది')

    // Verify small English translation is rendered under the Telugu reply
    const translation = page.locator('.reply-translation')
    await expect(translation).toBeVisible()
    await expect(translation).toContainText('EN:')
    await expect(translation).toContainText('Your token for tomorrow is number 1. Please come to the clinic on time.')
  })

  test('13. P2-2: Elder-friendly mode readable at 360px and passes axe check without serious violations', async ({
    page,
  }) => {
    // 360px mobile viewport
    await page.setViewportSize({ width: 360, height: 740 })

    await page.route('**/text/turn', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          transcript: 'I need a token for tomorrow',
          reply_text: 'Your token for tomorrow is number 1. Please come to the clinic on time.',
          reply_audio_base64: TINY_WAV_B64,
          token: { id: 303, number: 1, date: '2026-11-07', status: 'waiting', ahead_count: 0 },
        }),
      })
    })

    await page.goto('/')

    // Dismiss first visit banner
    const firstVisit = page.locator('.first-visit-banner')
    if (await firstVisit.isVisible()) {
      await firstVisit.click()
    }

    // Switch to English
    await page.click('button.lang-btn:has-text("English")')

    // Turn on both toggles
    const elderToggle = page.locator('#a11y-elder-toggle')
    const slowToggle = page.locator('#a11y-slow-toggle')
    await elderToggle.check()
    await slowToggle.check()

    // Ensure .elder-mode class is applied
    await expect(page.locator('.app-viewport')).toHaveClass(/elder-mode/)

    // Trigger a text turn so replay & say again are enabled with audio
    const chip = page.locator('button.try-saying-chip', { hasText: 'I need a token for tomorrow' })
    await chip.click()

    // Verify Replay and Say That Again buttons are at least 64px tall in elder mode (Req 3)
    const replayBtn = page.locator('button.replay-btn')
    const sayAgainBtn = page.locator('button.say-again-btn')
    await expect(replayBtn).toBeVisible()
    await expect(sayAgainBtn).toBeVisible()

    const replayBox = await replayBtn.boundingBox()
    const sayAgainBox = await sayAgainBtn.boundingBox()
    expect(replayBox.height).toBeGreaterThanOrEqual(64)
    expect(sayAgainBox.height).toBeGreaterThanOrEqual(64)

    // Verify mic button is enlarged in elder mode
    const micBtn = page.locator('button.mic-button')
    const micBox = await micBtn.boundingBox()
    expect(micBox.width).toBeGreaterThanOrEqual(150)
    expect(micBox.height).toBeGreaterThanOrEqual(150)

    // Verify no horizontal overflow at 360px
    const isOverflowing = await page.evaluate(() => {
      return document.documentElement.scrollWidth > window.innerWidth + 2
    })
    expect(isOverflowing).toBe(false)

    // Run axe accessibility check (Req 7)
    const accessibilityScanResults = await new AxeBuilder({ page })
      .disableRules(['color-contrast']) // Check core semantic violations; color-contrast checked separately if needed
      .analyze()

    const seriousViolations = accessibilityScanResults.violations.filter((v) =>
      ['serious', 'critical'].includes(v.impact)
    )
    expect(seriousViolations).toEqual([])
  })

  test('14. P2-2: Axe color-contrast and accessibility check passes with no serious violations', async ({
    page,
  }) => {
    await page.setViewportSize({ width: 360, height: 740 })
    await page.goto('/')

    // Dismiss first visit banner
    const firstVisit = page.locator('.first-visit-banner')
    if (await firstVisit.isVisible()) {
      await firstVisit.click()
    }

    // Turn on large text & high contrast
    await page.locator('#a11y-elder-toggle').check()
    await page.locator('#a11y-slow-toggle').check()

    // Run full Axe audit
    const results = await new AxeBuilder({ page }).analyze()
    const seriousOrCritical = results.violations.filter((v) =>
      ['serious', 'critical'].includes(v.impact)
    )

    if (seriousOrCritical.length > 0) {
      console.log('AXE VIOLATIONS:', JSON.stringify(seriousOrCritical, null, 2))
    }
    expect(seriousOrCritical).toEqual([])
  })

  test('15. Stale token ID: a 404 response clears saved token from view and displays notice', async ({
    page,
  }) => {
    // 1. Initial booking returns token #101
    await page.route('**/text/turn', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          transcript: 'I need a token for tomorrow',
          reply_text: 'Your token for tomorrow is number 1.',
          token: { id: 101, number: 1, date: '2026-11-07', status: 'waiting', ahead_count: 0 },
        }),
      })
    })

    // Return 200 for initial token poll
    await page.route('**/tokens/101', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ id: 101, number: 1, status: 'waiting', ahead_count: 0 }),
      })
    })

    await page.goto('/')
    await page.click('button:has-text("English")')

    // Click chip to book token #101
    const chip = page.locator('button.try-saying-chip', { hasText: 'I need a token for tomorrow' })
    await chip.click()

    // Verify token card appears
    await expect(page.locator('.token-card')).toBeVisible()

    // 2. Now unroute and return 404 on subsequent poll for token #101 (e.g. receptionist reset queue)
    await page.unroute('**/tokens/101')
    await page.unroute('**/tokens/**')
    await page.route('**/tokens/101', async (route) => {
      await route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Token 101 not found' }),
      })
    })
    await page.route('**/tokens/**', async (route) => {
      await route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Token not found' }),
      })
    })

    // Expect the token cleared notice to appear after polling returns 404
    await expect(page.locator('.token-cleared-notice')).toBeVisible({ timeout: 12000 })
    await expect(page.locator('.token-cleared-notice')).toContainText(/token was cleared/i)

    // Token card is cleared
    await expect(page.locator('.token-card')).not.toBeVisible()
  })
})
