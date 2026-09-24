import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { apiError } from '../../api/client'
import { applyToJob, fetchJob, fetchJobMatch } from '../../api/jobs'
import SkillChips from '../../components/jobs/SkillChips'
import StatusBadge from '../../components/jobs/StatusBadge'
import { useAuth } from '../../context/AuthContext'

function MatchPanel({ match }) {
  if (!match) return null
  const cls = match.score >= 70 ? 'ok' : match.score >= 40 ? 'warn' : 'bad'
  return (
    <div className="card match-panel">
      <div className="match-score">
        <span className={`score-tag ${cls}`}>{match.coverage}% match</span>
        <p className="muted">{match.recommendation}</p>
      </div>
      <div className="match-cols">
        <div>
          <h4>Matched skills</h4>
          {match.matched.length ? (
            <SkillChips skills={match.matched} kind="ok" />
          ) : (
            <p className="muted small">None yet.</p>
          )}
        </div>
        <div>
          <h4>Missing skills</h4>
          {match.missing.length ? (
            <SkillChips skills={match.missing} kind="miss" />
          ) : (
            <p className="muted small">Nothing — you cover every required skill.</p>
          )}
        </div>
      </div>
      <div>
        <h4>Required for this job</h4>
        <SkillChips skills={match.skills_required} />
      </div>
      <div>
        <h4>Your skills considered</h4>
        {match.your_skills.length ? (
          <SkillChips skills={match.your_skills} />
        ) : (
          <p className="muted small">
            No skills found. Add them to your <Link to="/student/profile">profile</Link> or
            upload an analyzed resume so we can compute a match.
          </p>
        )}
      </div>
    </div>
  )
}

export default function JobDetails() {
  const { id } = useParams()
  const { profile } = useAuth()
  const [job, setJob] = useState(null)
  const [match, setMatch] = useState(null)
  const [error, setError] = useState('')
  const [coverNote, setCoverNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [applied, setApplied] = useState(false)

  const load = useCallback(() => {
    setError('')
    fetchJob(id)
      .then((data) => {
        setJob(data)
        setApplied(Boolean(data.applied))
      })
      .catch((e) => setError(apiError(e, 'Could not load job')))
    fetchJobMatch(id).then(setMatch).catch(() => {})
  }, [id])

  useEffect(() => {
    load()
  }, [load])

  const onApply = async () => {
    setBusy(true)
    setError('')
    try {
      await applyToJob(id, coverNote)
      setApplied(true)
      load()
    } catch (e) {
      setError(apiError(e, 'Could not apply'))
    } finally {
      setBusy(false)
    }
  }

  if (!job && !error) return <div className="page page-loading">Loading…</div>
  if (!job) return <div className="page"><div className="alert error">{error}</div></div>

  const meta = [
    job.company_name,
    job.location,
    job.job_type?.replace('_', ' '),
    job.salary_range,
    job.recruiter_name && `posted by ${job.recruiter_name}`,
  ]
    .filter(Boolean)
    .join(' · ')

  const cgpa = Number(profile?.cgpa)
  const cgpaShortfall =
    job.min_cgpa != null && !Number.isNaN(cgpa) && cgpa < Number(job.min_cgpa)

  return (
    <div className="page">
      <Link className="back-link" to="/student/jobs">← Back to jobs</Link>
      {error && <div className="alert error">{error}</div>}
      <div className="job-head">
        <div>
          <h1>{job.title}</h1>
          <p className="muted">{meta}</p>
        </div>
        <StatusBadge status={job.status} />
      </div>

      <MatchPanel match={match} />

      <div className="detail-grid">
        <div className="card">
          <h3>Description</h3>
          <p className="summary">{job.description}</p>
          {job.responsibilities?.length > 0 && (
            <>
              <h4>Responsibilities</h4>
              <ul className="suggestions">
                {job.responsibilities.map((r) => <li key={r}>{r}</li>)}
              </ul>
            </>
          )}
          <h4>Required skills</h4>
          <SkillChips skills={job.skills_required} />
          {job.preferred_skills?.length > 0 && (
            <>
              <h4>Preferred skills</h4>
              <SkillChips skills={job.preferred_skills.map((s) => s.name)} />
            </>
          )}
        </div>

        <div className="card">
          <h3>Eligibility & details</h3>
          <dl className="detail-list">
            <div><dt>Education</dt><dd>{job.education_required || 'Open to all'}</dd></div>
            <div><dt>Min CGPA</dt><dd>{job.min_cgpa != null ? job.min_cgpa : 'No minimum'}</dd></div>
            <div><dt>Experience</dt><dd>{job.experience_required || 'Fresher / no experience required'}</dd></div>
            <div><dt>Openings</dt><dd>{job.openings}</dd></div>
            <div><dt>Apply by</dt><dd>{job.application_deadline || 'No deadline'}</dd></div>
            <div><dt>Applicants</dt><dd>{job.application_count ?? 0}</dd></div>
          </dl>
          {cgpaShortfall && (
            <p className="alert error">
              Your CGPA ({profile?.cgpa}) is below the listed minimum ({job.min_cgpa}).
              You can still apply, but you may not be shortlisted.
            </p>
          )}
        </div>
      </div>

      <div className="card apply-card">
        {applied ? (
          <div className="job-actions">
            <StatusBadge status={job.application_status} label={`Applied · ${job.application_status}`} />
            <Link className="btn btn-ghost btn-sm" to="/student/applications">
              View my applications
            </Link>
          </div>
        ) : job.is_active ? (
          <>
            <label>Cover note (optional)
              <textarea
                rows={3}
                value={coverNote}
                onChange={(e) => setCoverNote(e.target.value)}
                placeholder="A short note to the recruiter…"
              />
            </label>
            <div className="job-actions">
              <button className="btn btn-primary" onClick={onApply} disabled={busy}>
                {busy ? 'Applying…' : 'Apply now'}
              </button>
              <span className="muted small">
                Your latest resume and match score ({job.match?.score ?? match?.score ?? 0}%) are shared with the recruiter.
              </span>
            </div>
          </>
        ) : (
          <p className="muted">This job is closed and no longer accepts applications.</p>
        )}
      </div>
    </div>
  )
}