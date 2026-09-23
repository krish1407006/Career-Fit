import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { apiError } from '../api/client'
import { useAuth } from '../context/AuthContext'

const initial = {
  username: '',
  email: '',
  password: '',
  first_name: '',
  last_name: '',
  role: 'student',
}

export default function Register() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState(initial)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await register(form)
      navigate('/login')
    } catch (err) {
      setError(apiError(err, 'Registration failed'))
    } finally {
      setBusy(false)
    }
  }

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value })

  return (
    <div className="auth-page">
      <form className="auth-card" onSubmit={submit}>
        <h1 className="brand center">Create account</h1>
        {error && <div className="alert error">{error}</div>}
        <div className="row">
          <label>
            First name
            <input value={form.first_name} onChange={set('first_name')} />
          </label>
          <label>
            Last name
            <input value={form.last_name} onChange={set('last_name')} />
          </label>
        </div>
        <label>
          Username
          <input value={form.username} onChange={set('username')} required />
        </label>
        <label>
          Email
          <input type="email" value={form.email} onChange={set('email')} required />
        </label>
        <label>
          Password (min 8 chars)
          <input type="password" value={form.password} onChange={set('password')} required />
        </label>
        <label>
          I am a
          <select value={form.role} onChange={set('role')}>
            <option value="student">Student</option>
            <option value="recruiter">Recruiter</option>
          </select>
        </label>
        <button className="btn btn-primary" disabled={busy}>
          {busy ? 'Creating…' : 'Create account'}
        </button>
        <p className="muted center">
          Already registered? <Link to="/login">Sign in</Link>
        </p>
      </form>
    </div>
  )
}