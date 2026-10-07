import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { expect, test } from '@playwright/test'
import { ROUTES, SIGNED_OUT, VIEWPORTS, authState, gotoAndWait, measureOverflow } from './helpers.js'

const screenshotsDir = path.join(path.dirname(fileURLToPath(import.meta.url)), 'screenshots')

const slug = (route) => route.replace(/[^a-z0-9]+/gi, '-').replace(/^-|-$/g, '') || 'root'

const sweep = async (page, role, viewport, routes) => {
  fs.mkdirSync(screenshotsDir, { recursive: true })
  for (const route of routes) {
    await gotoAndWait(page, route)
    const m = await measureOverflow(page)
    await page.screenshot({
      path: path.join(screenshotsDir, `${role}-${viewport.name}-${slug(route)}.png`),
      fullPage: false,
    })
    expect.soft(
      m.scrollWidth,
      `${role} @ ${viewport.width}px on ${route} overflows by ${m.scrollWidth - m.clientWidth}px` +
        (m.culprit.length ? ` — first offenders: ${m.culprit.join(', ')}` : ''),
    ).toBeLessThanOrEqual(m.clientWidth + 1)
  }
}

for (const role of Object.keys(ROUTES)) {
  test.describe(`${role} layout`, () => {
    test.use({ storageState: role === 'guest' ? SIGNED_OUT : authState(role) })

    for (const viewport of VIEWPORTS) {
      test(`${role} routes fit a ${viewport.name} (${viewport.width}px) viewport`, async ({ page }) => {
        await page.setViewportSize({ width: viewport.width, height: viewport.height })
        await sweep(page, role, viewport, ROUTES[role])
      })
    }
  })
}

test.describe('student detail pages', () => {
  test.use({ storageState: authState('student') })

  for (const viewport of VIEWPORTS) {
    test(`job + quiz detail fit a ${viewport.name} (${viewport.width}px) viewport`, async ({ page }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height })
      fs.mkdirSync(screenshotsDir, { recursive: true })

      await gotoAndWait(page, '/student/jobs')
      const jobLink = page.locator('.job-title-link').first()
      if (await jobLink.count()) {
        await jobLink.click()
        await page.waitForURL(/\/student\/jobs\/\d+$/)
        await page.locator('.detail-grid, .page').first().waitFor({ state: 'visible' })
        const job = await measureOverflow(page)
        await page.screenshot({ path: path.join(screenshotsDir, `student-${viewport.name}-job-detail.png`) })
        expect.soft(
          job.scrollWidth,
          `job detail @ ${viewport.width}px overflows by ${job.scrollWidth - job.clientWidth}px` +
            (job.culprit.length ? ` — ${job.culprit.join(', ')}` : ''),
        ).toBeLessThanOrEqual(job.clientWidth + 1)
      }

      await gotoAndWait(page, '/student/quizzes')
      const quizLink = page.locator('.job-list .card h3 a').first()
      if (await quizLink.count()) {
        await quizLink.click()
        await page.waitForURL(/\/student\/quizzes\/\d+$/)
        await page.locator('.page').first().waitFor({ state: 'visible' })
        const quiz = await measureOverflow(page)
        await page.screenshot({ path: path.join(screenshotsDir, `student-${viewport.name}-quiz-detail.png`) })
        expect.soft(
          quiz.scrollWidth,
          `quiz detail @ ${viewport.width}px overflows by ${quiz.scrollWidth - quiz.clientWidth}px` +
            (quiz.culprit.length ? ` — ${quiz.culprit.join(', ')}` : ''),
        ).toBeLessThanOrEqual(quiz.clientWidth + 1)
      }
    })
  }
})
