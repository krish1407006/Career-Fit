import { useCallback, useEffect, useState } from 'react'

/**
 * Lists available microphones so the student can pick the one that is actually
 * connected. Labels stay blank until microphone permission is granted, so
 * `refresh` is called again after the stream opens.
 */
export function useAudioInputs() {
  const [devices, setDevices] = useState([])
  const supported = Boolean(
    typeof navigator !== 'undefined' &&
      navigator.mediaDevices &&
      navigator.mediaDevices.enumerateDevices,
  )

  const refresh = useCallback(async () => {
    if (!supported) return
    try {
      const all = await navigator.mediaDevices.enumerateDevices()
      setDevices(all.filter((device) => device.kind === 'audioinput'))
    } catch {
      // Device listing is optional; the system default still works.
    }
  }, [supported])

  useEffect(() => {
    if (!supported) return undefined
    let cancelled = false
    const load = async () => {
      try {
        const all = await navigator.mediaDevices.enumerateDevices()
        if (!cancelled) {
          setDevices(all.filter((device) => device.kind === 'audioinput'))
        }
      } catch {
        // Device listing is optional; the system default still works.
      }
    }
    load()
    navigator.mediaDevices.addEventListener?.('devicechange', load)
    return () => {
      cancelled = true
      navigator.mediaDevices.removeEventListener?.('devicechange', load)
    }
  }, [supported])

  return { devices, refresh, supported }
}

export default useAudioInputs
