import { useEffect, useState } from 'react'
import { apiError } from '../../api/client'
import { fetchRecruiterDashboard } from '../../api/dashboard'
import Stat from '../../components/Stat'
import { useAuth } from '../../context/AuthContext'

export default function RecruiterHome() {
  const { user } = useAuth()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    fetchRecruiterDashboard()
      .then(setData)
      .catch((e) => setError(apiError(e, 'Could not load dashboard')))
  }, [])

  const j = data?.jobs

  return (
    <div className="page dashboard">
      <h1>Recruiter Dashboard</h1>
      <p className="muted">Welcome, {user?.username}. Manage your openings and applicants here.</p>
      {error && <div className="alert error">{error}</div>}
      {data && (
        <div className="cards">
          <Stat label="Active jobs" value={j.active} sub={`${j.total} jobs total`} />
          <Stat label="Applications" value={j.applications} sub={`avg match ${j.avg_match}%`} />
          <Stat label="Applied" value={j.by_status.applied} />
          <Stat label="Shortlisted" value={j.by_status.shortlisted} />
          <Stat label="Selected" value={j.by_status.selected} />
          <Stat label="Rejected" value={j.by_status.rejected} />
        </div>
      )}
    </div>
  )
}