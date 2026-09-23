import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { apiError } from '../api/client'
import { useAuth } from '../context/AuthContext'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ username: '', password: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await login(form)
      navigate('/')
    } catch (err) {
      setError(apiError(err, 'Login failed'))
    } finally {
      setBusy(false)
    }
  }

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value })

  return (
    <div className="auth-page">
      <form className="auth-card" onSubmit={submit}>
        <h1 className="brand center">Career<span>AI</span></h1>
        <p className="muted center">Placement preparation, powered by AI.</p>
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
  )
}