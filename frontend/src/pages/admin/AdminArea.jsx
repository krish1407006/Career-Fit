import { useEffect, useState } from 'react'
import { apiError } from '../../api/client'
import { fetchAdminUsers } from '../../api/auth'
import { fetchAdminDashboard } from '../../api/dashboard'
import Stat from '../../components/Stat'

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