import { expect, test } from '@playwright/test'
import { authState, gotoAndWait, measureOverflow } from './helpers.js'

test.use({ storageState: authState('admin') })

const grantSection = (page) =>
  page.locator('section.card').filter({ has: page.locator('h2', { hasText: 'Grant admin to an email' }) })

const removeQaRows = async (page) => {
  page.on('dialog', (dialog) => dialog.accept())
  for (;;) {
    const row = page.locator('.data-table tbody tr').filter({ hasText: 'qa-super-' }).first()
    if (!(await row.count())) break
    await row.getByRole('button', { name: 'Delete' }).click()
    await expect(row).toHaveCount(0, { timeout: 10_000 })
  }
}

test('the page shell matches every other admin page', async ({ page }) => {
  await gotoAndWait(page, '/admin/super-emails')
  const shell = await page.evaluate(() => {
    const root = document.querySelector('.page-stack')
    const banner = document.querySelector('.banner')
    return {
      rootPadding: getComputedStyle(root).paddingLeft,
      rootMaxWidth: getComputedStyle(root).maxWidth,
      bannerPadding: getComputedStyle(banner).paddingLeft,
    }
  })
  expect.soft(shell.rootPadding, '.page-stack must be a page shell like .page').toBe('24px')
  expect.soft(shell.rootMaxWidth).toBe('1080px')
  expect.soft(shell.bannerPadding, '.banner needs its own padding').not.toBe('0px')
})

test('the grant table scrolls in place instead of widening the page', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 667 })
  await gotoAndWait(page, '/admin/super-emails')
  await removeQaRows(page)

  const email = `qa-super-${Date.now()}@example.com`
  try {
    const section = grantSection(page)
    await section.locator('input[type="email"]').fill(email)
    await section.getByRole('button', { name: /Add super email/ }).click()

    const table = page.locator('.data-table')
    await expect(table).toBeVisible({ timeout: 15_000 })

    const wrapper = await page.evaluate(() => {
      const el = document.querySelector('.table-wrap')
      return {
        overflowX: getComputedStyle(el).overflowX,
        clientWidth: el.clientWidth,
        scrollWidth: el.scrollWidth,
      }
    })
    expect.soft(wrapper.overflowX, '.table-wrap must own the horizontal scroll').toBe('auto')

    const measured = await measureOverflow(page)
    expect.soft(
      measured.scrollWidth,
      `super-emails @ 375px overflows by ${measured.scrollWidth - measured.clientWidth}px` +
        (measured.culprit.length ? ` — ${measured.culprit.join(', ')}` : ''),
    ).toBeLessThanOrEqual(measured.clientWidth + 1)
  } finally {
    await removeQaRows(page)
  }
})
