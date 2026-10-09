import { chromium } from '@playwright/test'

const browser = await chromium.launch()
const context = await browser.newContext({ storageState: 'e2e/.auth/student.json', viewport: { width: 375, height: 667 } })
const page = await context.newPage()
await page.goto('http://localhost:5173/student/profile', { waitUntil: 'networkidle' })
await page.waitForSelector('.profile-grid .card')

const report = await page.evaluate(() => {
  const limit = document.documentElement.clientWidth
  const all = [...document.querySelectorAll('body *')]
  const overflowing = all.filter((el) => el.getBoundingClientRect().right > limit + 1)
  const describe = (el) => {
    const r = el.getBoundingClientRect()
    const cs = getComputedStyle(el)
    return {
      tag: el.tagName.toLowerCase(),
      cls: String(el.className || '').slice(0, 40),
      left: Math.round(r.left),
      right: Math.round(r.right),
      width: Math.round(r.width),
      display: cs.display,
      minWidth: cs.minWidth,
      text: (el.textContent || '').trim().slice(0, 45),
      childCount: el.children.length,
    }
  }
  const leaves = overflowing.filter((el) => ![...el.children].some((c) => c.getBoundingClientRect().right > limit + 1))
  const grid = document.querySelector('.profile-grid')
  const cs = grid ? getComputedStyle(grid) : null
  return {
    clientWidth: limit,
    scrollWidth: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth),
    gridCols: cs ? cs.gridTemplateColumns : null,
    gridWidth: grid ? Math.round(grid.getBoundingClientRect().width) : null,
    overflowingCount: overflowing.length,
    top: overflowing.slice(0, 8).map(describe),
    leaves: leaves.slice(0, 15).map(describe),
  }
})
console.log(JSON.stringify(report, null, 2))
await browser.close()
