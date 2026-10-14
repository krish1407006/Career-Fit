import { chromium } from '@playwright/test'

const browser = await chromium.launch({ channel: 'chrome' })
const page = await browser.newPage()
await page.goto('http://localhost:5173/login', { waitUntil: 'domcontentloaded' })
await page.waitForSelector('.auth-page')
const info = await page.evaluate(() => {
  const body = getComputedStyle(document.body)
  const brand = document.querySelector('.brand')
  const hero = document.querySelector('.auth-hero')
  const card = document.querySelector('.auth-card')
  return {
    bodyBackgroundImage: body.backgroundImage.slice(0, 120),
    bodyBackgroundSize: body.backgroundSize,
    hasAuthHero: !!hero,
    heroText: hero ? hero.querySelector('h2')?.textContent : null,
    brandClip: brand ? getComputedStyle(brand).webkitBackgroundClip : null,
    cardRadius: card ? getComputedStyle(card).borderRadius : null,
    styleSheets: document.styleSheets.length,
  }
})
console.log(JSON.stringify(info, null, 2))
await browser.close()
