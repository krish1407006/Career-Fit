import { useCallback, useEffect, useState } from 'react'
import { apiError } from '../../api/client'
import {
  applyToJob,
  fetchJobs,
  fetchMyApplications,
  skillGap,
} from '../../api/jobs'

function ScoreTag({ score }) {
  if (score === null || score === undefined) return null
  const cls = score >= 70 ? 'ok' : score >= 40 ? 'warn' : 'bad'
  return <span className={`score-tag ${cls}`}>{score}% match</span>
}

function SkillGapModal({ job, onClose }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    skillGap(job.id)
      .then(setData)
      .catch((e) => setError(apiError(e, 'Could not compute gap')))
      .finally(() => setLoading(false))
  }, [job.id])

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>Skill gap — {job.title}</h3>
        {loading && <p className="muted">Analyzing…</p>}
        {error && <div className="alert error">{error}</div>}
        {data && (
          <>
            <p>
              Coverage <strong>{data.coverage}%</strong> — {data.recommendation}
            </p>
            <h4>Matched</h4>
            <div className="chips">
              {data.matched.map((s) => <span key={s} className="chip ok-chip">{s}</span>)}
            </div>
            <h4>Missing</h4>
            {data.missing.length ? (
              <div className="chips">
                {data.missing.map((s) => <span key={s} className="chip miss-chip">{s}</span>)}
              </div>
            ) : (
              <p className="muted">Nothing — you cover every required skill.</p>
            )}
          </>
        )}
        <button className="btn btn-ghost" onClick={onClose}>Close</button>
      </div>
    </div>
  )
}

function JobCard({ job, onShowGap, onApply, busy }) {
  return (
    <div className="card job-card">
      <div className="job-head">
        <div>
          <h3>{job.title}</h3>
          <p className="muted">
            {job.company_name} · {job.location} · {job.job_type.replace('_', ' ')}{' '}
            {job.salary_range && `· ${job.salary_range}`}
          </p>
        </div>
        {job.match && <ScoreTag score={job.match.score} />}
      </div>
      <p className="summary">{job.description}</p>
      <div className="chips">
        {job.skills_required.map((s) => <span key={s} className="chip">{s}</span>)}
      </div>
      {job.match && job.match.skill_gap.missing.length > 0 && (
        <p className="muted small">
          Missing: {job.match.skill_gap.missing.join(', ')}
        </p>
      )}
      <div className="job-actions">
        <button className="btn btn-ghost btn-sm" onClick={onShowGap}>
          Skill gap
        </button>
        {job.applied ? (
          <span className={`badge ${job.application_status}`}>Applied · {job.application_status}</span>
        ) : (
          <button className="btn btn-primary btn-sm" onClick={onApply} disabled={busy}>
            {busy ? 'Applying…' : 'Apply'}
          </button>
        )}
      </div>
    </div>
  )
}

export default function Jobs() {
  const [jobs, setJobs] = useState([])
  const [apps, setApps] = useState([])
  const [query, setQuery] = useState('')
  const [error, setError] = useState('')
  const [gapJob, setGapJob] = useState(null)
  const [busyJob, setBusyJob] = useState(null)

  const load = useCallback(() => {
    setError('')
    const params = query ? { q: query } : {}
    fetchJobs(params).then(setJobs).catch((e) => setError(apiError(e)))
    fetchMyApplications().then(setApps).catch(() => {})
  }, [query])

  useEffect(() => {
    load()
  }, [load])

  const onApply = async (job) => {
    setBusyJob(job.id)
    setError('')
    try {
      await applyToJob(job.id)
      load()
    } catch (e) {
      setError(apiError(e, 'Could not apply'))
    } finally {
      setBusyJob(null)
    }
  }

  return (
    <div className="page">
      <h1>Recommended jobs</h1>
      <p className="muted">
        Jobs are ranked by match with your resume skills. Open “Skill gap” to see what to learn.
      </p>
      {error && <div className="alert error">{error}</div>}
      <input
        className="search"
        placeholder="Search by role, company or location…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      <div className="job-list">
        {jobs.map((j) => (
          <JobCard
            key={j.id}
            job={j}
            busy={busyJob === j.id}
            onShowGap={() => setGapJob(j)}
            onApply={() => onApply(j)}
          />
        ))}
        {!jobs.length && <p className="muted">No jobs match your search.</p>}
      </div>

      <h2 className="section-title">My applications</h2>
      {apps.length ? (
        <div className="app-table-wrap">
          <table className="app-table">
            <thead>
              <tr><th>Job</th><th>Company</th><th>Match</th><th>Status</th><th>Applied</th></tr>
            </thead>
            <tbody>
              {apps.map((a) => (
                <tr key={a.id}>
                  <td>{a.job_title}</td>
                  <td>{a.company}</td>
                  <td>{a.match_score}%</td>
                  <td><span className={`badge ${a.status}`}>{a.status}</span></td>
                  <td>{new Date(a.applied_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="muted">You haven’t applied to any jobs yet.</p>
      )}

      {gapJob && <SkillGapModal job={gapJob} onClose={() => setGapJob(null)} />}
    </div>
  )
}