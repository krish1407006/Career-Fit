import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiError } from '../../api/client'
import { fetchAdminUsers } from '../../api/auth'
import { fetchAdminDashboard } from '../../api/dashboard'
import Stat from '../../components/Stat'

/** Where to go to check each area of the product. */
const INSPECTION_LINKS = [
  { to: '/admin/accounts', label: 'Accounts', hint: 'Every user, and what they own' },
  { to: '/admin/quizzes', label: 'Quizzes', hint: 'Create and edit quizzes and questions' },
  { to: '/admin/resumes', label: 'Resumes', hint: 'Every upload and its AI analysis' },
  { to: '/admin/applications', label: 'Applications', hint: 'Who applied where, and the status' },
  { to: '/admin/attempts', label: 'Quiz attempts', hint: 'Every attempt and its review' },
  { to: '/admin/interviews', label: 'Interviews', hint: 'Every mock interview transcript' },
]

/** The student flow, which an admin can run on their own account. */
const STUDENT_LINKS = [
  { to: '/student', label: 'Student dashboard', hint: 'Same stats a student sees' },
  { to: '/student/profile', label: 'Profile & resume', hint: 'Upload a PDF and run AI analysis' },
  { to: '/student/jobs', label: 'Jobs & matching', hint: 'Match scores, skill gaps, apply' },
  { to: '/student/applications', label: 'My applications', hint: 'Track what you applied to' },
  { to: '/student/quizzes', label: 'Quizzes', hint: 'Attempt a quiz end to end' },
  { to: '/student/interview', label: 'Mock interview', hint: 'Run a voice or text interview' },
]

const LinkCard = ({ to, label, hint }) => (
  <Link className="card stat-card" to={to} style={{ textDecoration: 'none' }}>
    <div className="stat-label">{label}</div>
    <div className="stat-sub">{hint}</div>
    <div className="muted small">Open →</div>
  </Link>
)

export default function AdminArea() {
  const [data, setData] = useState(null)
  const [users, setUsers] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([fetchAdminDashboard(), fetchAdminUsers()])
      .then(([dash, rows]) => {
        setData(dash)
        setUsers(rows)
      })
      .catch((e) => setError(apiError(e, 'Could not load admin area')))
  }, [])

  return (
    <div className="page dashboard">
      <h1>Admin Area</h1>
      {error && <div className="alert error">{error}</div>}
      {data && (
        <>
          <div className="cards">
            <Stat label="Students" value={data.users.student} />
            <Stat label="Recruiters" value={data.users.recruiter} />
            <Stat label="Admins" value={data.users.admin} />
            <Stat label="Total users" value={data.users.total} />
            <Stat label="Jobs" value={data.jobs.total} sub={`${data.jobs.active} active · ${data.jobs.applications} applications`} />
            <Stat label="Quizzes" value={data.quizzes.quizzes} sub={`${data.quizzes.attempts} attempts`} />
            <Stat label="Interviews" value={data.interviews.sessions} sub={`${data.interviews.completed} completed`} />
          </div>

          <h2 className="section-title">Check what each student did</h2>
          <p className="muted">
            Read-only screens over every student's records, so you can confirm the
            platform is storing what it should.
          </p>
          <div className="cards">
            {INSPECTION_LINKS.map((link) => (
              <LinkCard key={link.to} {...link} />
            ))}
          </div>

          <h2 className="section-title">Try the student experience yourself</h2>
          <div className="alert warn">
            You have full student access on your own admin account. Anything you do
            here is written against <strong>your</strong> account, so the same write
            paths a student uses get exercised. It will show up in the read-only
            screens above as your own records.
          </div>
          <div className="cards">
            {STUDENT_LINKS.map((link) => (
              <LinkCard key={link.to} {...link} />
            ))}
          </div>

          <h2 className="section-title">Users</h2>
          <div className="app-table-wrap">
            <table className="app-table">
              <thead>
                <tr><th>Username</th><th>Email</th><th>Role</th><th>Status</th></tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id}>
                    <td>{u.username}</td>
                    <td>{u.email || '—'}</td>
                    <td><span className="badge">{u.role}</span></td>
                    <td>{u.is_active ? <span className="ok">active</span> : <span className="bad">disabled</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}
