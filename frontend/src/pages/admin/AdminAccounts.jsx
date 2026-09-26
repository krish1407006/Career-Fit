import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { bulkDeleteAdminUsers, fetchAdminUsers, resetAdminUserPassword, setAdminUserActive } from '../../api/accounts'

const ROLE_LABEL = { admin: 'Admin', recruiter: 'Recruiter', student: 'Student' }

const formatDate = (value) => {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleString(undefined, {
    year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

const totalRecords = (counts) =>
  Object.values(counts || {}).reduce((sum, value) => sum + (value || 0), 0)

/**
 * Admin account management: every account on the platform on one screen, with
 * search, role filters, and the ability to select and remove accounts.
 */
export default function AdminAccounts() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [accounts, setAccounts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [selected, setSelected] = useState([])
  const [search, setSearch] = useState('')
  const [roleFilter, setRoleFilter] = useState('all')
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setAccounts(await fetchAdminUsers())
      setSelected([])
    } catch (e) {
      setError(e?.message || 'Could not load accounts')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  // Do not let a non-admin sit on this page even if they navigate straight here.
  useEffect(() => {
    if (user && !user.is_admin_role) navigate('/admin', { replace: true })
  }, [user, navigate])

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase()
    return accounts.filter((account) => {
      if (roleFilter !== 'all' && account.role !== roleFilter) return false
      if (!term) return true
      return [account.username, account.email, account.full_name, account.company_name]
        .filter(Boolean)
        .some((value) => value.toLowerCase().includes(term))
    })
  }, [accounts, search, roleFilter])

  const visibleIds = filtered.map((account) => account.id)
  const allVisibleSelected = visibleIds.length > 0 && visibleIds.every((id) => selected.includes(id))
  const selectedAccounts = accounts.filter((account) => selected.includes(account.id))
  const selectedAdmins = selectedAccounts.filter(
    (account) => account.role === 'admin' && account.is_active,
  )
  const activeAdminTotal = accounts.filter(
    (account) => account.role === 'admin' && account.is_active,
  ).length
  const wouldRemoveLastAdmin = selectedAdmins.length >= activeAdminTotal && activeAdminTotal > 0

  const toggleAll = () => {
    setSelected(allVisibleSelected ? [] : visibleIds)
  }

  const toggleOne = (id) => {
    setSelected((current) =>
      current.includes(id) ? current.filter((value) => value !== id) : [...current, id],
    )
  }

  const onDelete = async () => {
    if (selected.length === 0) return
    const names = selectedAccounts.map((account) => account.username).join(', ')
    if (!window.confirm(
      `Delete ${selected.length} account(s) permanently?\n\n${names}\n\n`
      + 'Their resumes, applications, interviews and quiz attempts are deleted too. '
      + 'This cannot be undone.',
    )) return

    setBusy(true)
    setError('')
    setNotice('')
    try {
      const result = await bulkDeleteAdminUsers(selected)
      setNotice(`Deleted ${result.deleted} account(s).`)
      await load()
    } catch (e) {
      setError(e?.message || 'Could not delete the selected accounts')
    } finally {
      setBusy(false)
    }
  }

  const onToggleActive = async (account) => {
    setBusy(true)
    setError('')
    setNotice('')
    try {
      await setAdminUserActive(account.id, !account.is_active)
      setNotice(
        `${account.username} is now ${account.is_active ? 'disabled' : 'enabled'}.`,
      )
      await load()
    } catch (e) {
      setError(e?.message || 'Could not update that account')
    } finally {
      setBusy(false)
    }
  }

  const onResetPassword = (account) => {
    const next = window.prompt(
      `New password for "${account.username}"\n\nAt least 8 characters.`,
      '',
    )
    if (next === null) return
    if (next.length < 8) {
      setError('Password must be at least 8 characters.')
      return
    }
    setBusy(true)
    setError('')
    setNotice('')
    resetAdminUserPassword(account.id, next)
      .then((result) => setNotice(result?.detail || `Password updated for ${account.username}.`))
      .catch((e) => setError(e?.message || 'Could not reset that password'))
      .finally(() => setBusy(false))
  }

  const onSignOut = async () => {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Accounts</h1>
          <p className="muted">
            Every account on the platform. Select the ones you want and remove them.
          </p>
        </div>
        <button className="btn btn-ghost" onClick={onSignOut}>Sign out</button>
      </div>

      {error && <div className="alert error">{error}</div>}
      {notice && <div className="alert ok">{notice}</div>}

      <div className="card card-sheet admin-accounts">
        <div className="admin-accounts-controls">
          <input
            aria-label="Search accounts"
            placeholder="Search username, email, name or company"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <select
            aria-label="Filter by role"
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
          >
            <option value="all">All roles</option>
            <option value="student">Students</option>
            <option value="recruiter">Recruiters</option>
            <option value="admin">Admins</option>
          </select>
          <button className="btn btn-ghost" onClick={load} disabled={loading}>
            {loading ? 'Loading…' : 'Refresh'}
          </button>
        </div>

        <div className="admin-accounts-actions">
          <span className="muted small">
            {selected.length
              ? `${selected.length} selected`
              : `${filtered.length} of ${accounts.length} account(s)`}
          </span>
          <button
            className="btn btn-danger"
            onClick={onDelete}
            disabled={busy || selected.length === 0 || wouldRemoveLastAdmin}
          >
            {busy ? 'Working…' : `Delete selected${selected.length ? ` (${selected.length})` : ''}`}
          </button>
        </div>

        {wouldRemoveLastAdmin && (
          <div className="alert warn">
            That selection includes every active admin. Keep at least one so you can still
            manage accounts.
          </div>
        )}

        <div className="app-table-wrap">
          <table className="app-table">
            <thead>
              <tr>
                <th scope="col">
                  <input
                    type="checkbox"
                    aria-label="Select all shown accounts"
                    checked={allVisibleSelected}
                    onChange={toggleAll}
                  />
                </th>
                <th scope="col">Username</th>
                <th scope="col">Name</th>
                <th scope="col">Email</th>
                <th scope="col">Phone</th>
                <th scope="col">Role</th>
                <th scope="col">Status</th>
                <th scope="col">Records</th>
                <th scope="col">Joined</th>
                <th scope="col">Last login</th>
                <th scope="col">Action</th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr><td colSpan={11} className="muted">Loading accounts…</td></tr>
              )}
              {!loading && filtered.length === 0 && (
                <tr><td colSpan={11} className="muted">No accounts match your search.</td></tr>
              )}
              {filtered.map((account) => (
                <tr key={account.id} className={selected.includes(account.id) ? 'is-selected' : ''}>
                  <td>
                    <input
                      type="checkbox"
                      aria-label={`Select ${account.username}`}
                      checked={selected.includes(account.id)}
                      onChange={() => toggleOne(account.id)}
                    />
                  </td>
                  <td>
                    <strong>{account.username}</strong>
                    {account.username === user?.username && (
                      <span className="muted small"> (you)</span>
                    )}
                    {account.company_name && (
                      <div className="muted small">{account.company_name}</div>
                    )}
                  </td>
                  <td>{account.full_name || '—'}</td>
                  <td>{account.email || '—'}</td>
                  <td>{account.phone || '—'}</td>
                  <td>
                    <span className={`score-tag role-${account.role}`}>
                      {ROLE_LABEL[account.role] || account.role}
                    </span>
                  </td>
                  <td>
                    <span className={`score-tag ${account.is_active ? 'ok' : 'bad'}`}>
                      {account.is_active ? 'Active' : 'Disabled'}
                    </span>
                  </td>
                  <td className="muted small">
                    {totalRecords(account.related_counts)}
                    <div>
                      {Object.entries(account.related_counts || {})
                        .filter(([, value]) => value > 0)
                        .map(([key, value]) => `${key}:${value}`)
                        .join(' ') || '—'}
                    </div>
                  </td>
                  <td className="muted small">{formatDate(account.date_joined)}</td>
                  <td className="muted small">{formatDate(account.last_login)}</td>
                  <td>
                    {account.username === user?.username ? (
                      <span className="muted small">Current account</span>
                    ) : (
                      <div className="voice-controls">
                        <button
                          className="btn btn-ghost"
                          onClick={() => onResetPassword(account)}
                          disabled={busy}
                        >
                          Set password
                        </button>
                        <button
                          className="btn btn-ghost"
                          onClick={() => onToggleActive(account)}
                          disabled={busy}
                        >
                          {account.is_active ? 'Disable' : 'Enable'}
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
