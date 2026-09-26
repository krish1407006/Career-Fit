import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  cleanTranscript,
  describeRecognitionError,
  getSpeechRecognition,
  mergeSpokenTranscript,
  speechRecognitionBlocker,
  speechRecognitionSupported,
} from '../lib/speech'

/**
 * Browser speech recognition (speech -> text) for the voice interview.
 *
 * Recording only ever starts from an explicit user action: `start()` is called
 * from the microphone button, never automatically. `continuous` is false so a
 * single answer ends on its own, and partial results are surfaced as a live
 * preview while the final result is what gets submitted.
 *
 * The hook degrades safely: an unsupported browser, a denied permission or a
 * network error all resolve to a message plus `supported: false`, and the
 * interview continues in text mode.
 */
export function useSpeechRecognition({ onFinal } = {}) {
  const supported = speechRecognitionSupported()
  const blocker = useMemo(() => speechRecognitionBlocker(), [])
  const recognitionRef = useRef(null)
  const finalRef = useRef('')
  // Words heard but not yet flagged final. Kept so an auto-ended session does
  // not discard a clearly spoken answer.
  const interimRef = useRef('')
  const lastErrorCodeRef = useRef('')
  const onFinalRef = useRef(onFinal)
  // `onend` fires after `onerror`, and it must not overwrite the real reason the
  // microphone failed, so the message is tracked in a ref rather than read from
  // a stale render closure.
  const errorRef = useRef('')
  const listeningRef = useRef(false)
  const [listening, setListening] = useState(false)
  const [interim, setInterim] = useState('')
  const [transcript, setTranscript] = useState('')
  const [error, setError] = useState('')

  const setErrorBoth = useCallback((message) => {
    errorRef.current = message
    setError(message)
  }, [])

  useEffect(() => {
    onFinalRef.current = onFinal
  }, [onFinal])

  const teardown = useCallback(() => {
    const recognition = recognitionRef.current
    if (recognition) {
      recognition.onresult = null
      recognition.onerror = null
      recognition.onend = null
      try {
        recognition.stop()
      } catch {
        // Already stopped; nothing to do.
      }
    }
    recognitionRef.current = null
    listeningRef.current = false
    setListening(false)
    setInterim('')
  }, [])

  // Never leave the microphone hot when the component unmounts or the student
  // navigates away mid-answer.
  useEffect(() => teardown, [teardown])

  const reset = useCallback(() => {
    finalRef.current = ''
    interimRef.current = ''
    lastErrorCodeRef.current = ''
    setTranscript('')
    setInterim('')
    setErrorBoth('')
  }, [setErrorBoth])

  const stop = useCallback(() => {
    const recognition = recognitionRef.current
    if (recognition) {
      try {
        recognition.stop()
      } catch {
        // Already stopped.
      }
    }
  }, [])

  // Stable identity: the panel memoises callbacks on it, so a new object per
  // render would re-create them constantly.
  const start = useCallback(() => {
    if (listeningRef.current) return

    const Recognition = getSpeechRecognition()
    if (!Recognition) {
      setErrorBoth(
        speechRecognitionBlocker() ||
          'Voice input is not supported in this browser. Use text interview mode instead.',
      )
      return
    }

    const recognition = new Recognition()
    recognition.lang = 'en-US'
    recognition.continuous = true
    recognition.interimResults = true
    recognition.maxAlternatives = 1

    finalRef.current = ''
    interimRef.current = ''
    setTranscript('')
    setInterim('')
    setErrorBoth('')

    recognition.onresult = (event) => {
      let live = ''
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const result = event.results[i]
        const alternative = result[0]
        if (!alternative) continue
        if (result.isFinal) {
          finalRef.current += `${alternative.transcript} `
        } else {
          live += alternative.transcript
        }
      }
      interimRef.current = live
      setInterim(cleanTranscript(live))
      setTranscript(cleanTranscript(`${finalRef.current} ${live}`.trim()))
    }

    recognition.onerror = (event) => {
      lastErrorCodeRef.current = event?.error || ''
      const message = describeRecognitionError(event)
      if (message) setErrorBoth(message)
    }

    recognition.onend = () => {
      // Promote whatever was heard. Chrome ends a continuous session on its own
      // after a silence timeout, and results that were never flagged final must
      // not be thrown away, otherwise a clearly spoken answer reports as
      // "nothing recognised".
      const finalText = mergeSpokenTranscript(finalRef.current, interimRef.current)
      recognitionRef.current = null
      listeningRef.current = false
      setListening(false)
      setInterim('')
      if (finalText) {
        setTranscript(finalText)
        onFinalRef.current?.(finalText)
      } else if (!errorRef.current) {
        setErrorBoth(
          lastErrorCodeRef.current
            ? `Speech recognition stopped (${lastErrorCodeRef.current}). Type your answer instead.`
            : 'Nothing was recognised. Check the microphone is unmuted and try again, or type your answer.',
        )
      }
    }

    try {
      recognition.start()
      recognitionRef.current = recognition
      listeningRef.current = true
      setListening(true)
    } catch {
      recognitionRef.current = null
      listeningRef.current = false
      setListening(false)
      setErrorBoth('The microphone could not be started. Type your answer instead.')
    }
  }, [setErrorBoth])

  return useMemo(
    () => ({
      supported,
      blocker,
      listening,
      /** Live preview of words not yet finalised. */
      interim,
      /** Final recognised transcript for the current answer. */
      transcript,
      error,
      start,
      stop,
      reset,
    }),
    [supported, blocker, listening, interim, transcript, error, start, stop, reset],
  )
}

export default useSpeechRecognition
