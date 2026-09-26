import { useCallback, useEffect, useRef, useState } from 'react'
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
            utteranceRef.current = null
            setSpeaking(false)
            resolve(spoke)
          }
          utterance.onend = () => finish(true)
          utterance.onerror = () => finish(false)
          utteranceRef.current = utterance
          setSpeaking(true)
          window.speechSynthesis.speak(utterance)
        } catch {
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

  return { supported, speaking, muted, voice, speak, cancel, toggleMute }
}

export default useSpeechSynthesis
