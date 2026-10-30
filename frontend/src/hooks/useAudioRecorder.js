import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { mediaRecorderSupported, pickAudioMimeType } from '../lib/speech'

/**
 * Records one spoken answer from an existing microphone stream.
 *
 * Used when the in-page Web Speech API is unreliable (Edge) or unavailable.
 * The stream is owned by the level-meter hook, so the browser only opens one
 * microphone and the meter and recording always hear the same device.
 */
export function useAudioRecorder() {
  const supported = mediaRecorderSupported()
  const mimeType = useMemo(() => pickAudioMimeType(), [])
  const recorderRef = useRef(null)
  const chunksRef = useRef([])
  const [recording, setRecording] = useState(false)
  const [error, setError] = useState('')

  const stopTracks = useCallback((recorder) => {
    try {
      recorder?.stream?.getTracks?.().forEach((track) => track.stop())
    } catch {
      // The stream may already be closed by the meter.
    }
  }, [])

  const start = useCallback(
    (stream) => {
      if (!supported || !stream || recorderRef.current) return Boolean(recorderRef.current)
      setError('')
      chunksRef.current = []
      let recorder
      try {
        recorder = mimeType
          ? new window.MediaRecorder(stream, { mimeType })
          : new window.MediaRecorder(stream)
      } catch {
        try {
          recorder = new window.MediaRecorder(stream)
        } catch {
          setError('This browser could not start audio recording. Type your answer instead.')
          return false
        }
      }
      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) chunksRef.current.push(event.data)
      }
      recorder.onerror = () => {
        setError('Audio recording stopped unexpectedly. Try again or type your answer.')
      }
      try {
        recorder.start()
      } catch {
        setError('This browser could not start audio recording. Type your answer instead.')
        return false
      }
      recorderRef.current = recorder
      setRecording(true)
      return true
    },
    [mimeType, supported],
  )

  const stop = useCallback(
    () =>
      new Promise((resolve) => {
        const recorder = recorderRef.current
        if (!recorder) {
          resolve(null)
          return
        }
        let settled = false
        const finish = () => {
          if (settled) return
          settled = true
          recorderRef.current = null
          setRecording(false)
          const type = recorder.mimeType || mimeType || 'audio/webm'
          const chunks = chunksRef.current
          chunksRef.current = []
          resolve(chunks.length ? new Blob(chunks, { type }) : null)
        }
        recorder.onstop = finish
        recorder.onerror = finish
        try {
          if (recorder.state === 'inactive') finish()
          else recorder.stop()
        } catch {
          finish()
        }
        // Never leave the UI stuck if a browser fails to fire onstop.
        window.setTimeout(finish, 3000)
      }),
    [mimeType],
  )

  const cancel = useCallback(() => {
    const recorder = recorderRef.current
    recorderRef.current = null
    chunksRef.current = []
    setRecording(false)
    if (!recorder) return
    recorder.onstop = null
    recorder.ondataavailable = null
    recorder.onerror = null
    try {
      if (recorder.state !== 'inactive') recorder.stop()
    } catch {
      // Already stopped.
    }
    stopTracks(recorder)
  }, [stopTracks])

  useEffect(() => cancel, [cancel])

  return useMemo(
    () => ({ supported, recording, error, start, stop, cancel }),
    [supported, recording, error, start, stop, cancel],
  )
}

export default useAudioRecorder
