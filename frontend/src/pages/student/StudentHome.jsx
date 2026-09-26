import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiError } from '../../api/client'
import { fetchStudentDashboard } from '../../api/dashboard'
import Stat from '../../components/Stat'
import StatusBadge from '../../components/jobs/StatusBadge'
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

  const jobs = data?.jobs
  const recent = jobs?.recent || []
  const resume = data?.resume

  return (
    <div className="page dashboard">
      <h1>Student Dashboard</h1>
      <p className="muted">
        Welcome, {profile?.full_name || 'student'}. Track your placement preparation here.
      </p>
      {error && <div className="alert error">{error}</div>}
      {data && (
        <>
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
            <Stat
              label="Available jobs"
              value={jobs.available_jobs}
              sub={<Link to="/student/jobs">Browse jobs →</Link>}
            />
            <Stat
              label="Applications sent"
              value={jobs.total_applications}
              sub={`${jobs.by_status.shortlisted} shortlisted · ${jobs.by_status.interview} interview · ${jobs.by_status.selected} selected`}
            />
            <Stat
              label="Best match"
              value={jobs.best_match != null ? `${jobs.best_match}%` : '-'}
              sub="Highest match score across your applications"
            />
            <Stat label="Quizzes" value={data.quizzes.attempts} sub={data.quizzes.passed ? `${data.quizzes.passed} passed` : 'No attempts yet'} />
            <Stat label="Mock interviews" value={data.interviews.completed} sub={`${data.interviews.total} total sessions`} />
          </div>

          <h2 className="section-title">Resume analysis</h2>
          <div className="cards">
            <Stat
              label="Resume uploaded"
              value={resume?.uploaded ? 'Yes' : 'No'}
              sub={
                resume?.uploaded
                  ? <Link to="/student/profile">Manage resume →</Link>
                  : 'Upload a PDF from your profile page'
              }
            />
            <Stat
              label="Analysis completed"
              value={resume?.analysis_completed ? 'Yes' : 'No'}
              sub={
                resume?.analysis_completed
                  ? `Analysed with ${resume.source === 'ai' ? 'AI' : 'the rule-based checker'}`
                  : 'Run Analyze resume from your profile page'
              }
            />
            <Stat
              label="Detected skills"
              value={resume?.detected_skills_count ?? 0}
              sub="Skills found in your resume by AI"
            />
            <Stat
              label="Skill gaps"
              value={resume?.skill_gaps_count ?? 0}
              sub={resume?.improvements_count ? `${resume.improvements_count} improvement tips` : 'Areas to work on'}
            />
          </div>

          <h2 className="section-title">Application status</h2>
          <div className="cards">
            <Stat label="Applied" value={jobs.by_status.applied} />
            <Stat label="Shortlisted" value={jobs.by_status.shortlisted} />
            <Stat label="Interview" value={jobs.by_status.interview} />
            <Stat label="Selected" value={jobs.by_status.selected} />
            <Stat label="Rejected" value={jobs.by_status.rejected} />
          </div>

          <h2 className="section-title">Recent applications</h2>
          {recent.length ? (
            <div className="app-table-wrap">
              <table className="app-table">
                <thead>
                  <tr><th>Job</th><th>Company</th><th>Location</th><th>Match</th><th>Status</th><th>Applied</th></tr>
                </thead>
                <tbody>
                  {recent.map((a) => (
                    <tr key={a.id}>
                      <td><Link to={`/student/jobs/${a.job_id}`}>{a.job__title}</Link></td>
                      <td>{a.job__company_name}</td>
                      <td>{a.job__location}</td>
                      <td>{a.match_score}%</td>
                      <td><StatusBadge status={a.status} /></td>
                      <td>{new Date(a.applied_at).toLocaleDateString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="muted">
              No applications yet. Explore{' '}
              <Link to="/student/jobs">recommended jobs</Link> to get started.
            </p>
          )}
        </>
      )}
    </div>
  )
}