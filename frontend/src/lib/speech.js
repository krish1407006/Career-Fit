/**
 * Browser speech support detection and capability reporting.
 *
 * The Web Speech API is prefixed in some browsers, so everything is resolved
 * through these helpers instead of touching `window.SpeechRecognition`
 * directly. Pure functions, no React, so they are trivially testable.
 */

export const UNSUPPORTED_MESSAGE =
  'Voice input is not supported in this browser. Please use a supported browser or use text interview mode.'

export const TTS_UNSUPPORTED_MESSAGE =
  'Spoken questions are not supported in this browser, so questions will be shown as text only.'

/** Resolve the vendor-prefixed SpeechRecognition constructor, if any. */
export const getSpeechRecognition = () => {
  if (typeof window === 'undefined') return null
  return (
    window.SpeechRecognition ||
    window.webkitSpeechRecognition ||
    window.SpeechRecognitionConstructor ||
    null
  )
}

/** True when this browser can transcribe speech in-page. */
export const speechRecognitionSupported = () => Boolean(getSpeechRecognition())

/**
 * Why voice input cannot be used right now, or null when it can.
 *
 * The microphone is only exposed in a secure context, so `http://` on anything
 * other than localhost silently kills the feature. Reporting the reason turns a
 * dead button into something the student can act on.
 */
export const speechRecognitionBlocker = () => {
  if (typeof window === 'undefined') return 'No browser window is available.'
  if (!window.isSecureContext) {
    return 'Voice input needs a secure connection. Open the app on https:// or on http://localhost, not a plain http:// network address.'
  }
  if (!getSpeechRecognition()) {
    return 'This browser has no speech recognition. Chrome or Edge support it; in Firefox or Safari, type your answer instead.'
  }
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    return 'This browser blocks microphone access. Type your answer instead.'
  }
  return null
}

/** True when this browser can speak text aloud. */
export const speechSynthesisSupported = () =>
  typeof window !== 'undefined' &&
  'speechSynthesis' in window &&
  typeof window.SpeechSynthesisUtterance === 'function'

/** True when the platform exposes an installed voice for playback. */
export const speechSynthesisHasVoices = () => {
  if (!speechSynthesisSupported()) return false
  try {
    return window.speechSynthesis.getVoices().length > 0
  } catch {
    return false
  }
}

/**
 * Pick the most suitable installed voice.
 *
 * Prefers an English voice and a natural "Google UK English Male"-style name so
 * the interviewer sounds like a person rather than a robot.
 */
export const pickVoice = (voices) => {
  if (!Array.isArray(voices) || voices.length === 0) return null
  const english = voices.filter((v) => /^en(-|_|$)/i.test(v.lang || ''))
  const pool = english.length ? english : voices
  const preferred = ['Google UK English Male', 'Google US English', 'Microsoft David',
    'Microsoft Mark', 'Alex', 'Daniel', 'Google UK English Female']
  return (
    pool.find((v) => preferred.includes(v.name)) ||
    pool.find((v) => v.localService) ||
    pool[0]
  )
}

/** Human-readable messages for Web Speech error codes. */
export const describeRecognitionError = (error) => {
  const code = error?.error || error
  switch (code) {
    case 'not-allowed':
    case 'service-not-allowed':
      return 'Microphone access was blocked. Allow microphone permission in your browser and try again.'
    case 'no-speech':
      return 'No speech was detected. Start speaking when you are ready, or type your answer instead.'
    case 'audio-capture':
      return 'No microphone was found. Connect a microphone, or type your answer instead.'
    case 'network':
      return 'Speech recognition needs a network connection in this browser. You can type your answer instead.'
    case 'aborted':
      return ''
    default:
      return 'Speech recognition stopped unexpectedly. You can retype or record your answer again.'
  }
}

/**
 * Strip filler words and clean a raw transcript for review/submission.
 * Conservative on purpose: it never rewrites the candidate's meaning.
 */
export const cleanTranscript = (text) =>
  String(text || '')
    .replace(/\s+/g, ' ')
    .trim()
    // Trim first: the recognizer often emits a leading space, which would
    // otherwise stop the anchored filler pattern from matching.
    .replace(/^(uh+|um+|erm+|hmm+)[,\s]*/i, '')
    .trim()

/**
 * Assemble the transcript to keep once a recognition session ends.
 *
 * The browser ends a continuous session on its own after a silence timeout, and
 * words it heard may never be flagged `isFinal`. Reading only the final bucket
 * would silently discard a clearly spoken answer and report "nothing
 * recognised", so the pending interim words are promoted into the result.
 */
export const mergeSpokenTranscript = (finalText, interimText) =>
  cleanTranscript(`${finalText || ''} ${interimText || ''}`.trim())

/** A transcript long enough to be worth evaluating. */
export const isUsableTranscript = (text, minWords = 3) =>
  cleanTranscript(text).split(' ').filter(Boolean).length >= minWords

// ---------------------------------------------------------------------------
// Microphone level meter
// ---------------------------------------------------------------------------

/** Below this level the room is considered silent. */
export const SILENCE_LEVEL = 0.06
/** At or above this level the student is considered to be speaking. */
export const SPEAKING_LEVEL = 0.16

/**
 * Root-mean-square amplitude of one analyser frame, mapped to 0..1.
 *
 * `getByteTimeDomainData` is centred on 128, so it is re-centred and scaled
 * first. The gain compensates for normal speech sitting well below full scale;
 * without it the meter barely moves for a quiet voice.
 */
export const rmsToLevel = (samples, gain = 3.4) => {
  if (!samples || samples.length === 0) return 0
  let sum = 0
  for (let i = 0; i < samples.length; i += 1) {
    const centred = (samples[i] - 128) / 128
    sum += centred * centred
  }
  const rms = Math.sqrt(sum / samples.length)
  const level = rms * gain
  return level > 1 ? 1 : level
}

/**
 * Ballistics for the meter: rise fast so speech onset is obvious, fall slowly so
 * the bar does not flicker between words.
 */
export const smoothLevel = (previous, next, rise = 0.55, fall = 0.12) =>
  previous + (next - previous) * (next > previous ? rise : fall)

/** True when the browser can expose a live microphone level. */
export const audioLevelSupported = () =>
  typeof window !== 'undefined' &&
  typeof navigator !== 'undefined' &&
  Boolean(navigator.mediaDevices && navigator.mediaDevices.getUserMedia) &&
  Boolean(window.AudioContext || window.webkitAudioContext)

/**
 * Stable idempotency key for one answer, so a double click or a retried request
 * can never evaluate the same answer twice. No crypto dependency: the backend
 * only needs a unique-per-answer string.
 */
export const makeClientToken = () => {
  const random = Math.random().toString(36).slice(2, 10)
  return `ans-${Date.now().toString(36)}-${random}`.slice(0, 64)
}
