import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import {
  addSuperEmail,
  fetchMyEmail,
  fetchSuperEmails,
  removeSuperEmail,
  setSuperEmailActive,
  updateMyEmail,
} from '../../api/superEmails'

const EMPTY_FORM = { email: '', note: '' }

export default function AdminSuperEmails() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [rows, setRows] = useState([])
  const [myEmail, setMyEmail] = useState('')
  const [form, setForm] = useState(EMPTY_FORM)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const load = useCallback(async () => {
    setError('')
    try {
      const [list, mine] = await Promise.all([fetchSuperEmails(), fetchMyEmail()])
      setRows(list)
      setMyEmail(mine)
    } catch (e) {
      setError(e?.message || 'Could not load super emails')
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  if (user && user.role !== 'admin') {
    return (
      <section className="empty-state">
        <h2>Admins only</h2>
        <p>You need admin access to manage super emails.</p>
        <Link className="btn btn-primary" to="/">Back to dashboard</Link>
      </section>
    )
  }

  const onAdd = async (event) => {
    event.preventDefault()
    const email = form.email.trim()
    if (!email) {
      setError('Enter an email address.')
      return
    }
    setBusy(true)
    setError('')
    setNotice('')
    try {
      await addSuperEmail(email, form.note.trim())
      setForm(EMPTY_FORM)
      setNotice(`${email} can now use admin features after they sign in.`)
      await load()
    } catch (e) {
      setError(e?.message || 'Could not add that email')
    } finally {
      setBusy(false)
    }
  }

  const onToggle = async (row) => {
    setBusy(true)
    setError('')
    setNotice('')
    try {
      await setSuperEmailActive(row.id, !row.is_active)
      await load()
    } catch (e) {
      setError(e?.message || 'Could not update that email')
    } finally {
      setBusy(false)
    }
  }

  const onRemove = async (row) => {
    if (
      !window.confirm(
        `Remove "${row.email}"?\n\nThey lose admin access, and any account that signed ` +
          'in with this address is demoted back to a normal user.',
      )
    ) {
      return
    }
    setBusy(true)
    setError('')
    setNotice('')
    try {
      await removeSuperEmail(row.id)
      setNotice(`${row.email} no longer has admin access.`)
      await load()
    } catch (e) {
      setError(e?.message || 'Could not remove that email')
    } finally {
      setBusy(false)
    }
  }

  const onSaveMyEmail = async (event) => {
    event.preventDefault()
    const email = myEmail.trim()
    if (!email) {
      setError('Your email cannot be empty.')
      return
    }
    setBusy(true)
    setError('')
    setNotice('')
    try {
      const result = await updateMyEmail(email)
      setNotice(result?.detail || 'Email updated.')
      await load()
    } catch (e) {
      setError(e?.message || 'Could not update your email')
    } finally {
      setBusy(false)
    }
  }

  const onSignOut = async () => {
    await logout()
    navigate('/login')
  }

  const activeCount = rows.filter((row) => row.is_active).length

  return (
    <div className="page-stack">
      <header className="page-head">
        <div>
          <h1>Super emails</h1>
          <p className="muted">
            An address on this list is given full admin access the moment that person
            signs in. It is a second pair of hands, not a shared password.
          </p>
        </div>
        <div className="voice-controls">
          <Link className="btn btn-ghost" to="/admin/accounts">All accounts</Link>
          <button className="btn btn-ghost" onClick={onSignOut}>Sign out</button>
        </div>
      </header>

      <div className="banner banner-warning">
        <strong>These addresses have full admin power.</strong> They can read and delete
        every account, resume and interview. Only add addresses you control, and remove
        them when the access is no longer needed.
      </div>

      {error ? <div className="banner banner-error">{error}</div> : null}
      {notice ? <div className="banner banner-success">{notice}</div> : null}

      <section className="card">
        <h2>My admin email</h2>
        <p className="muted small">
          This is the address matched against the list. Change it here, then add the
          new address below if you want it to keep admin access.
        </p>
        <form className="form-grid" onSubmit={onSaveMyEmail}>
          <label>
            Email
            <input
              type="email"
              value={myEmail}
              onChange={(e) => setMyEmail(e.target.value)}
              placeholder="you@example.com"
              disabled={busy}
            />
          </label>
          <div className="form-actions">
            <button className="btn btn-primary" type="submit" disabled={busy}>
              {busy ? 'Saving...' : 'Save my email'}
            </button>
          </div>
        </form>
      </section>

      <section className="card">
        <h2>Grant admin to an email</h2>
        <form className="form-grid" onSubmit={onAdd}>
          <label>
            Email
            <input
              type="email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              placeholder="teammate@example.com"
              disabled={busy}
            />
          </label>
          <label>
            Note (optional)
            <input
              type="text"
              value={form.note}
              onChange={(e) => setForm({ ...form, note: e.target.value })}
              placeholder="Why they need access"
              disabled={busy}
            />
          </label>
          <div className="form-actions">
            <button className="btn btn-primary" type="submit" disabled={busy}>
              {busy ? 'Adding...' : 'Add super email'}
            </button>
          </div>
        </form>
      </section>

      <section className="card">
        <h2>Granted addresses ({activeCount} active)</h2>
        {rows.length === 0 ? (
          <p className="muted">No super emails yet.</p>
        ) : (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Email</th>
                  <th>Note</th>
                  <th>Added by</th>
                  <th>Added</th>
                  <th>Status</th>
                  <th aria-label="Actions" />
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.id}>
                    <td>
                      {row.email}
                      {row.is_own_address ? (
                        <span className="pill pill-info">Your address</span>
                      ) : null}
                    </td>
                    <td className="muted small">{row.note || '—'}</td>
                    <td className="muted small">{row.added_by || '—'}</td>
                    <td className="muted small">
                      {new Date(row.created_at).toLocaleDateString()}
                    </td>
                    <td>
                      {row.is_active ? (
                        <span className="pill pill-success">Active</span>
                      ) : (
                        <span className="pill pill-muted">Revoked</span>
                      )}
                    </td>
                    <td>
                      <div className="voice-controls">
                        <button
                          className="btn btn-ghost"
                          onClick={() => onToggle(row)}
                          disabled={busy}
                        >
                          {row.is_active ? 'Revoke' : 'Restore'}
                        </button>
                        <button
                          className="btn btn-danger-ghost"
                          onClick={() => onRemove(row)}
                          disabled={busy}
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {activeCount <= 1 ? (
          <p className="muted small">
            You have {activeCount} active super email. Add another before removing this
            one, or nobody can manage the list.
          </p>
        ) : null}
      </section>
    </div>
  )
}
