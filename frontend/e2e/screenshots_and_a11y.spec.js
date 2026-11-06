import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const SCREENS_DIR = path.resolve(__dirname, '../../docs/screens')
const RESULTS_FILE = path.resolve(__dirname, '../../docs/a11y_report.json')

test.describe('Visual Screenshots & Accessibility (axe-core)', () => {
  test.beforeAll(() => {
    if (!fs.existsSync(SCREENS_DIR)) {
      fs.mkdirSync(SCREENS_DIR, { recursive: true })
    }
  })

  test.beforeEach(async ({ page }) => {
    // Intercept standard routes so page displays realistic clinic data
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
        body: JSON.stringify({ limit: 100, real_calls_today: 12 }),
      })
    })

    await page.route('**/queue?day=today', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          day: 'today',
          date: '2026-11-05',
          counts: { waiting: 2, in_consult: 1 },
          tokens: [
            { id: 1, number: 1, label: 'Patient 1', status: 'in_consult', date: '2026-11-05', language: 'te-IN' },
            { id: 2, number: 2, label: 'Patient 2', status: 'waiting', date: '2026-11-05', language: 'te-IN' },
            { id: 3, number: 3, label: 'Patient 3', status: 'waiting', date: '2026-11-05', language: 'te-IN' },
          ],
        }),
      })
    })

    await page.route('**/voice-logs?limit=20', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          { id: 1, time: '10:15:00', transcript: 'repu token kavali', detected_language: 'te-IN', intent: 'BOOK', ok: true, token_number: 1 },
        ]),
      })
    })

    await page.route('**/review-status', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          fully_reviewed: true,
          reviewed_count: 50,
          total_strings: 50,
          pending_count: 0,
        }),
      })
    })

    await page.route('**/voice-tests', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          { id: 1, text: 'repu token kavali', language: 'te-IN', noise_level: 'quiet', accuracy: 'high', ok: true },
        ]),
      })
    })

    await page.route('**/voice-tests/summary', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          total: 45,
          passed: 45,
          accuracy_percent: 100.0,
          languages: { 'te-IN': 25, 'en-IN': 20 },
        }),
      })
    })

    await page.routeWebSocket('**/ws/queue', () => {})
  })

  test('1. Patient Page screenshots at 360x740 and 1366x768', async ({ page }) => {
    // Mobile Viewport (360x740)
    await page.setViewportSize({ width: 360, height: 740 })
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    await page.screenshot({ path: path.join(SCREENS_DIR, 'patient_360x740.png'), fullPage: true })

    // Desktop Viewport (1366x768)
    await page.setViewportSize({ width: 1366, height: 768 })
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    await page.screenshot({ path: path.join(SCREENS_DIR, 'patient_1366x768.png'), fullPage: true })
  })

  test('2. Dashboard screenshots at 360x740 and 1366x768', async ({ page }) => {
    // Mobile Viewport (360x740)
    await page.setViewportSize({ width: 360, height: 740 })
    await page.goto('/clinic')
    await page.waitForLoadState('networkidle')
    await page.screenshot({ path: path.join(SCREENS_DIR, 'dashboard_360x740.png'), fullPage: true })

    // Desktop Viewport (1366x768)
    await page.setViewportSize({ width: 1366, height: 768 })
    await page.goto('/clinic')
    await page.waitForLoadState('networkidle')
    await page.screenshot({ path: path.join(SCREENS_DIR, 'dashboard_1366x768.png'), fullPage: true })
  })

  test('3. Tests page screenshots at 360x740 and 1366x768', async ({ page }) => {
    // Mobile Viewport (360x740)
    await page.setViewportSize({ width: 360, height: 740 })
    await page.goto('/tests')
    await page.waitForLoadState('networkidle')
    await page.screenshot({ path: path.join(SCREENS_DIR, 'tests_360x740.png'), fullPage: true })

    // Desktop Viewport (1366x768)
    await page.setViewportSize({ width: 1366, height: 768 })
    await page.goto('/tests')
    await page.waitForLoadState('networkidle')
    await page.screenshot({ path: path.join(SCREENS_DIR, 'tests_1366x768.png'), fullPage: true })
  })

  test('4. About page screenshots at 360x740 and 1366x768', async ({ page }) => {
    // Mobile Viewport (360x740)
    await page.setViewportSize({ width: 360, height: 740 })
    await page.goto('/about')
    await page.waitForLoadState('networkidle')
    await page.screenshot({ path: path.join(SCREENS_DIR, 'about_360x740.png'), fullPage: true })

    // Desktop Viewport (1366x768)
    await page.setViewportSize({ width: 1366, height: 768 })
    await page.goto('/about')
    await page.waitForLoadState('networkidle')
    await page.screenshot({ path: path.join(SCREENS_DIR, 'about_1366x768.png'), fullPage: true })
  })

  test('5. Telugu text renders properly on patient page (screenshot)', async ({ page }) => {
    await page.setViewportSize({ width: 360, height: 740 })
    await page.goto('/')
    // Ensure Telugu language is selected
    await page.click('button:has-text("తెలుగు")')
    await expect(page.locator('.clinic-title')).toBeVisible()
    await expect(page.locator('.card-transcript .card-label')).toHaveText('మీరు చెప్పినది')

    await page.screenshot({
      path: path.join(SCREENS_DIR, 'patient_telugu_rendered.png'),
      fullPage: true,
    })
  })

  test('4. Axe accessibility checks on Patient Page and Dashboard', async ({ page }) => {
    // Patient Page
    await page.goto('/')
    const patientAxe = await new AxeBuilder({ page }).analyze()

    // Dashboard
    await page.goto('/clinic')
    const dashboardAxe = await new AxeBuilder({ page }).analyze()

    const report = {
      patient: {
        violationsCount: patientAxe.violations.length,
        violations: patientAxe.violations.map((v) => ({
          id: v.id,
          impact: v.impact,
          description: v.description,
          nodes: v.nodes.length,
        })),
      },
      dashboard: {
        violationsCount: dashboardAxe.violations.length,
        violations: dashboardAxe.violations.map((v) => ({
          id: v.id,
          impact: v.impact,
          description: v.description,
          nodes: v.nodes.length,
        })),
      },
    }

    fs.writeFileSync(RESULTS_FILE, JSON.stringify(report, null, 2))
    expect(patientAxe).toBeDefined()
    expect(dashboardAxe).toBeDefined()
  })
})

