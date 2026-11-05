const { chromium } = require('@playwright/test');
const path = require('path');

(async () => {
  const fakeWav = path.resolve('../backend/tests/audio/fake_mic_3s.wav');
  console.log('Using fake wav:', fakeWav);

  const browser = await chromium.launch({
    headless: true,
    args: [
      '--use-fake-ui-for-media-stream',
      '--use-fake-device-for-media-stream',
      `--use-file-for-fake-audio-capture=${fakeWav}`,
    ],
  });

  const context = await browser.newContext({ permissions: ['microphone'] });
  const page = await context.newPage();

  page.on('console', (msg) => console.log('BROWSER LOG:', msg.type(), msg.text()));
  page.on('pageerror', (err) => console.log('PAGE ERROR:', err));

  await page.goto('http://127.0.0.1:5173/');
  await page.click('button:has-text("English")');

  console.log('Pressing Space down...');
  await page.keyboard.down('Space');
  await page.waitForTimeout(1500);
  console.log('Releasing Space...');
  await page.keyboard.up('Space');
  await page.waitForTimeout(1000);

  const errMsg = await page.locator('.error-alert').textContent().catch(() => null);
  console.log('Error alert on page:', errMsg);
  const status = await page.locator('.status-text').textContent().catch(() => null);
  console.log('Status text on page:', status);

  await browser.close();
})();

