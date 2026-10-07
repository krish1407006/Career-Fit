import { expect, test } from '@playwright/test'
import { authState, gotoAndWait } from './helpers.js'

test.use({ storageState: authState('student') })

test('harness: both servers are up and the seeded student can sign in', async ({
  page,
  request,
}) => {
  const health = await request.get('/api/health/')
  expect(health.ok()).toBeTruthy()

  await gotoAndWait(page, '/')
  await expect(page).toHaveURL(/\/student$/)

  await gotoAndWait(page, '/student/jobs')
  await expect(page.locator('.job-list')).toBeVisible()
})
