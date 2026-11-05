import { test, expect } from '@playwright/test'

test.describe('Clinic Dashboard E2E with Mocked WebSocket', () => {
  let initialTokens = [
    { id: 101, number: 1, label: 'Patient 1', date: '2026-11-05', status: 'in_consult', language: 'te-IN' },
    { id: 102, number: 2, label: 'Patient 2', date: '2026-11-05', status: 'waiting', language: 'te-IN' },
  ]

  test.beforeEach(async ({ page }) => {
    // Inject mock WebSocket implementation before any page scripts execute
    await page.addInitScript(() => {
      window.__wsConnectCount = 0
      class MockWebSocket extends EventTarget {
        constructor(url) {
          super()
          this.url = url
          this.readyState = 1 // OPEN
          window.__mockWs = this
          window.__wsConnectCount++
          setTimeout(() => {
            if (this.onopen) this.onopen(new Event('open'))
            this.dispatchEvent(new Event('open'))
          }, 30)
        }
        send(data) {}
        close() {
          this.readyState = 3 // CLOSED
          if (this.onclose) this.onclose(new CloseEvent('close'))
          this.dispatchEvent(new CloseEvent('close'))
        }
      }
      window.WebSocket = MockWebSocket
    })
  })

  test('1. A new token appears without refresh on WebSocket queue_changed message', async ({ page }) => {
    let currentTokens = [...initialTokens]

    await page.route('**/queue*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          day: 'today',
          date: '2026-11-05',
          counts: { waiting: currentTokens.filter((t) => t.status === 'waiting').length },
          tokens: currentTokens,
        }),
      })
    })

    await page.route('**/voice-logs*', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
    })

    await page.route('**/usage*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ limit: 100, real_calls_today: 10 }),
      })
    })

    await page.goto('/clinic')

    // Initial tokens visible
    await expect(page.locator('.consult-token-badge')).toContainText('#1')
    await expect(page.locator('.queue-token-item')).toContainText('#2')

    // Add token #3 dynamically in backend
    currentTokens.push({
      id: 103,
      number: 3,
      label: 'Patient 3',
      date: '2026-11-05',
      status: 'waiting',
      language: 'te-IN',
    })

    // Dispatch queue_changed via WebSocket
    await page.evaluate(() => {
      if (window.__mockWs && window.__mockWs.onmessage) {
        window.__mockWs.onmessage({ data: JSON.stringify({ type: 'queue_changed', date: '2026-11-05' }) })
      }
    })

    // Token #3 should appear on screen without page refresh
    await expect(page.locator('.waiting-list')).toContainText('#3')
  })

  test('2. Call next, Mark done, and No-show trigger the correct POST endpoints', async ({ page }) => {
    let callNextCalled = false
    let markDoneId = null
    let markNoShowId = null

    await page.route('**/queue*', async (route) => {
      const url = route.request().url()
      if (url.includes('/queue/next')) {
        callNextCalled = true
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ id: 202, number: 2, status: 'in_consult' }),
        })
      }
      if (url.includes('/done')) {
        const match = url.match(/\/queue\/(\d+)\/done/)
        if (match) markDoneId = match[1]
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ id: 201, number: 1, status: 'done' }),
        })
      }
      if (url.includes('/no-show')) {
        const match = url.match(/\/queue\/(\d+)\/no-show/)
        if (match) markNoShowId = match[1]
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ id: 202, number: 2, status: 'no_show' }),
        })
      }
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          day: 'today',
          date: '2026-11-05',
          counts: { waiting: 1, in_consult: 1 },
          tokens: [
            { id: 201, number: 1, label: 'Patient 1', status: 'in_consult', date: '2026-11-05' },
            { id: 202, number: 2, label: 'Patient 2', status: 'waiting', date: '2026-11-05' },
          ],
        }),
      })
    })

    await page.route('**/voice-logs*', async (route) => {
      await route.fulfill({ status: 200, body: '[]' })
    })

    await page.route('**/usage*', async (route) => {
      await route.fulfill({ status: 200, body: JSON.stringify({ limit: 100, real_calls_today: 0 }) })
    })

    await page.goto('/clinic')

    // 1. Click 'Call next'
    const callNextBtn = page.locator('button.btn-call-next')
    await callNextBtn.click()
    expect(callNextCalled).toBe(true)

    // 2. Click 'Mark Done' on token 201
    const doneBtn = page.locator('.btn-mark-done')
    await doneBtn.click()
    expect(markDoneId).toBe('201')

    // 3. Click 'No-show' on token 201
    const noShowBtn = page.locator('.btn-no-show')
    await noShowBtn.click()
    expect(markNoShowId).toBe('201')
  })

  test('3. Reconnects after the WebSocket closes', async ({ page }) => {
    await page.route('**/queue*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ day: 'today', date: '2026-11-05', counts: {}, tokens: [] }),
      })
    })
    await page.route('**/voice-logs*', async (route) => route.fulfill({ status: 200, body: '[]' }))
    await page.route('**/usage*', async (route) => route.fulfill({ status: 200, body: '{"limit":100,"real_calls_today":0}' }))

    await page.goto('/clinic')

    // Wait until initial websocket connection is established
    await page.waitForFunction(() => window.__wsConnectCount >= 1)
    const initialCount = await page.evaluate(() => window.__wsConnectCount)

    // Simulate socket disconnect
    await page.evaluate(() => {
      if (window.__mockWs) window.__mockWs.close()
    })

    // Dashboard reconnect timeout is 2000ms
    await page.waitForTimeout(2500)
    const afterReconnectCount = await page.evaluate(() => window.__wsConnectCount)
    expect(afterReconnectCount).toBeGreaterThan(initialCount)
  })
})
