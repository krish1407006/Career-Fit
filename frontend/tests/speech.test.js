import assert from 'node:assert/strict'
import test from 'node:test'

import {
  cleanTranscript,
  describeRecognitionError,
  getSpeechRecognition,
  isUsableTranscript,
  makeClientToken,
  pickVoice,
  speechRecognitionBlocker,
  speechRecognitionSupported,
  speechSynthesisHasVoices,
  speechSynthesisSupported,
} from '../src/lib/speech.js'

/** Install a minimal fake window/navigator, then run fn with it in place. */
const withWindow = (win, fn) => {
  const previousWindow = globalThis.window
  const previousNavigator = globalThis.navigator
  globalThis.window = win
  Object.defineProperty(globalThis, 'navigator', {
    value: win.navigator ?? { mediaDevices: { getUserMedia: () => {} } },
    configurable: true,
    writable: true,
  })
  try {
    return fn()
  } finally {
    if (previousWindow === undefined) delete globalThis.window
    else globalThis.window = previousWindow
    if (previousNavigator === undefined) delete globalThis.navigator
    else {
      Object.defineProperty(globalThis, 'navigator', {
        value: previousNavigator,
        configurable: true,
        writable: true,
      })
    }
  }
}

const Recognition = function FakeRecognition() {}

test('getSpeechRecognition prefers the unprefixed constructor', () => {
  withWindow({ SpeechRecognition: Recognition }, () => {
    assert.equal(getSpeechRecognition(), Recognition)
    assert.equal(speechRecognitionSupported(), true)
  })
})

test('getSpeechRecognition falls back to the webkit prefix', () => {
  withWindow({ webkitSpeechRecognition: Recognition }, () => {
    assert.equal(getSpeechRecognition(), Recognition)
    assert.equal(speechRecognitionSupported(), true)
  })
})

test('blocker explains an insecure context even when the API exists', () => {
  // This is the case that silently kills the microphone: served over plain
  // http:// on a LAN address, the constructor exists but never gets a stream.
  withWindow({ isSecureContext: false, SpeechRecognition: Recognition }, () => {
    const reason = speechRecognitionBlocker()
    assert.match(reason, /secure connection/i)
    assert.equal(speechRecognitionSupported(), true, 'API presence is not the problem here')
  })
})

test('blocker explains a missing constructor', () => {
  withWindow({ isSecureContext: true }, () => {
    assert.equal(speechRecognitionSupported(), false)
    assert.match(speechRecognitionBlocker(), /Chrome or Edge/)
  })
})

test('blocker explains a missing mediaDevices', () => {
  withWindow({ isSecureContext: true, SpeechRecognition: Recognition, navigator: {} }, () => {
    assert.match(speechRecognitionBlocker(), /blocks microphone access/)
  })
})

test('blocker is null when everything is present', () => {
  withWindow({ isSecureContext: true, SpeechRecognition: Recognition }, () => {
    assert.equal(speechRecognitionBlocker(), null)
  })
})

test('speech synthesis support is detected from the constructor', () => {
  withWindow({ speechSynthesis: { getVoices: () => [] } }, () => {
    assert.equal(speechSynthesisSupported(), false)
    assert.equal(speechSynthesisHasVoices(), false)
  })
  withWindow({ speechSynthesis: { getVoices: () => [{ name: 'Alex', lang: 'en-US' }] },
    SpeechSynthesisUtterance: function () {} }, () => {
    assert.equal(speechSynthesisSupported(), true)
    assert.equal(speechSynthesisHasVoices(), true)
  })
})

test('pickVoice prefers a known English voice', () => {
  const chosen = pickVoice([
    { name: 'Zarvox', lang: 'ar-SA' },
    { name: 'Google UK English Male', lang: 'en-GB' },
  ])
  assert.equal(chosen.name, 'Google UK English Male')
})

test('pickVoice survives no voices at all', () => {
  assert.equal(pickVoice([]), null)
  assert.equal(pickVoice(null), null)
})

test('describeRecognitionError maps every code to an actionable message', () => {
  assert.match(describeRecognitionError({ error: 'not-allowed' }), /permission/i)
  assert.match(describeRecognitionError({ error: 'no-speech' }), /No speech/i)
  assert.match(describeRecognitionError({ error: 'audio-capture' }), /microphone/i)
  assert.match(describeRecognitionError({ error: 'network' }), /network/i)
  assert.equal(describeRecognitionError({ error: 'aborted' }), '', 'a manual stop is not an error')
  assert.ok(describeRecognitionError({ error: 'weird' }).length > 0)
})

test('cleanTranscript collapses whitespace and strips leading fillers', () => {
  assert.equal(cleanTranscript('  um   so   the  GIL '), 'so the GIL')
  assert.equal(cleanTranscript('uh, I built a project'), 'I built a project')
  assert.equal(cleanTranscript(''), '')
  assert.equal(cleanTranscript(null), '')
})

test('isUsableTranscript enforces a minimum word count', () => {
  assert.equal(isUsableTranscript('yes', 2), false)
  assert.equal(isUsableTranscript('two words', 2), true)
  assert.equal(isUsableTranscript('one two three', 3), true)
  assert.equal(isUsableTranscript('one two', 3), false)
  assert.equal(isUsableTranscript('', 2), false)
})

test('makeClientToken is unique and fits the 64 char column', () => {
  const tokens = new Set()
  for (let i = 0; i < 5000; i += 1) {
    const token = makeClientToken()
    assert.ok(token.length <= 64, `token too long: ${token.length}`)
    assert.ok(!tokens.has(token), 'token repeated, idempotency would break')
    tokens.add(token)
  }
})
