import fs from 'node:fs'
import { expect, test } from '@playwright/test'
import { authState, gotoAndWait, measureOverflow } from './helpers.js'

test.use({ storageState: authState('admin') })

const grantSection = (page) =>
  page.locator('section.card').filter({ has: page.locator('h2', { hasText: 'Grant admin to an email' }) })

/** Rows this spec creates are dropped straight back out, pass or fail. */
const purgeQaRows = async (request) => {
  const state = JSON.parse(fs.readFileSync(authState('admin'), 'utf8'))
  const token = state.origins[0].localStorage.find((e) => e.name === 'careerai_access').value
  const headers = { Authorization: `Bearer ${token}` }
  const res = await request.get('/api/auth/admin/super-emails/', { headers })
  if (!res.ok()) return
  const { results = [] } = await res.json()
  for (const row of results.filter((r) => r.email.startsWith('qa-super-'))) {
    await request.delete(`/api/auth/admin/super-emails/${row.id}/`, { headers })
  }
}

test('the page shell matches every other admin page', async ({ page }) => {
  await gotoAndWait(page, '/admin/super-emails')
  const shell = await page.evaluate(() => {
    const root = document.querySelector('.page')
    const banner = document.querySelector('.banner')
    const table = document.querySelector('.app-table-wrap')
    return {
      rootPadding: getComputedStyle(root).paddingLeft,
      rootMaxWidth: getComputedStyle(root).maxWidth,
      bannerPadding: getComputedStyle(banner).paddingLeft,
      tableOverflowX: table ? getComputedStyle(table).overflowX : 'missing',
    }
  })
  expect.soft(shell.rootPadding, 'the page shell must pad like every other admin page').toBe('24px')
  expect.soft(shell.rootMaxWidth).toBe('1080px')
  expect.soft(shell.bannerPadding, '.banner needs its own padding').not.toBe('0px')
  expect.soft(shell.tableOverflowX, '.app-table-wrap must own the horizontal scroll').toBe('auto')
})

test('the grant table scrolls in place instead of widening the page', async ({ page, request }) => {
  await page.setViewportSize({ width: 375, height: 667 })
  await purgeQaRows(request)
  await gotoAndWait(page, '/admin/super-emails')

  const email = `qa-super-${Date.now()}@example.com`
  try {
    const section = grantSection(page)
    await section.locator('input[type="email"]').fill(email)
    await section.getByRole('button', { name: /Add super email/ }).click()

    await expect(page.locator('.app-table tbody tr')).toBeVisible({ timeout: 15_000 })

    const measured = await measureOverflow(page)
    expect.soft(
      measured.scrollWidth,
      `super-emails @ 375px overflows by ${measured.scrollWidth - measured.clientWidth}px` +
        (measured.culprit.length ? ` — ${measured.culprit.join(', ')}` : ''),
    ).toBeLessThanOrEqual(measured.clientWidth + 1)
  } finally {
    await purgeQaRows(request)
  }
})
