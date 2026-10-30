import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  audioLevelSupported,
  rmsToLevel,
  SILENCE_LEVEL,
  smoothLevel,
  SPEAKING_LEVEL,
} from '../lib/speech'

/**
 * Live microphone level for the recording meter.
 *
 * The Web Speech API reports no amplitude at all, so the meter opens its own
 * `getUserMedia` stream and reads an `AnalyserNode`. In server-transcription
 * mode that same stream is handed to MediaRecorder, so the meter and the
 * recorded answer always come from one device. Otherwise the stream only drives
 * the level: it is never recorded or uploaded.
 *
 * The bar is written straight to the DOM through `barRef` inside the animation
 * frame instead of going through React state, because a level changes ~60 times
 * a second and re-rendering the interview that often would make it stutter.
 *
 * Failing to get a level is never fatal: the student can still type the answer.
 */
export function useAudioLevel({ onSpeakingChange, deviceId = '' } = {}) {
  const supported = audioLevelSupported()
  const [active, setActive] = useState(false)
  const [error, setError] = useState('')
  const [speaking, setSpeaking] = useState(false)
  // True when the stream is open but nothing has been heard for a while, which
  // almost always means the wrong input device is selected or it is muted.
  const [silent, setSilent] = useState(false)
  const [deviceLabel, setDeviceLabel] = useState('')

  // Owned here rather than passed in, so the animation frame can write to it
  // without reaching through an argument.
  const barRef = useRef(null)
  const streamRef = useRef(null)
  const contextRef = useRef(null)
  const frameRef = useRef(null)
  const samplesRef = useRef(null)
  const smoothedRef = useRef(0)
  const speakingRef = useRef(false)
  const silentRef = useRef(false)
  const lastSoundAtRef = useRef(0)
  const onSpeakingChangeRef = useRef(onSpeakingChange)

  useEffect(() => {
    onSpeakingChangeRef.current = onSpeakingChange
  }, [onSpeakingChange])

  const teardown = useCallback(() => {
    if (frameRef.current) {
      cancelAnimationFrame(frameRef.current)
      frameRef.current = null
    }
    const stream = streamRef.current
    if (stream) {
      // Releasing the hardware is the point: never leave the mic indicator on.
      stream.getTracks().forEach((track) => track.stop())
      streamRef.current = null
    }
    const context = contextRef.current
    if (context) {
      try {
        if (context.state !== 'closed') context.close()
      } catch {
        // Already closed.
      }
      contextRef.current = null
    }
    const bar = barRef.current
    if (bar) bar.style.width = '0%'
    smoothedRef.current = 0
    speakingRef.current = false
    silentRef.current = false
    lastSoundAtRef.current = 0
    setSpeaking(false)
    setSilent(false)
    setDeviceLabel('')
    setActive(false)
  }, [])

  useEffect(() => teardown, [teardown])

  const start = useCallback(async () => {
    if (!supported) return null
    if (streamRef.current) return streamRef.current
    setError('')
    try {
      const constraints = deviceId
        ? { audio: { deviceId: { exact: deviceId } } }
        : { audio: true }
      const stream = await navigator.mediaDevices.getUserMedia(constraints)
      streamRef.current = stream
      const track = stream.getAudioTracks?.()[0]
      setDeviceLabel(track?.label || '')
      lastSoundAtRef.current = performance.now()
      silentRef.current = false
      setSilent(false)

      const AudioContextClass = window.AudioContext || window.webkitAudioContext
      const context = new AudioContextClass()
      contextRef.current = context
      // Autoplay policies can hand back a suspended context on some browsers.
      if (context.state === 'suspended') await context.resume()

      const source = context.createMediaStreamSource(stream)
      const analyser = context.createAnalyser()
      analyser.fftSize = 2048
      // Do not let the meter alter what the microphone hears.
      analyser.smoothingTimeConstant = 0.6
      source.connect(analyser)
      samplesRef.current = new Uint8Array(analyser.fftSize)

      setActive(true)

      const tick = () => {
        const buffer = samplesRef.current
        const bar = barRef.current
        if (buffer && analyser) {
          analyser.getByteTimeDomainData(buffer)
          const level = rmsToLevel(buffer)
          smoothedRef.current = smoothLevel(smoothedRef.current, level)
          const shown = Math.round(smoothedRef.current * 100)
          if (bar) bar.style.width = `${shown}%`

          const nowSpeaking = smoothedRef.current >= SPEAKING_LEVEL
          if (nowSpeaking !== speakingRef.current) {
            speakingRef.current = nowSpeaking
            setSpeaking(nowSpeaking)
            onSpeakingChangeRef.current?.(nowSpeaking)
          }

          if (level >= SILENCE_LEVEL) {
            lastSoundAtRef.current = performance.now()
            if (silentRef.current) {
              silentRef.current = false
              setSilent(false)
            }
          } else if (
            !silentRef.current &&
            performance.now() - lastSoundAtRef.current > 4000
          ) {
            silentRef.current = true
            setSilent(true)
          }
        }
        frameRef.current = requestAnimationFrame(tick)
      }
      frameRef.current = requestAnimationFrame(tick)
      return stream
    } catch (err) {
      const name = err?.name || ''
      teardown()
      if (name === 'NotAllowedError' || name === 'SecurityError') {
        setError('Microphone access was blocked, so the level meter is unavailable.')
      } else if (name === 'NotFoundError') {
        setError('No microphone was found, so the level meter is unavailable.')
      } else {
        setError('The level meter could not start. Speech recognition still works.')
      }
      return null
    }
  }, [supported, teardown, deviceId])

  const stop = useCallback(() => {
    teardown()
  }, [teardown])

  return useMemo(
    () => ({ supported, active, speaking, silent, deviceLabel, error, start, stop, barRef }),
    [supported, active, speaking, silent, deviceLabel, error, start, stop],
  )
}

export default useAudioLevel
