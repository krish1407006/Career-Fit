import { useCallback, useEffect, useRef, useState } from 'react'
import {
  cleanTranscript,
  describeRecognitionError,
  getSpeechRecognition,
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
  const recognitionRef = useRef(null)
  const finalRef = useRef('')
  const onFinalRef = useRef(onFinal)
  const [listening, setListening] = useState(false)
  const [interim, setInterim] = useState('')
  const [transcript, setTranscript] = useState('')
  const [error, setError] = useState('')

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
    setListening(false)
    setInterim('')
  }, [])

  // Never leave the microphone hot when the component unmounts or the student
  // navigates away mid-answer.
  useEffect(() => teardown, [teardown])

  const reset = useCallback(() => {
    finalRef.current = ''
    setTranscript('')
    setInterim('')
    setError('')
  }, [])

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

  const start = useCallback(() => {
    if (!supported) {
      setError('Voice input is not supported in this browser. Use text mode instead.')
      return
    }
    if (listening) return

    const Recognition = getSpeechRecognition()
    if (!Recognition) {
      setError('Voice input is not supported in this browser. Use text mode instead.')
      return
    }

    const recognition = new Recognition()
    recognition.lang = 'en-US'
    recognition.continuous = false
    recognition.interimResults = true
    recognition.maxAlternatives = 1

    finalRef.current = ''
    setTranscript('')
    setInterim('')
    setError('')

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
      setInterim(cleanTranscript(live))
      setTranscript(cleanTranscript(finalRef.current))
    }

    recognition.onerror = (event) => {
      const message = describeRecognitionError(event)
      if (message) setError(message)
    }

    recognition.onend = () => {
      const finalText = cleanTranscript(finalRef.current)
      recognitionRef.current = null
      setListening(false)
      setInterim('')
      if (finalText) {
        setTranscript(finalText)
        onFinalRef.current?.(finalText)
      } else if (!error) {
        setError('Nothing was recognised. Try again, or type your answer instead.')
      }
    }

    try {
      recognition.start()
      recognitionRef.current = recognition
      setListening(true)
    } catch {
      recognitionRef.current = null
      setListening(false)
      setError('The microphone could not be started. Type your answer instead.')
    }
  }, [error, listening, supported])

  return {
    supported,
    listening,
    /** Live preview of words not yet finalised. */
    interim,
    /** Final recognised transcript for the current answer. */
    transcript,
    error,
    start,
    stop,
    reset,
  }
}

export default useSpeechRecognition
