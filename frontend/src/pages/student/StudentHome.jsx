import { useEffect, useState } from 'react'
import { apiError } from '../../api/client'
import { fetchStudentDashboard } from '../../api/dashboard'
import Stat from '../../components/Stat'
import { useAuth } from '../../context/AuthContext'

export default function StudentHome() {
  const { profile } = useAuth()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    fetchStudentDashboard()
      .then(setData)
      .catch((e) => setError(apiError(e, 'Could not load dashboard')))
  }, [])

  return (
    <div className="page dashboard">
      <h1>Student Dashboard</h1>
      <p className="muted">
        Welcome, {profile?.full_name || 'student'}. Track your placement preparation here.
      </p>
      {error && <div className="alert error">{error}</div>}
{data && (
        <div className="cards">
          <Stat
            label="Profile completion"
            value={`${data.profile.completion ?? 0}%`}
            sub={`${data.profile.skills_count} skills · ${data.profile.projects_count} projects`}
          />
          <Stat
            label="Resume"
            value={data.profile.resume_uploaded ? 'Uploaded' : 'Not uploaded'}
            sub={data.profile.resume_uploaded ? 'Keep it up to date' : 'Add your resume from the Profile page'}
          />
          <Stat label="Open jobs" value={data.jobs.openings} sub={`${data.jobs.applications} applications sent`} />
          <Stat
            label="Best match"
            value={data.jobs.best_match ? `${data.jobs.best_match}%` : '-'}
            sub={`${data.jobs.shortlisted} shortlisted · ${data.jobs.selected} selected`}
          />
          <Stat label="Quizzes" value={data.quizzes.attempts} sub={data.quizzes.passed ? `${data.quizzes.passed} passed` : 'No attempts yet'} />
          <Stat label="Mock interviews" value={data.interviews.completed} sub={`${data.interviews.total} total sessions`} />
        </div>
      )}
    </div>
  )
}