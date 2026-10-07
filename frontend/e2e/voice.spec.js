import { expect, test } from '@playwright/test'
import { authState, gotoAndWait } from './helpers.js'

// The voice interview is a conversation with a human, so the parts that need
// real speech are covered by a person (see e2e/VOICE-MANUAL.md). What is
// automated here is everything deterministic: capability detection, failure
// messages, the listening/turn state machine, microphone release and the
// promise that no audio ever leaves the browser.
test.use({ storageState: authState('e2e-student') })

/**
 * Replace the browser's SpeechRecognition with a controllable fake.
 *
 * Headless Chrome either has no recogniser or reports arbitrary errors, so the
 * failure paths a student actually hits (denied permission, silence timeout,
 * network failure, a recognised sentence) are driven explicitly instead.
 */
const installFakeSTT = (page, mode) =>
  page.addInitScript(
    ({ mode }) => {
      const fire = (fn, arg) => {
        try {
          fn?.(arg)
        } catch {
          // A listener threw; the fake must not take the page down with it.
        }
      }
      class FakeRecognition {
        constructor() {
          this.continuous = false
          this.interimResults = false
          this.lang = ''
          this.onresult = null
          this.onerror = null
          this.onend = null
        }

        start() {
          if (mode === 'denied') {
            setTimeout(() => {
              fire(this.onerror, { error: 'not-allowed' })
              fire(this.onend)
            }, 20)
          } else if (mode === 'silent') {
            setTimeout(() => fire(this.onend), 20)
          } else if (mode === 'network') {
            setTimeout(() => {
              fire(this.onerror, { error: 'network' })
              fire(this.onend)
            }, 20)
          } else if (mode === 'speech') {
            setTimeout(() => {
              const final = { isFinal: true }
              final[0] = { transcript: 'I have spent five years building Django REST APIs.' }
              fire(this.onresult, { resultIndex: 0, results: [final] })
            }, 20)
          }
          // 'manual' stays open until stop(), so the test owns the timing.
        }

        stop() {
          setTimeout(() => fire(this.onend), mode === 'manual' ? 3_000 : 20)
        }

        abort() {
          setTimeout(() => fire(this.onend), 0)
        }
      }
      for (const key of ['SpeechRecognition', 'webkitSpeechRecognition']) {
        try {
          Object.defineProperty(window, key, { value: FakeRecognition, configurable: true })
        } catch {
          try {
            window[key] = FakeRecognition
          } catch {
            // The platform kept it read-only; the test will fail loudly below.
          }
        }
      }
    },
    { mode },
  )

/** Headless Chrome installs no voice, so never wait on the TTS watchdog. */
const installInstantTTS = (page) =>
  page.addInitScript(() => {
    const synth = window.speechSynthesis
    if (!synth) return
    synth.speak = (utterance) => setTimeout(() => utterance.onend?.(), 0)
  })

/** Count microphone streams opened and tracks stopped, to catch a leaked mic. */
const installMediaCounters = (page) =>
  page.addInitScript(() => {
    window.__media = { opens: 0, stops: 0 }
    const gum = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices)
    navigator.mediaDevices.getUserMedia = (constraints) => {
      window.__media.opens += 1
      return gum(constraints)
    }
    const stopTrack = MediaStreamTrack.prototype.stop
    MediaStreamTrack.prototype.stop = function stop() {
      window.__media.stops += 1
      return stopTrack.call(this)
    }
  })

/** A warning that carries the given text, without tripping strict mode. */
const warn = (page, text) => page.locator('.alert.warn').filter({ hasText: text })

/** Reads the turn pill and the mic button together: they must always agree. */
const stageState = (page) =>
  page.evaluate(() => {
    const stageEl = document.querySelector('.voice-stage')
    const micEl = document.querySelector('.mic-btn')
    return {
      stageClass: stageEl ? [...stageEl.classList].find((c) => c.startsWith('stage-')) : null,
      listening: Boolean(stageEl && stageEl.classList.contains('stage-listening')),
      micLabel: micEl ? micEl.textContent.trim() : null,
      stopLabel: Boolean(micEl && /Stop recording/.test(micEl.textContent)),
      disabled: Boolean(micEl && micEl.disabled),
    }
  })

const cancelActive = async (page) => {
  try {
    await page.evaluate(async () => {
      const headers = { Authorization: `Bearer ${localStorage.getItem('careerai_access') || ''}` }
      const active = await fetch('/api/interviews/active/', { headers })
      if (!active.ok) return
      const data = await active.json()
      if (data?.id) await fetch(`/api/interviews/${data.id}/cancel/`, { method: 'POST', headers })
    })
  } catch {
    // The page may have navigated away; the next start discards leftovers anyway.
  }
}

/** Signs in, drops any leftover session and starts a fresh voice interview. */
const startInterview = async (page, { role = 'Python Developer' } = {}) => {
  await gotoAndWait(page, '/student/interview')
  const discard = page.getByRole('button', { name: 'Discard it' })
  if (await discard.isVisible().catch(() => false)) {
    await discard.click()
    await expect(page.getByRole('button', { name: 'Start interview' })).toBeEnabled()
  }
  await page.getByLabel('Target role').fill(role)
  await page.getByRole('button', { name: 'Start interview' }).click()
  await expect(page.locator('.voice-interview')).toBeVisible({ timeout: 30_000 })
  await expect(page.locator('.voice-stage')).toHaveClass(/stage-awaiting_answer/, {
    timeout: 20_000,
  })
}

const mic = (page) => page.locator('.mic-btn')
const stage = (page) => page.locator('.voice-stage')
const header = (page) => page.locator('.voice-interview .page-head .muted')

/** Asserts the panel advanced to the next question after a successful answer. */
const expectNextQuestion = async (page) => {
  const text = await header(page).textContent()
  const found = /Question (\d+) of (\d+)/.exec(String(text || ''))
  expect(found, `question header was: ${text}`).toBeTruthy()
  await expect(header(page)).toContainText(`Question ${Number(found[1]) + 1} of ${found[2]}`, {
    timeout: 30_000,
  })
}

test.afterEach(async ({ page }) => {
  await cancelActive(page)
})

test('voice: a browser without speech recognition falls back to typing', async ({ page }) => {
  await installInstantTTS(page)
  await page.addInitScript(() => {
    for (const key of ['SpeechRecognition', 'webkitSpeechRecognition']) {
      try {
        Object.defineProperty(window, key, { value: undefined, configurable: true })
      } catch {
        try {
          window[key] = undefined
        } catch {
          // Leave it in place; the assertions below will report the failure.
        }
      }
    }
  })

  await gotoAndWait(page, '/student/interview')
  await expect(warn(page, 'This browser has no speech recognition')).toBeVisible()
  // The interview itself must never be gated on voice support.
  await expect(page.getByRole('button', { name: 'Start interview' })).toBeEnabled()

  await startInterview(page)
  await expect(warn(page, 'no speech recognition')).toBeVisible()
  await expect(mic(page)).toBeDisabled()
  await expect(mic(page)).toHaveText(/Start speaking/)

  await page
    .getByLabel('Or type / edit your answer')
    .fill('I built a Django REST API for the payments team last year.')
  await expect(page.getByRole('button', { name: 'Submit answer' })).toBeEnabled()
  await page.getByRole('button', { name: 'Submit answer' }).click()
  await expectNextQuestion(page)
  expect((await stageState(page)).listening).toBe(false)
})

test('voice: an insecure connection explains why the microphone is off', async ({ page }) => {
  await installInstantTTS(page)
  await page.addInitScript(() => {
    Object.defineProperty(window, 'isSecureContext', { get: () => false, configurable: true })
  })

  await gotoAndWait(page, '/student/interview')
  await expect(warn(page, 'Voice input needs a secure connection')).toBeVisible()

  await startInterview(page)
  await expect(warn(page, 'secure connection')).toBeVisible()
  await expect(mic(page)).toBeDisabled()
  expect((await stageState(page)).micLabel).toMatch(/Start speaking/)
})

test('voice: a blocked microphone says so and hands the turn back', async ({ page }) => {
  await installInstantTTS(page)
  await installFakeSTT(page, 'denied')
  await startInterview(page)

  await mic(page).click()
  await expect(warn(page, 'Microphone access was blocked')).toBeVisible()
  await expect(mic(page)).toHaveText(/Start speaking/)
  // Nothing is recording any more, so the pill must not claim it is.
  await expect(stage(page)).not.toHaveClass(/stage-listening/, { timeout: 5_000 })

  const state = await stageState(page)
  expect(state.listening).toBe(false)
  expect(state.stopLabel).toBe(false)
  expect(state.stageClass).toBe('stage-awaiting_answer')
})

test('voice: an auto-ended session gives the turn back and releases the mic', async ({
  page,
}) => {
  await installInstantTTS(page)
  await installMediaCounters(page)
  await installFakeSTT(page, 'silent')
  await startInterview(page)

  await mic(page).click()
  await expect(warn(page, 'Nothing was recognised')).toBeVisible()
  await expect(stage(page)).not.toHaveClass(/stage-listening/, { timeout: 5_000 })
  await expect(mic(page)).toHaveText(/Start speaking/)

  // Chrome ends a silent session on its own; the OS mic indicator must go with it.
  await expect
    .poll(() => page.evaluate(() => window.__media), { timeout: 5_000 })
    .toEqual({ opens: 1, stops: 1 })
})

test('voice: a level meter that cannot start does not block the answer', async ({ page }) => {
  await installInstantTTS(page)
  await installFakeSTT(page, 'speech')
  await page.addInitScript(() => {
    navigator.mediaDevices.getUserMedia = () =>
      Promise.reject(Object.assign(new Error('blocked'), { name: 'NotAllowedError' }))
  })

  await startInterview(page)
  await mic(page).click()
  await expect(warn(page, 'level meter is unavailable')).toBeVisible()
  // Speech recognition keeps working with the meter down.
  await expect(page.getByLabel('Recognised transcript')).toHaveValue(/Django REST APIs/)
  await expect(stage(page)).toHaveClass(/stage-listening/)

  await mic(page).click()
  await expect(stage(page)).not.toHaveClass(/stage-listening/)
  await expect(page.getByLabel('Recognised transcript')).toHaveValue(/Django REST APIs/)
})

test('voice: a failed submit keeps the transcript and hands the turn back', async ({ page }) => {
  await installInstantTTS(page)
  await installFakeSTT(page, 'speech')
  await startInterview(page)

  await mic(page).click()
  await expect(page.getByLabel('Recognised transcript')).toHaveValue(/Django REST APIs/)
  await mic(page).click()

  await page.route('**/interviews/*/answer/', (route) => route.abort())
  await page.getByRole('button', { name: 'Submit answer' }).click()

  await expect(page.locator('.voice-interview .alert.error')).toContainText(
    'Could not submit your answer',
  )
  await expect(stage(page)).toHaveClass(/stage-awaiting_answer/)
  await expect(page.getByLabel('Recognised transcript')).toHaveValue(/Django REST APIs/)
  await expect(page.getByRole('button', { name: 'Submit answer' })).toBeEnabled()
  expect((await stageState(page)).listening).toBe(false)
})

test('voice: only the transcript is sent over the network, never audio', async ({ page }) => {
  await installInstantTTS(page)
  await installFakeSTT(page, 'speech')
  const requests = []
  page.on('request', (r) =>
    requests.push({ url: r.url(), type: r.resourceType(), body: r.postData() || '' }),
  )

  await startInterview(page)
  await mic(page).click()
  await expect(page.getByLabel('Recognised transcript')).toHaveValue(/Django REST APIs/)
  await mic(page).click()
  await page.getByRole('button', { name: 'Submit answer' }).click()
  await expectNextQuestion(page)

  const answers = requests.filter((r) => /\/interviews\/\d+\/answer\//.test(r.url))
  expect(answers).toHaveLength(1)

  // No media stream, no blob/data URL, and nothing that looks like encoded audio.
  expect(requests.filter((r) => r.type === 'media')).toEqual([])
  expect(requests.filter((r) => /^(blob|data):/.test(r.url))).toEqual([])
  expect(requests.filter((r) => /audio\/|video\/|;base64,/.test(r.body))).toEqual([])

  // No app call leaves the machine: no cloud speech service, no telemetry.
  const appCalls = requests.filter((r) => r.type === 'xhr' || r.type === 'fetch')
  expect(appCalls.length).toBeGreaterThan(0)
  expect(
    appCalls.filter((r) => !/^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?(\/|$)/.test(r.url)),
  ).toEqual([])
})

test('voice: leaving the interview releases the microphone', async ({ page }) => {
  await installInstantTTS(page)
  await installMediaCounters(page)
  await installFakeSTT(page, 'speech')
  await startInterview(page)

  await mic(page).click()
  await expect.poll(() => page.evaluate(() => window.__media.opens)).toBeGreaterThan(0)
  await expect(page.getByRole('link', { name: 'Jobs', exact: true })).toBeVisible()
  await page.getByRole('link', { name: 'Jobs', exact: true }).click()
  await expect(page).toHaveURL(/\/student\/jobs/)

  // The route change unmounts the panel; a live stream must not survive it.
  await expect
    .poll(() => page.evaluate(() => window.__media), { timeout: 5_000 })
    .toEqual({ opens: 1, stops: 1 })
})

test('voice: a stale recogniser end cannot kill the next recording', async ({ page }) => {
  await installInstantTTS(page)
  await installFakeSTT(page, 'manual')
  await startInterview(page)

  // Stop, then stop again while the first session is still winding down, so its
  // late `onend` lands after a fresh recording has already begun.
  await mic(page).click()
  await expect(stage(page)).not.toHaveClass(/stage-listening/)
  await page.waitForTimeout(2_500)
  await expect(mic(page)).toHaveText(/Stop recording/)
  await mic(page).click()

  await expect(mic(page)).toHaveText(/Start speaking/, { timeout: 5_000 })
  await mic(page).click()
  await expect(stage(page)).toHaveClass(/stage-listening/)
  await expect(mic(page)).toHaveText(/Stop recording/)

  // The abandoned recogniser's `onend` fires here and must be ignored.
  await page.waitForTimeout(3_000)
  const state = await stageState(page)
  expect(state.stopLabel).toBe(true)
  expect(state.listening).toBe(true)
  expect(state.stageClass).toBe('stage-listening')
  expect(state.disabled).toBe(false)
})
