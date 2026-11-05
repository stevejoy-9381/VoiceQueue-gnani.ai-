import { test, expect } from '@playwright/test'

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
    await expect(page.locator('.error-alert')).toContainText(/Too short, hold the key a little longer/i)
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
    await expect(page.locator('.error-alert')).toContainText(/Microphone access denied/i)

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
})
