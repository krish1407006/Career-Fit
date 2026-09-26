import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { pickVoice, speechSynthesisSupported } from '../lib/speech'

/**
 * Browser text-to-speech for the AI interviewer.
 *
 * `speak()` resolves when the utterance finishes (or is cancelled), which is
 * what lets the interview hand the turn over to the student at exactly the
 * right moment. Unsupported browsers simply never resolve into a "speaking"
 * state, and the question is always on screen as text.
 */
export function useSpeechSynthesis() {
  const supported = speechSynthesisSupported()
  const utteranceRef = useRef(null)
  const [speaking, setSpeaking] = useState(false)
  const [muted, setMuted] = useState(false)
  const [voice, setVoice] = useState(null)

  useEffect(() => {
    if (!supported) return undefined
    const synth = window.speechSynthesis
    const load = () => setVoice(pickVoice(synth.getVoices()))
    load()
    synth.addEventListener?.('voiceschanged', load)
    return () => {
      synth.removeEventListener?.('voiceschanged', load)
      synth.cancel()
    }
  }, [supported])

  const cancel = useCallback(() => {
    if (!supported) return
    try {
      window.speechSynthesis.cancel()
    } catch {
      // Nothing to cancel.
    }
    utteranceRef.current = null
    setSpeaking(false)
  }, [supported])

  /**
   * Speak text. Resolves true when it actually spoke, false when muted,
   * unsupported or empty, so the caller can move on immediately.
   *
   * A watchdog is essential rather than defensive: if the platform has no
   * installed voice it can accept the utterance and then never fire `onend` or
   * `onerror`. Without the timeout the interview would sit on "AI is speaking"
   * forever with no way for the student to answer.
   */
  const speak = useCallback(
    (text) =>
      new Promise((resolve) => {
        const content = String(text || '').trim()
        if (!content || muted || !supported || !content) {
          setSpeaking(false)
          resolve(false)
          return
        }
        let timer = null
        try {
          window.speechSynthesis.cancel()
          const utterance = new window.SpeechSynthesisUtterance(content)
          utterance.lang = 'en-US'
          utterance.rate = 1
          utterance.pitch = 1
          if (voice) utterance.voice = voice
          let settled = false
          const finish = (spoke) => {
            if (settled) return
            settled = true
            if (timer) clearTimeout(timer)
            utteranceRef.current = null
            setSpeaking(false)
            resolve(spoke)
          }
          utterance.onend = () => finish(true)
          utterance.onerror = () => finish(false)
          utteranceRef.current = utterance
          setSpeaking(true)
          window.speechSynthesis.speak(utterance)
          // ~380ms per word plus a floor, so a long question is not cut off.
          const words = content.split(/\s+/).length
          timer = setTimeout(() => {
            try {
              window.speechSynthesis.cancel()
            } catch {
              // Ignore: already finished.
            }
            finish(true)
          }, Math.max(6000, words * 380 + 3000))
        } catch {
          if (timer) clearTimeout(timer)
          setSpeaking(false)
          resolve(false)
        }
      }),
    [muted, supported, voice],
  )

  const toggleMute = useCallback(() => {
    setMuted((previous) => {
      if (previous) return false
      try {
        window.speechSynthesis?.cancel()
      } catch {
        // Ignore: nothing was speaking.
      }
      setSpeaking(false)
      return true
    })
  }, [])

  return useMemo(
    () => ({ supported, speaking, muted, voice, speak, cancel, toggleMute }),
    [supported, speaking, muted, voice, speak, cancel, toggleMute],
  )
}

export default useSpeechSynthesis
