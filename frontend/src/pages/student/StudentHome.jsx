import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiError } from '../../api/client'
import { fetchStudentDashboard } from '../../api/dashboard'
import Stat from '../../components/Stat'
import StatusBadge, { STATUS_LABELS } from '../../components/jobs/StatusBadge'
import PerformanceTrendChart from '../../components/dashboard/PerformanceTrendChart'
import { useAuth } from '../../context/AuthContext'
import { plural } from '../../lib/format'

const STATUS_ORDER = ['applied', 'shortlisted', 'interview', 'selected', 'rejected']

function formatScore(value) {
  return value === null || value === undefined ? '—' : `${value}%`
}

function ResumeSection({ resume }) {
  const analyzed = resume?.analysis_completed
  return (
    <section>
      <h2 className="section-title">Resume analysis</h2>
      <div className="card">
        {!resume.uploaded ? (
          <>
            <p className="muted">You have not uploaded a resume yet.</p>
            <Link to="/student/profile" className="btn btn-primary btn-sm">Upload resume</Link>
          </>
        ) : !analyzed ? (
          <>
            <p className="muted">Your resume is uploaded but has not been analyzed yet. Analyze it to surface skill insights.</p>
            <Link to="/student/profile" className="btn btn-primary btn-sm">Analyze resume</Link>
          </>
        ) : (
          <>
            <div className="section-head">
              <h3>{resume.original_name || 'Your resume'}</h3>
              <span className={`badge ${resume.analysis_status === 'failed' ? 'bad' : 'ok'}`}>
                {resume.analysis_status === 'failed' ? 'Analysis failed' : 'Analyzed'}
                {resume.source === 'ai' ? ' with AI' : ''}
              </span>
            </div>
            {typeof resume.score === 'number' && resume.score > 0 && (
              <div className="scorebar">
                <span className="muted small">Resume quality score</span>
                <div className="bar">
                  <div className="bar-fill" style={{ width: `${Math.min(100, resume.score)}%` }} />
                </div>
              </div>
            )}

            {resume.detected_skills_count > 0 && (
              <div className="analysis-block">
                <h4>Detected skills ({plural(resume.detected_skills_count, 'skill')})</h4>
                <div className="chips">
                  {resume.detected_skills.map((skill) => (
                    <span key={skill} className="chip ai-chip">{skill}</span>
                  ))}
                </div>
              </div>
            )}

            {resume.skill_gaps_count > 0 && (
              <div className="analysis-block">
                <h4>Skill gaps ({plural(resume.skill_gaps_count, 'skill gap')})</h4>
                <div className="chips">
                  {resume.skill_gaps.map((skill) => (
                    <span key={skill} className="chip miss-chip">{skill}</span>
                  ))}
                </div>
              </div>
            )}

            {resume.strengths_count > 0 && (
              <div className="analysis-block">
                <h4>Strengths</h4>
                <ul className="analysis-list ok">
                  {resume.strengths.map((item) => <li key={item}>{item}</li>)}
                </ul>
              </div>
            )}

            {resume.improvements_count > 0 && (
              <div className="analysis-block">
                <h4>Improvement suggestions</h4>
                <ul className="analysis-list">
                  {resume.improvements.map((item) => <li key={item}>{item}</li>)}
                </ul>
              </div>
            )}

            {resume.recommended_roles_count > 0 && (
              <div className="analysis-block">
                <h4>Recommended roles</h4>
                <div className="chips">
                  {resume.recommended_roles.map((role) => <span key={role} className="chip">{role}</span>)}
                </div>
              </div>
            )}

            <p className="muted small">Manage your resume and re-run analysis from the profile page.</p>
          </>
        )}
      </div>
    </section>
  )
}

function SkillsSection({ skills }) {
  return (
    <section>
      <h2 className="section-title">Skills &amp; skill gaps</h2>
      <div className="cards">
        <Stat label="Skills on profile" value={skills.current_count} sub="Used to rank jobs you apply to" />
        <Stat label="Detected in resume" value={skills.detected_count} sub="Found during analysis" />
        <Stat label="Analysis gaps" value={skills.gaps_count} sub="Flagged by your resume analysis" />
        <Stat label="Job skill gaps" value={skills.job_gap_count} sub="Required by jobs you applied to" />
      </div>

      <div className="card">
        <h3>Your skills</h3>
        {skills.current.length ? (
          <div className="chips">{skills.current.map((skill) => <span key={skill} className="chip">{skill}</span>)}</div>
        ) : (
          <p className="muted">No skills on your profile yet. Add them to improve job matching.</p>
        )}

        {skills.detected.length > 0 && (
          <div className="analysis-block">
            <h4>Detected in resume</h4>
            <div className="chips">{skills.detected.map((skill) => <span key={skill} className="chip ai-chip">{skill}</span>)}</div>
          </div>
        )}

        {skills.job_gaps.length > 0 && (
          <div className="analysis-block">
            <h4>Skills your applications demand</h4>
            <div className="chips">
              {skills.job_gaps.map((gap) => (
                <span key={gap.skill} className="chip miss-chip">
                  {gap.skill}
                  <span className="gap-count"> · {gap.required_by} {plural(gap.required_by, 'application')}</span>
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </section>
  )
}

function QuizSection({ quizzes }) {
  return (
    <section>
      <h2 className="section-title">Quiz performance</h2>
      <div className="cards">
        <Stat label="Attempts" value={quizzes.attempts_completed} sub={quizzes.in_progress ? `${quizzes.in_progress} in progress` : 'Submitted attempts'} />
        <Stat label="Average score" value={formatScore(quizzes.average_score)} sub={quizzes.attempts_completed ? `across ${plural(quizzes.attempts_completed, 'attempt')}` : 'No attempts yet'} />
        <Stat label="Highest score" value={quizzes.highest_score === null || quizzes.highest_score === undefined ? '—' : `${quizzes.highest_score}%`} sub="Best single attempt" />
        <Stat label="Passed" value={quizzes.passed} sub="Scored 60% or above" />
      </div>

      {quizzes.by_category.length > 0 && (
        <div className="card">
          <h3>By category</h3>
          {quizzes.by_category.map((row) => (
            <div key={row.category} className="category-row">
              <span className="cat-label">{row.label}</span>
              <div className="scorebar">
                <div className="bar">
                  <div className="bar-fill" style={{ width: `${Math.min(100, row.average ?? 0)}%` }} />
                </div>
              </div>
              <span className="cat-value">{formatScore(row.average)}</span>
            </div>
          ))}
        </div>
      )}

      {quizzes.recent_attempts.length > 0 && (
        <div className="card">
          <div className="section-head">
            <h3>Recent attempts</h3>
            <Link to="/student/quizzes/history" className="btn btn-ghost btn-sm">View all</Link>
          </div>
          <div className="recent-list">
            {quizzes.recent_attempts.map((attempt) => (
              <div key={attempt.id} className="recent-row">
                <Link to={`/student/quizzes/${attempt.quiz_id}/result?attempt=${attempt.id}`}>{attempt.title}</Link>
                <span className={`score-tag ${attempt.score_percent >= 60 ? 'ok' : 'bad'}`}>{attempt.score_percent}%</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {quizzes.attempts_completed === 0 && (
        <p className="muted">No quiz attempts yet. <Link to="/student/quizzes">Browse quizzes →</Link></p>
      )}
    </section>
  )
}

function InterviewSection({ interviews }) {
  const latest = interviews.latest
  const active = interviews.active_session
  return (
    <section>
      <h2 className="section-title">Mock interviews</h2>
      <div className="cards">
        <Stat label="Completed" value={interviews.completed} sub={`${interviews.total} total sessions`} />
        <Stat label="Average score" value={interviews.average_score !== null ? `${interviews.average_score} / 10` : '—'} sub={interviews.scored_interviews ? `across ${plural(interviews.scored_interviews, 'scored session')}` : 'No scored sessions'} />
        <Stat label="In progress" value={interviews.in_progress} sub="Sessions not yet finished" />
      </div>

      {active && (
        <div className="card">
          <p className="muted small">You have an interrupted session for {active.position}.</p>
          <Link to="/student/interview" className="btn btn-primary btn-sm">Resume interview</Link>
        </div>
      )}

      {latest ? (
        <div className="card">
          <div className="section-head">
            <h3>Latest interview — {latest.position}</h3>
            <span className={`score-tag ${latest.score == null ? 'neutral' : latest.score >= 7 ? 'ok' : latest.score >= 5 ? 'warn' : 'bad'}`}>
              {latest.score == null ? 'Not scored' : `${latest.score} / 10`}
            </span>
          </div>
          {latest.summary && <p className="summary">{latest.summary}</p>}
          {latest.areas_to_improve.length > 0 && (
            <div className="analysis-block">
              <h4>Areas to improve</h4>
              <div className="chips">
                {latest.areas_to_improve.map((area) => <span key={area} className="chip miss-chip">{area}</span>)}
              </div>
            </div>
          )}
          {latest.topics_to_prepare.length > 0 && (
            <div className="analysis-block">
              <h4>Topics to prepare</h4>
              <div className="chips">
                {latest.topics_to_prepare.map((topic) => <span key={topic} className="chip">{topic}</span>)}
              </div>
            </div>
          )}
          <p className="muted small">
            {new Date(latest.completed_at).toLocaleDateString()} · {latest.mode}
          </p>
        </div>
      ) : (
        <p className="muted">
          No mock interviews yet. <Link to="/student/interview">Start a practice interview →</Link>
        </p>
      )}
    </section>
  )
}

function ApplicationsSection({ applications }) {
  const recent = applications.recent
  return (
    <section>
      <h2 className="section-title">Applications</h2>
      <div className="cards">
        <Stat label="Applied" value={applications.total} sub="Jobs you applied to" />
        <Stat label="Best match" value={applications.best_match !== null ? `${applications.best_match}%` : '—'} sub="Highest match score on your applications" />
      </div>

      {recent.length ? (
        <>
          <div className="chips apps-status">
            {STATUS_ORDER.map((status) => (
              <span key={status} className={`badge ${status}`}>{STATUS_LABELS[status]} · {applications.by_status[status] ?? 0}</span>
            ))}
          </div>
          <div className="app-table-wrap">
            <table className="app-table">
              <thead>
                <tr><th>Job</th><th>Company</th><th>Location</th><th>Match</th><th>Status</th><th>Applied</th></tr>
              </thead>
              <tbody>
                {recent.map((a) => (
                  <tr key={a.id}>
                    <td><Link to={`/student/jobs/${a.job_id}`}>{a.title}</Link></td>
                    <td>{a.company}</td>
                    <td>{a.location}</td>
                    <td>{a.match_score}%</td>
                    <td><StatusBadge status={a.status} /></td>
                    <td>{new Date(a.applied_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : (
        <p className="muted">
          No applications yet. Explore <Link to="/student/jobs">recommended jobs</Link> to get started.
        </p>
      )}
    </section>
  )
}

function TrendSection({ points }) {
  return (
    <section>
      <h2 className="section-title">Performance trend</h2>
      <div className="card">
        {points.length ? (
          <PerformanceTrendChart points={points} />
        ) : (
          <p className="muted">Complete more quizzes and interviews to see your performance trend.</p>
        )}
      </div>
    </section>
  )
}

function InsightsSection({ insights }) {
  return (
    <section>
      <h2 className="section-title">Preparation insights</h2>
      {insights.length ? (
        <div className="insight-list">
          {insights.map((insight) => (
            <div key={insight.id} className={`card insight-card tone-${insight.tone}`}>
              <h4>{insight.title}</h4>
              <p>{insight.detail}</p>
              {insight.link && <Link to={insight.link} className="card-link">{insight.link_label}</Link>}
            </div>
          ))}
        </div>
      ) : (
        <p className="muted">Insights will appear here as you build your resume, take quizzes and practise interviews.</p>
      )}
    </section>
  )
}

export default function StudentHome() {
  const { user } = useAuth()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [refreshing, setRefreshing] = useState(false)

  const load = () => {
    setRefreshing(true)
    fetchStudentDashboard()
      .then(setData)
      .catch((e) => setError(apiError(e, 'Could not load dashboard')))
      .finally(() => setRefreshing(false))
  }

  useEffect(() => {
    load()
  }, [])

  if (!data && !error) {
    return <div className="page-loading">Loading…</div>
  }

  const student = data?.student
  const overview = data?.overview || {}
  const profile = data?.profile || {}
  const resume = data?.resume || {}
  const skills = data?.skills || { current: [], detected: [], gaps: [], job_gaps: [], current_count: 0, detected_count: 0, gaps_count: 0, job_gap_count: 0 }
  const quizzes = data?.quiz_performance || {}
  const interviews = data?.interview_performance || {}
  const applications = data?.applications || { recent: [], by_status: {}, total: 0, best_match: null }
  const points = data?.performance_trend || []
  const insights = data?.preparation_insights || []

  return (
    <div className="page dashboard">
      <div className="page-head">
        <div>
          <h1>Student Dashboard</h1>
          <p className="muted">
            Welcome, {student?.full_name || user?.username || 'student'}. Track your placement preparation here.
          </p>
        </div>
        <button className="btn btn-ghost btn-sm" onClick={load} disabled={refreshing}>
          {refreshing ? 'Refreshing…' : 'Refresh'}
        </button>
      </div>

      {error && <div className="alert error">{error}</div>}

      {data && (
        <>
          <div className="cards">
            <Stat
              label="Profile completion"
              value={`${profile.completion ?? 0}%`}
              sub={`${profile.skills_count} skills · ${profile.projects_count} projects`}
            />
            <Stat
              label="Resume"
              value={profile.resume_uploaded ? 'Uploaded' : 'Not uploaded'}
              sub={overview.resume_analyzed ? 'Analysis complete' : profile.resume_uploaded ? 'Not analyzed yet' : 'Upload from the Profile page'}
            />
            <Stat label="Job skill gaps" value={skills.job_gap_count} sub={`across your ${plural(applications.total, 'application')}`} />
            <Stat label="Available jobs" value={overview.jobs_available ?? 0} sub={<Link to="/student/jobs">Browse jobs →</Link>} />
            <Stat label="Applications sent" value={applications.total} sub={applications.best_match !== null ? `Best match: ${applications.best_match}%` : 'No applications yet'} />
            <Stat label="Quiz attempts" value={quizzes.attempts_completed ?? 0} sub={quizzes.average_score != null ? `Average: ${quizzes.average_score}%` : 'No attempts yet'} />
            <Stat label="Mock interviews" value={interviews.completed ?? 0} sub={interviews.average_score != null ? `Average: ${interviews.average_score}/10` : 'No scored sessions'} />
          </div>

          <ResumeSection resume={resume} />
          <SkillsSection skills={skills} />
          <QuizSection quizzes={quizzes} />
          <InterviewSection interviews={interviews} />
          <ApplicationsSection applications={applications} />
          <TrendSection points={points} />
          <InsightsSection insights={insights} />
        </>
      )}

      {!data && error && (
        <p className="muted">
          Could not load your dashboard. <button className="btn btn-ghost btn-sm" onClick={load}>Try again</button>
        </p>
      )}
    </div>
  )
}