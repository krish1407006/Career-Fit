import path from 'node:path'
import { fileURLToPath } from 'node:url'

const here = path.dirname(fileURLToPath(import.meta.url))

/** Absolute path to a storage-state file written by e2e/global-setup.js */
export const authState = (name) => path.join(here, '.auth', `${name}.json`)

export const SIGNED_OUT = { cookies: [], origins: [] }

/** Fixtures for the resume upload tests. Large files are generated at runtime. */
export const fixturesDir = path.join(here, 'fixtures')

export const VIEWPORTS = [
  { name: 'phone', width: 375, height: 667 },
  { name: 'tablet', width: 768, height: 1024 },
  // Guards the nav-wrap fix against regressing the wide layout.
  { name: 'desktop', width: 1280, height: 800 },
]

/** Routes to sweep, grouped by the role that is allowed to see them. */
export const ROUTES = {
  guest: ['/login', '/register'],
  student: [
    '/profile',
    '/student',
    '/student/profile',
    '/student/jobs',
    '/student/applications',
    '/student/quizzes',
    '/student/quizzes/history',
    '/student/interview',
  ],
  admin: [
    '/admin',
    '/admin/accounts',
    '/admin/quizzes',
    '/admin/resumes',
    '/admin/applications',
    '/admin/attempts',
    '/admin/interviews',
    '/admin/super-emails',
  ],
  recruiter: ['/recruiter', '/recruiter/jobs', '/recruiter/applications'],
}

/**
 * Measures page-level horizontal overflow: the document is wider than the
 * viewport, so the user has to scroll sideways to read the page. Overflow
 * inside a deliberately scrollable child (e.g. .app-table-wrap) does not
 * count, because it is clipped by that element rather than the document.
 */
export const measureOverflow = (page) =>
  page.evaluate(() => {
    const doc = document.documentElement
    const limit = doc.clientWidth
    const scrollWidth = Math.max(doc.scrollWidth, document.body.scrollWidth)
    const culprit = [...document.querySelectorAll('body *')]
      .filter((el) => el.getBoundingClientRect().right > limit + 1)
      .slice(0, 5)
      .map((el) => {
        const rect = el.getBoundingClientRect()
        const cls = String(el.className || '').split(' ')[0]
        return `${el.tagName.toLowerCase()}${cls ? `.${cls}` : ''} right=${Math.round(rect.right)}`
      })
    return { scrollWidth, clientWidth: limit, culprit }
  })

/**
 * Waits for the page shell plus its main content region, so measurements are
 * never taken against a half-rendered route.
 */
export const gotoAndWait = async (page, route) => {
  await page.goto(route, { waitUntil: 'domcontentloaded' })
  await page.locator('.app-shell, .auth-page').first().waitFor({ state: 'visible' })
  await page.locator('main, .auth-card, .page').first().waitFor({ state: 'visible' })
  await page.waitForFunction(() => !document.querySelector('.page-loading'), null, {
    timeout: 15_000,
  }).catch(() => {})
  // Let the page's own data requests land, otherwise tables and lists are
  // still empty when the caller measures or screenshots them.
  await page.waitForLoadState('networkidle', { timeout: 15_000 }).catch(() => {})
}
