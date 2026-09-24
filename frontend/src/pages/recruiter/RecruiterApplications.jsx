import { useCallback, useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { apiError } from '../../api/client'
import { fetchMyJobs, fetchRecruiterApplications, updateApplicationStatus } from '../../api/jobs'
import ApplicantCard from '../../components/jobs/ApplicantCard'
import StatusBadge from '../../components/jobs/StatusBadge'
import { downloadResume } from '../../api/resumes'

const STATUSES = ['applied', 'shortlisted', 'interview', 'selected', 'rejected']

export default function RecruiterApplications() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [jobs, setJobs] = useState([])
  const [apps, setApps] = useState([])
  const [error, setError] = useState('')

  const jobId = searchParams.get('job_id') || ''
  const status = searchParams.get('status') || ''

  const loadJobs = () => {
    fetchMyJobs().then(setJobs).catch(() => {})
  }

  const load = useCallback(() => {
    setError('')
    const params = {}
    if (jobId) params.job_id = jobId
    if (status) params.status = status
    fetchRecruiterApplications(params)
      .then(setApps)
      .catch((e) => setError(apiError(e, 'Could not load applications')))
  }, [jobId, status])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    loadJobs()
  }, [])

  const setFilter = (key) => (e) => {
    const next = { ...Object.fromEntries(searchParams) }
    if (e.target.value) next[key] = e.target.value
    else delete next[key]
    setSearchParams(next)
  }

  const onStatusChange = async (applicationId, payload) => {
    try {
      await updateApplicationStatus(applicationId, payload)
      load()
    } catch (e) {
      setError(apiError(e, 'Could not update application'))
      throw e
    }
  }

  const counts = STATUSES.reduce(
    (acc, s) => ({ ...acc, [s]: apps.filter((a) => a.status === s).length }),
    {},
  )

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Applications</h1>
          <p className="muted">All applications across your job postings, newest first.</p>
        </div>
        <div className="job-actions">
          <Link className="btn btn-ghost btn-sm" to="/recruiter/jobs">My jobs</Link>
        </div>
      </div>
      {error && <div className="alert error">{error}</div>}
      <div className="filter-bar">
        <select value={jobId} onChange={setFilter('job_id')} aria-label="Job">
          <option value="">All jobs</option>
          {jobs.map((j) => (
            <option key={j.id} value={j.id}>{j.title}</option>
          ))}
        </select>
        <select value={status} onChange={setFilter('status')} aria-label="Status">
          <option value="">All statuses</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <span className="muted small">{apps.length} shown</span>
      </div>
      {apps.length > 0 && (
        <div className="status-summary">
          {STATUSES.map((s) => (
            <span key={s} className="muted small">
              <StatusBadge status={s} /> {counts[s]}
            </span>
          ))}
        </div>
      )}
      {!apps.length && <p className="muted">No applications match the current filters.</p>}
      <div className="applicant-list">
        {apps.map((a) => (
          <div key={a.application_id}>
            {!jobId && (
              <h4 className="applicant-job-title">
                {a.job_title}
                <span className="muted small"> · {a.company} · {a.location}</span>
              </h4>
            )}
            <ApplicantCard
              application={a}
              onStatusChange={onStatusChange}
              onDownloadResume={(_appId, resumeId, name) => downloadResume(resumeId, name)}
            />
          </div>
        ))}
      </div>
    </div>
  )
}