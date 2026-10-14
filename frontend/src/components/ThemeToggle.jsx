import { useEffect, useState } from 'react'

const isDark = () =>
  document.documentElement.getAttribute('data-theme') !== 'light'

export default function ThemeToggle() {
  const [dark, setDark] = useState(isDark)

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light')
    try {
      localStorage.setItem('careerai-theme', dark ? 'dark' : 'light')
    } catch {
      /* storage unavailable — theme still applies for this session */
    }
  }, [dark])

  return (
    <button
      type="button"
      className="btn btn-ghost btn-sm theme-toggle"
      onClick={() => setDark((value) => !value)}
      aria-label={dark ? 'Switch to light theme' : 'Switch to dark theme'}
      title={dark ? 'Switch to light theme' : 'Switch to dark theme'}
    >
      {dark ? '☀' : '☾'}
    </button>
  )
}
