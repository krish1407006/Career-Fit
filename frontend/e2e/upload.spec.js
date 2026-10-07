import fs from 'node:fs'
import path from 'node:path'
import { expect, test } from '@playwright/test'
import { authState, fixturesDir, gotoAndWait } from './helpers.js'

test.use({ storageState: authState('e2e-student') })

const token = () => {
  const state = JSON.parse(fs.readFileSync(authState('e2e-student'), 'utf8'))
  return state.origins[0].localStorage.find((e) => e.name === 'careerai_access').value
}

const api = (request, method, url, options = {}) =>
  request.fetch(url.startsWith('/') ? `/api${url}` : url, {
    method,
    headers: { Authorization: `Bearer ${token()}` },
    ...options,
  })

const clearResumes = async (request) => {
  const res = await api(request, 'GET', '/resumes/')
  if (!res.ok()) return
  const body = await res.json()
  const rows = Array.isArray(body) ? body : (body.results ?? [])
  for (const row of rows) await api(request, 'DELETE', `/resumes/${row.id}/`)
}

const fixtureB64 = (name) => fs.readFileSync(path.join(fixturesDir, name)).toString('base64')

/** Dispatches a native drag/drop event carrying a real File, as a drop would. */
const dragEvent = (page, type, descriptor) =>
  page.evaluate(
    ({ type, b64, size, name }) => {
      const bytes = size
        ? (() => {
            const b = new Uint8Array(size)
            b.set(new TextEncoder().encode('%PDF-1.4\n'))
            return b
          })()
        : Uint8Array.from(atob(b64), (c) => c.charCodeAt(0))
      const dt = new DataTransfer()
      dt.items.add(new File([bytes], name, { type: 'application/pdf' }))
      document
        .querySelector('.dropzone')
        .dispatchEvent(new DragEvent(type, { bubbles: true, cancelable: true, dataTransfer: dt }))
    },
    { type, ...descriptor },
  )

const dropFixture = (page, name) => dragEvent(page, 'drop', { name, b64: fixtureB64(name) })

const dropOversized = (page, name) => dragEvent(page, 'drop', { name, b64: '', size: 11 * 1024 * 1024 })

const dragOver = (page) => dragEvent(page, 'dragover', { name: 'probe.pdf', b64: fixtureB64('valid.pdf') })

const dragLeave = (page) =>
  page.evaluate(() => {
    document
      .querySelector('.dropzone')
      .dispatchEvent(new DragEvent('dragleave', { bubbles: true, cancelable: true, dataTransfer: new DataTransfer() }))
  })

/** Simulates the file picker: assigns .files then fires the change event. */
const pickFixture = (page, name) =>
  page.evaluate(
    ({ name, b64 }) => {
      const input = document.querySelector('input[type=file]')
      const dt = new DataTransfer()
      dt.items.add(
        new File([Uint8Array.from(atob(b64), (c) => c.charCodeAt(0))], name, { type: 'application/pdf' }),
      )
      input.files = dt.files
      input.dispatchEvent(new Event('change', { bubbles: true }))
    },
    { name, b64: fixtureB64(name) },
  )

const trackUploads = (page) => {
  const posts = []
  page.on('request', (request) => {
    if (request.method() === 'POST' && request.url().includes('/api/resumes/')) posts.push(request)
  })
  return posts
}

const alert = (page) => page.locator('.alert.error')

test('a dropped PDF uploads, and the request carries a multipart boundary', async ({
  page,
  request,
}) => {
  await clearResumes(request)
  const posts = trackUploads(page)
  await gotoAndWait(page, '/student/profile')
  await expect(page.locator('.dropzone')).toBeVisible()

  await dropFixture(page, 'valid.pdf')

  await expect(page.locator('.resume-head strong')).toHaveText('valid.pdf')
  expect(posts, 'exactly one upload').toHaveLength(1)
  expect(posts[0].headers()['content-type'], 'boundary must be present').toContain(
    'multipart/form-data; boundary=',
  )
})

test('a non-PDF dropped into the zone is rejected client-side with no request', async ({
  page,
  request,
}) => {
  await clearResumes(request)
  const posts = trackUploads(page)
  await gotoAndWait(page, '/student/profile')

  await dropFixture(page, 'resume.docx')

  await expect(alert(page)).toHaveText('Only PDF files are supported.')
  expect(posts, 'no request may leave the browser').toHaveLength(0)
})

test('a PDF extension holding HTML is rejected by the server', async ({ page, request }) => {
  await clearResumes(request)
  await gotoAndWait(page, '/student/profile')

  await dropFixture(page, 'fake.pdf')

  await expect(alert(page)).toContainText('PDF header')
})

test('an empty file is rejected by the server', async ({ page, request }) => {
  await clearResumes(request)
  await gotoAndWait(page, '/student/profile')

  await dropFixture(page, 'empty.pdf')

  await expect(alert(page)).toContainText('empty')
})

test('a file over 10 MB is rejected by the server', async ({ page, request }) => {
  await clearResumes(request)
  await gotoAndWait(page, '/student/profile')

  await dropOversized(page, 'huge.pdf')

  await expect(alert(page)).toContainText('under 10 MB')
})

test('the file input clears after an attempt so re-picking the same file works', async ({
  page,
  request,
}) => {
  await clearResumes(request)
  await gotoAndWait(page, '/student/profile')

  await pickFixture(page, 'fake.pdf')
  await expect(alert(page)).toContainText('PDF header')

  const value = await page.evaluate(() => document.querySelector('input[type=file]').value)
  expect(value, 'a leftover value means re-picking the same file fires no change event').toBe('')
})

test('a drop while an upload is in flight does not start a second upload', async ({
  page,
  request,
}) => {
  await clearResumes(request)
  const posts = trackUploads(page)
  await page.route('**/api/resumes/', async (route) => {
    if (route.request().method() === 'POST') await new Promise((r) => setTimeout(r, 1500))
    await route.continue()
  })

  await gotoAndWait(page, '/student/profile')
  await dropFixture(page, 'valid.pdf')
  await expect(page.locator('.dropzone')).toHaveText('Uploading…')

  await dropFixture(page, 'valid.pdf')

  await expect(page.locator('.resume-head strong')).toHaveText('valid.pdf', { timeout: 30_000 })
  expect(posts, 'uploads must not overlap').toHaveLength(1)
})

test('the download is served as an inert attachment', async ({ request }) => {
  await clearResumes(request)
  const upload = await api(request, 'POST', '/resumes/', {
    multipart: {
      file: {
        name: 'valid.pdf',
        mimeType: 'application/pdf',
        buffer: fs.readFileSync(path.join(fixturesDir, 'valid.pdf')),
      },
    },
  })
  expect(upload.status()).toBe(201)
  const { id } = await upload.json()

  const download = await api(request, 'GET', `/resumes/${id}/download/`)
  expect(download.status()).toBe(200)
  const headers = download.headers()
  expect(headers['content-type']).toBe('application/pdf')
  expect(headers['content-disposition']).toContain('attachment')
  expect(headers['x-content-type-options']).toBe('nosniff')
  expect(headers['content-security-policy']).toBe('sandbox')
  expect(headers['cache-control']).toContain('no-store')
})

test('the dropzone highlight follows the drag lifecycle', async ({ page, request }) => {
  await clearResumes(request)
  const posts = trackUploads(page)
  await gotoAndWait(page, '/student/profile')
  const zone = page.locator('.dropzone')

  await dragOver(page)
  await expect(zone).toHaveClass(/over/)

  await dragLeave(page)
  await expect(zone).not.toHaveClass(/over/)

  await dragOver(page)
  await page.evaluate(() => {
    const dt = new DataTransfer()
    dt.setData('text/plain', 'not a file')
    document
      .querySelector('.dropzone')
      .dispatchEvent(new DragEvent('drop', { bubbles: true, cancelable: true, dataTransfer: dt }))
  })
  await expect(zone).not.toHaveClass(/over/)
  expect(posts, 'a non-file drop must not upload').toHaveLength(0)
})
