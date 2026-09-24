import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiError } from '../../api/client'
import { fetchMyApplications } from '../../api/jobs'
import StatusBadge from '../../components/jobs/StatusBadge'

export default function MyApplications() {
  const [apps, setApps] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    fetchMyApplications()
      .then(setApps)
      .catch((e) => setError(apiError(e, 'Could not load applications')))
  }, [])

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>My applications</h1>
          <p className="muted">Track every job you have applied to and its status.</p>
        </div>
        <Link className="btn btn-ghost btn-sm" to="/student/jobs">Browse jobs</Link>
      </div>
      {error && <div className="alert error">{error}</div>}
      {apps && !apps.length && (
        <p className="muted">You haven’t applied to any jobs yet.</p>
      )}
      {apps && apps.length > 0 && (
        <div className="app-list">
          {apps.map((a) => (
            <div className="card application" key={a.id}>
              <div className="applicant-head">
                <div>
                  <h3>
                    <Link to={`/student/jobs/${a.job_id}`}>{a.job_title}</Link>
                  </h3>
                  <p className="muted small">
                    {a.company} · {a.location} · {a.job_type?.replace('_', ' ')} · Applied{' '}
                    {new Date(a.applied_at).toLocaleDateString()}
                  </p>
                </div>
                <div className="application-side">
                  <span className="score-tag neutral">Match {a.match_score}%</span>
                  <StatusBadge status={a.status} />
                </div>
              </div>
              {a.cover_note && <p className="summary">Your note: “{a.cover_note}”</p>}
              {a.remarks && (
                <p className="remarks-row">
                  <strong>Recruiter remarks:</strong> {a.remarks}
                </p>
              )}
              <div className="job-actions">
                {a.resume ? (
                  <span className="muted small">Resume attached: {a.resume.original_name}</span>
                ) : (
                  <span className="muted small">
                    No resume attached — upload one from <Link to="/student/profile">Profile</Link>.
                  </span>
                )}
                <Link className="btn btn-ghost btn-sm" to={`/student/jobs/${a.job_id}`}>
                  View job
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}