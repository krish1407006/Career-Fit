import { useState } from 'react'
import { apiError } from '../api/client'
import { useAuth } from '../context/AuthContext'

export default function Profile() {
  const { user, profile, updateProfile } = useAuth()
  const [form, setForm] = useState(
    profile || {
      full_name: '', college: '', branch: '', graduation_year: '',
      cgpa: '', phone: '', location: '', preferred_roles: [],
    },
  )
  const [msg, setMsg] = useState({ type: '', text: '' })
  const [busy, setBusy] = useState(false)

  if (!user) return null

  const isStudent = user.role === 'student'

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setMsg({ type: '', text: '' })
    try {
      await updateProfile({ profile: form })
      setMsg({ type: 'ok', text: 'Profile saved.' })
    } catch (err) {
      setMsg({ type: 'error', text: apiError(err, 'Failed to save profile') })
    } finally {
      setBusy(false)
    }
  }

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value })
  const rolesText = form.preferred_roles.join(', ')

  return (
    <div className="page">
      <h1>My profile</h1>
      {msg.text && <div className={`alert ${msg.type}`}>{msg.text}</div>}
      <form className="auth-card card-sheet" onSubmit={submit}>
        <h3>Account</h3>
        <div className="row">
          <label>
            Username
            <input value={user.username} disabled />
          </label>
          <label>
            Email
            <input value={user.email} disabled />
          </label>
        </div>

        {isStudent ? (
          <>
            <h3>Student details</h3>
            <label>
              Full name
              <input value={form.full_name} onChange={set('full_name')} />
            </label>
            <div className="row">
              <label>
                College
                <input value={form.college} onChange={set('college')} />
              </label>
              <label>
                Branch
                <input value={form.branch} onChange={set('branch')} />
              </label>
            </div>
            <div className="row">
              <label>
                Graduation year
                <input type="number" value={form.graduation_year ?? ''} onChange={set('graduation_year')} />
              </label>
              <label>
                CGPA
                <input type="number" step="0.01" value={form.cgpa ?? ''} onChange={set('cgpa')} />
              </label>
            </div>
            <div className="row">
              <label>
                Phone
                <input value={form.phone} onChange={set('phone')} />
              </label>
              <label>
                Location
                <input value={form.location} onChange={set('location')} />
              </label>
            </div>
            <label>
              Preferred roles (comma separated) — e.g. Python Developer, Django Developer
              <input
                value={rolesText}
                onChange={(e) =>
                  setForm({
                    ...form,
                    preferred_roles: e.target.value
                      .split(',')
                      .map((s) => s.trim())
                      .filter(Boolean),
                  })
                }
              />
            </label>
          </>
        ) : (
          <>
            <h3>Company details</h3>
            <label>
              Company name
              <input value={form.company_name || ''} onChange={set('company_name')} />
            </label>
            <label>
              Website
              <input value={form.website || ''} onChange={set('website')} />
            </label>
            <label>
              Location
              <input value={form.location} onChange={set('location')} />
            </label>
            <label>
              Description
              <textarea rows={3} value={form.description || ''} onChange={set('description')} />
            </label>
          </>
        )}

        <button className="btn btn-primary" disabled={busy}>
          {busy ? 'Saving…' : 'Save profile'}
        </button>
      </form>
    </div>
  )
}