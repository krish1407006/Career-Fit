import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { apiError } from '../api/client'
import { useAuth } from '../context/authState'
import ThemeToggle from '../components/ThemeToggle'

const roleHome = (user) => {
  if (user.is_admin_role) return '/admin'
  if (user.role === 'recruiter') return '/recruiter'
  return '/student'
}

const allowedFrom = (user, pathname) =>
  pathname === '/profile' || pathname.startsWith(roleHome(user))

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [form, setForm] = useState({ username: '', password: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      const user = await login(form)
      const from = location.state?.from?.pathname
      if (from && allowedFrom(user, from)) {
        navigate(from, { replace: true })
      } else {
        navigate(roleHome(user), { replace: true })
      }
    } catch (err) {
      setError(apiError(err, 'Login failed'))
    } finally {
      setBusy(false)
    }
  }

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value })

  return (
    <div className="auth-page">
      <ThemeToggle />
      <div className="auth-shell">
        <aside className="auth-hero">
          <div className="brand brand-lg">Career<span>AI</span></div>
          <h2>Prep smarter. Interview with confidence.</h2>
          <p>
            AI-driven resume analysis, smart job matching, timed quizzes and live
            voice mock interviews — everything you need for placement season, in
            one place.
          </p>
          <ul className="auth-features">
            <li>
              <span className="af-icon">✓</span>
              <div>AI resume analysis<small>Reveal skill gaps and strengths instantly</small></div>
            </li>
            <li>
              <span className="af-icon">★</span>
              <div>Smart job matching<small>See how well you fit every role</small></div>
            </li>
            <li>
              <span className="af-icon">→</span>
              <div>Voice mock interviews<small>Practise with live AI feedback</small></div>
            </li>
          </ul>
        </aside>
        <form className="auth-card" onSubmit={submit}>
          <h1 className="brand center">Welcome back</h1>
          <p className="muted center">Sign in to continue your preparation.</p>
          {location.state?.notice && (
            <div className="alert ok">{location.state.notice}</div>
          )}
          {error && <div className="alert error">{error}</div>}
          <label>
            Username
            <input value={form.username} onChange={set('username')} autoFocus required />
          </label>
          <label>
            Password
            <input type="password" value={form.password} onChange={set('password')} required />
          </label>
          <button className="btn btn-primary" disabled={busy}>
            {busy ? 'Signing in…' : 'Sign in'}
          </button>
          <p className="muted center">
            New here? <Link to="/register">Create an account</Link>
          </p>
        </form>
      </div>
    </div>
  )
}