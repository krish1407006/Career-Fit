import { useEffect, useState } from 'react'
import { apiError } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { fetchDashboard } from '../api/dashboard'

function Stat({ label, value, sub }) {
  return (
    <div className="card stat-card">
      <div className="stat-value">{value === null || value === undefined ? '—' : value}</div>
      <div className="stat-label">{label}</div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  )
}

function StudentDash({ data, profile }) {
  const r = data.resume
  const j = data.jobs
  const q = data.quizzes
  const i = data.interviews
  const passPct = q.attempts ? Math.round((q.passed / q.attempts) * 100) : null
  return (
    <>
      <h2 className="section-title">Career snapshot</h2>
      <div className="cards">
        <Stat
          label="Resume strength"
          value={r.analyzed ? `${r.score}%` : r.status}
          sub={r.skills_count ? `${r.skills_count} skills extracted` : 'Upload your resume'}
        />
        <Stat label="Open jobs" value={j.openings} sub={`${j.applications} applications sent`} />
        <Stat
          label="Best match"
          value={j.best_match ? `${j.best_match}%` : '—'}
          sub={`${j.shortlisted} shortlisted · ${j.selected} selected`}
        />
        <Stat
          label="Quizzes"
          value={q.attempts}
          sub={passPct !== null ? `${q.passed}/${q.attempts} passed (${passPct}%) · avg ${q.avg_score}%` : 'No attempts yet'}
        />
        <Stat
          label="Mock interviews"
          value={i.completed}
          sub={`${i.total} total sessions`}
        />
      </div>
      <p className="muted">
        {profile?.full_name || 'You'} · {profile?.college || 'Add your college in Profile'}
        {profile?.preferred_roles?.length ? ` · Prefers ${profile.preferred_roles.join(', ')}` : ''}
      </p>
    </>
  )
}

function RecruiterDash({ data }) {
  const j = data.jobs
  const s = j.by_status
  return (
    <>
      <h2 className="section-title">Recruiting overview</h2>
      <div className="cards">
        <Stat label="Active jobs" value={j.active} sub={`${j.total} jobs total`} />
        <Stat label="Applications" value={j.applications} sub={`avg match ${j.avg_match}%`} />
        <Stat label="Applied" value={s.applied} />
        <Stat label="Shortlisted" value={s.shortlisted} />
        <Stat label="Selected" value={s.selected} />
        <Stat label="Rejected" value={s.rejected} />
      </div>
    </>
  )
}

function AdminDash({ data }) {
  const u = data.users
  const j = data.jobs
  const q = data.quizzes
  const i = data.interviews
  return (
    <>
      <h2 className="section-title">Platform overview</h2>
      <div className="cards">
        <Stat label="Students" value={u.student} />
        <Stat label="Recruiters" value={u.recruiter} />
        <Stat label="Total users" value={u.total} />
        <Stat label="Jobs" value={j.total} sub={`${j.active} active · ${j.applications} applications`} />
        <Stat label="Quizzes" value={q.quizzes} sub={`${q.attempts} attempts · avg ${q.avg_score}%`} />
        <Stat label="Interviews" value={i.sessions} sub={`${i.completed} completed`} />
      </div>
      {data.colleges?.length > 0 && (
        <>
          <h2 className="section-title">Top colleges</h2>
          <div className="app-table-wrap">
            <table className="app-table">
              <thead><tr><th>College</th><th>Students</th></tr></thead>
              <tbody>
                {data.colleges.map((c) => (
                  <tr key={c.college}>
                    <td>{c.college}</td>
                    <td>{c.n}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </>
  )
}

export default function Dashboard() {
  const { user, profile } = useAuth()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    fetchDashboard()
      .then(setData)
      .catch((e) => setError(apiError(e, 'Could not load dashboard')))
  }, [])

  const role = user?.is_admin_role ? 'admin' : user?.role

  return (
    <div className="page dashboard">
      <h1>Welcome, {profile?.full_name || user?.username || 'there'}</h1>
      {error && <div className="alert error">{error}</div>}
      {data && role === 'admin' && <AdminDash data={data} />}
      {data && role === 'student' && <StudentDash data={data} profile={profile} />}
      {data && role === 'recruiter' && <RecruiterDash data={data} />}
    </div>
  )
}