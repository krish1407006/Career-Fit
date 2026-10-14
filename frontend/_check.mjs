import { chromium } from '@playwright/test'

const browser = await chromium.launch({ channel: 'chrome' })
const page = await browser.newPage()
await page.goto('http://localhost:5173/login', { waitUntil: 'domcontentloaded' })
await page.waitForSelector('.auth-page')
const q = (sel) => document.querySelector(sel)
const info = await page.evaluate(() => {
  const g = (sel) => {
    const el = document.querySelector(sel)
    return el ? getComputedStyle(el) : null
  }
  const brand = g('.brand')
  const btn = g('.auth-card button')
  const topbar = g('.topbar')
  return {
    theme: document.documentElement.getAttribute('data-theme'),
    bodyAnim: getComputedStyle(document.body).animationName,
    bodyBgImg: getComputedStyle(document.body).backgroundImage.slice(0, 60),
    brandColor: brand && brand.color,
    brandBgClip: brand && brand.webkitBackgroundClip,
    brandAnim: brand && brand.animationName,
    btnBg: btn && btn.backgroundColor,
    btnAnim: btn && btn.animationName,
    topbarBefore: topbar ? getComputedStyle(topbar, '::before').display : null,
  }
})
console.log(JSON.stringify(info, null, 2))
await browser.close()
