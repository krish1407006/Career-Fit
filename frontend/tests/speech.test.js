import assert from 'node:assert/strict'
import test from 'node:test'

import {
  audioLevelSupported,
  cleanTranscript,
  describeRecognitionError,
  getSpeechRecognition,
  isUsableTranscript,
  makeClientToken,
  mergeSpokenTranscript,
  pickVoice,
  rmsToLevel,
  SILENCE_LEVEL,
  smoothLevel,
  SPEAKING_LEVEL,
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

test('mergeSpokenTranscript keeps words the browser never flagged final', () => {
  // Regression: Chrome ends a continuous session on a silence timeout, so a
  // fully spoken answer can still be sitting in the interim bucket when onend
  // fires. Reading only the final bucket reported "nothing recognised".
  assert.equal(mergeSpokenTranscript('', 'I built a Django project'), 'I built a Django project')
  assert.equal(
    mergeSpokenTranscript('I built a Django project', 'with JWT auth'),
    'I built a Django project with JWT auth',
  )
})

test('mergeSpokenTranscript collapses the seam between the two buckets', () => {
  assert.equal(mergeSpokenTranscript('first part ', ' second part'), 'first part second part')
  assert.equal(mergeSpokenTranscript('  ', '  '), '')
  assert.equal(mergeSpokenTranscript('', ''), '')
  assert.equal(mergeSpokenTranscript(null, undefined), '')
})

test('mergeSpokenTranscript output is always submittable when long enough', () => {
  const spoken = 'I would use a token refresh rotation with blacklisting'
  assert.equal(isUsableTranscript(mergeSpokenTranscript('', spoken), 3), true)
})

test('rmsToLevel reports silence for a centred buffer', () => {
  const silence = new Uint8Array(512).fill(128)
  assert.equal(rmsToLevel(silence), 0)
  assert.equal(rmsToLevel(new Uint8Array(0)), 0)
  assert.equal(rmsToLevel(null), 0)
})

test('rmsToLevel rises with loudness and stays within 0..1', () => {
  const at = (amplitude) => {
    const buffer = new Uint8Array(1024)
    for (let i = 0; i < buffer.length; i += 1) {
      buffer[i] = Math.max(0, Math.min(255, 128 + amplitude * Math.sin(i / 8)))
    }
    return rmsToLevel(buffer)
  }
  const quiet = at(6)
  const medium = at(24)
  const loud = at(90)
  assert.ok(quiet < medium, `quiet ${quiet} should be below medium ${medium}`)
  assert.ok(medium < loud, `medium ${medium} should be below loud ${loud}`)
  assert.ok(loud <= 1, 'level must never exceed 1')
  assert.ok(loud > SPEAKING_LEVEL, 'a loud voice must read as speaking')
  // A quiet but real voice has to clear the noise floor, or the meter stays dead
  // for soft speakers.
  assert.ok(quiet > SILENCE_LEVEL, `quiet speech ${quiet} must clear the noise floor`)
  assert.ok(quiet < SPEAKING_LEVEL, `quiet speech ${quiet} should not trip the speaking flag`)
})

test('rmsToLevel clips instead of overflowing on a full scale buffer', () => {
  const buffer = new Uint8Array(256)
  for (let i = 0; i < buffer.length; i += 1) buffer[i] = i % 2 === 0 ? 255 : 0
  assert.equal(rmsToLevel(buffer), 1)
})

test('smoothLevel rises quickly and falls slowly', () => {
  // Attack: a level jump should be mostly visible on the very next frame.
  const jumped = smoothLevel(0, 0.8)
  assert.ok(jumped > 0.4, `attack too slow: ${jumped}`)
  // Release: the bar should not flicker away between words.
  const released = smoothLevel(0.8, 0)
  assert.ok(released > 0.6 && released < 0.8, `release too fast: ${released}`)
  assert.equal(smoothLevel(0.5, 0.5), 0.5)
  assert.ok(Math.abs(smoothLevel(0, 0) - 0) < 1e-9)
})

test('smoothLevel converges on a steady level', () => {
  let level = 0
  for (let i = 0; i < 60; i += 1) level = smoothLevel(level, 0.5)
  assert.ok(Math.abs(level - 0.5) < 0.01, `did not converge: ${level}`)
})

test('audioLevelSupported requires both getUserMedia and an AudioContext', () => {
  withWindow({ AudioContext: function () {} }, () => {
    assert.equal(audioLevelSupported(), true)
  })
  withWindow({}, () => {
    assert.equal(audioLevelSupported(), false, 'no AudioContext means no meter')
  })
  withWindow(
    { AudioContext: function () {}, navigator: { mediaDevices: {} } },
    () => {
      assert.equal(audioLevelSupported(), false, 'no getUserMedia means no meter')
    },
  )
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
