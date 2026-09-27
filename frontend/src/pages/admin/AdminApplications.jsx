import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchAdminApplications } from '../../api/admin'
import StatusBadge from '../../components/jobs/StatusBadge'

const STATUSES = ['applied', 'shortlisted', 'interview', 'selected', 'rejected']

const formatDate = (value) => {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString()
}

/**
 * Read-only view of every application on the platform.
 *
 * Answers "did each student's application get recorded against the right job
 * with the right status and match score?". Changing a status stays on the
 * recruiter's screen, so there is one code path for that write.
 */
export default function AdminApplications() {
  const [applications, setApplications] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('all')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setApplications(await fetchAdminApplications())
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const term = search.trim().toLowerCase()
  const visible = applications.filter((application) => {
    if (status !== 'all' && application.status !== status) return false
    if (!term) return true
    return [
      application.student_username,
      application.student_email,
      application.student_name,
      application.job_title,
      application.company,
    ]
      .filter(Boolean)
      .some((value) => value.toLowerCase().includes(term))
  })

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Applications</h1>
          <p className="muted">
            Every application submitted by every student, with the match score that
            was stored at the time. Read only.
          </p>
        </div>
        <button className="btn btn-ghost" onClick={load} disabled={loading}>
          {loading ? 'Loading…' : 'Refresh'}
        </button>
      </div>

      {error && <div className="alert error">{error}</div>}

      <div className="cards">
        <div className="card stat-card">
          <div className="stat-value">{applications.length}</div>
          <div className="stat-label">Applications</div>
        </div>
        {STATUSES.map((value) => (
          <div className="card stat-card" key={value}>
            <div className="stat-value">
              {applications.filter((a) => a.status === value).length}
            </div>
            <div className="stat-label">{value}</div>
          </div>
        ))}
        <div className="card stat-card">
          <div className="stat-value">
            {applications.filter((a) => a.resume_name).length}
          </div>
          <div className="stat-label">With resume</div>
          <div className="stat-sub">Applied after uploading one</div>
        </div>
      </div>

      <div className="filter-bar">
        <input
          className="search"
          placeholder="Search student, job or company"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="all">All statuses</option>
          {STATUSES.map((value) => (
            <option key={value} value={value}>{value}</option>
          ))}
        </select>
      </div>

      <div className="app-table-wrap">
        <table className="app-table">
          <thead>
            <tr>
              <th>Student</th>
              <th>Role</th>
              <th>Job</th>
              <th>Company</th>
              <th>Match</th>
              <th>Status</th>
              <th>Remarks</th>
              <th>Applied</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr><td colSpan={8} className="muted">Loading applications…</td></tr>
            )}
            {!loading && visible.length === 0 && (
              <tr><td colSpan={8} className="muted">No applications match your search.</td></tr>
            )}
            {visible.map((application) => (
              <tr key={application.id}>
                <td>
                  <strong>{application.student_username}</strong>
                  <div className="muted small">
                    {application.student_name || '—'}
                    {application.student_role !== 'student' && ` · ${application.student_role}`}
                  </div>
                </td>
                <td className="muted small">{application.student_email || '—'}</td>
                <td>{application.job_title}</td>
                <td>
                  {application.company}
                  <div className="muted small">by {application.recruiter_username}</div>
                </td>
                <td>{application.match_score}%</td>
                <td><StatusBadge status={application.status} /></td>
                <td className="muted small">{application.remarks || '—'}</td>
                <td className="muted small">{formatDate(application.applied_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="back-link">
        <Link to="/admin">Back to admin dashboard</Link>
      </p>
    </div>
  )
}
