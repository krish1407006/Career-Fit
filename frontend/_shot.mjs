import { chromium } from '@playwright/test'

const browser = await chromium.launch({ channel: 'chrome' })
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } })
for (const [route, name] of [['/login', 'login'], ['/register', 'register']]) {
  await page.goto('http://localhost:5173' + route, { waitUntil: 'networkidle' })
  await page.waitForSelector('.auth-page')
  await page.waitForTimeout(800)
  await page.screenshot({ path: `_shot-${name}.png`, fullPage: true })
}
await browser.close()
console.log('done')
