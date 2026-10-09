import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiError } from '../../api/client'
import { fetchJobs, skillGap } from '../../api/jobs'
import SkillChips from '../../components/jobs/SkillChips'
import { coverageBucket } from '../../lib/skillGap'

function GapPanel({ gap }) {
  return (
    <div className="card match-panel">
      <div className="match-score">
        <span className={`score-tag ${coverageBucket(gap.score)}`}>{gap.coverage}% match</span>
        <p className="muted">{gap.recommendation}</p>
      </div>
      <div className="match-cols">
        <div>
          <h4>Matched skills</h4>
          {gap.matched.length ? (
            <SkillChips skills={gap.matched} kind="ok" />
          ) : (
            <p className="muted small">None yet.</p>
          )}
        </div>
        <div>
          <h4>Missing skills</h4>
          {gap.missing.length ? (
            <SkillChips skills={gap.missing} kind="miss" />
          ) : (
            <p className="muted small">Nothing — you cover every required skill.</p>
          )}
        </div>
      </div>
      <div>
        <h4>Required for {gap.job.title}</h4>
        {gap.skills_required.length ? (
          <SkillChips skills={gap.skills_required} />
        ) : (
          <p className="muted small">This job lists no required skills.</p>
        )}
      </div>
      <div>
        <h4>Your skills considered</h4>
        {gap.your_skills.length ? (
          <SkillChips skills={gap.your_skills} />
        ) : (
          <p className="muted small">
            No skills found. Add them to your <Link to="/student/profile">profile</Link> or
            analyze a resume so we can compute a gap.
          </p>
        )}
      </div>
      <div>
        <Link className="btn btn-ghost btn-sm" to={`/student/jobs/${gap.job.id}`}>
          View job
        </Link>
      </div>
    </div>
  )
}

export default function SkillGap() {
  const [jobs, setJobs] = useState(null)
  const [jobsError, setJobsError] = useState('')
  const [selectedId, setSelectedId] = useState('')
  const [gap, setGap] = useState(null)
  const [gapLoading, setGapLoading] = useState(false)
  const [gapError, setGapError] = useState('')

  const loadJobs = useCallback(() => {
    fetchJobs()
      .then((data) => {
        const rows = Array.isArray(data) ? data : data.results ?? []
        setJobs(rows)
      })
      .catch((e) => {
        setJobs([])
        setJobsError(apiError(e, 'Could not load jobs'))
      })
  }, [])

  useEffect(() => {
    loadJobs()
  }, [loadJobs])

  const retryJobs = () => {
    setJobs(null)
    setJobsError('')
    loadJobs()
  }

  const loadGap = useCallback((jobId) => {
    if (!jobId) return
    setGapLoading(true)
    setGapError('')
    skillGap(jobId)
      .then(setGap)
      .catch((e) => {
        setGap(null)
        setGapError(apiError(e, 'Could not compute your skill gap'))
      })
      .finally(() => setGapLoading(false))
  }, [])

  const onSelect = (e) => {
    const id = e.target.value
    setSelectedId(id)
    setGap(null)
    setGapError('')
    if (id) loadGap(id)
  }

  return (
    <div className="page">
      <h1>Skill gap analysis</h1>
      <p className="muted">
        Pick a job to see which of its required skills you already cover and which
        to learn next. Matching uses the skills on your profile and your latest
        analyzed resume.
      </p>

      {jobsError ? (
        <div className="card">
          <div className="alert error">{jobsError}</div>
          <button className="btn btn-ghost btn-sm" onClick={retryJobs}>
            Retry
          </button>
        </div>
      ) : jobs === null ? (
        <div className="page-loading">Loading jobs…</div>
      ) : jobs.length === 0 ? (
        <div className="card">
          <p className="muted">There are no open jobs to compare against right now.</p>
          <Link className="btn btn-ghost btn-sm" to="/student/jobs">
            Back to jobs
          </Link>
        </div>
      ) : (
        <>
          <div className="filter-bar">
            <select value={selectedId} onChange={onSelect} aria-label="Choose a job">
              <option value="">Select a job…</option>
              {jobs.map((job) => (
                <option key={job.id} value={job.id}>
                  {job.title} — {job.company_name}
                </option>
              ))}
            </select>
          </div>

          {gapLoading && <div className="page-loading">Analyzing your skills…</div>}

          {!gapLoading && gapError && (
            <div className="card">
              <div className="alert error">{gapError}</div>
              <button className="btn btn-ghost btn-sm" onClick={() => loadGap(selectedId)}>
                Retry
              </button>
            </div>
          )}

          {!gapLoading && !gapError && gap && <GapPanel gap={gap} />}

          {!gapLoading && !gapError && !gap && (
            <div className="card">
              <p className="muted">Select a job above to see your skill gap.</p>
            </div>
          )}
        </>
      )}
    </div>
  )
}
