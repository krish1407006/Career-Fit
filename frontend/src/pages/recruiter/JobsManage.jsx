import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiError } from '../../api/client'
import {
  createJob,
  deleteJob,
  fetchApplicants,
  fetchMyJobs,
  fetchSkills,
  updateApplicationStatus,
  updateJob,
} from '../../api/jobs'
import ApplicantCard from '../../components/jobs/ApplicantCard'
import JobForm from '../../components/jobs/JobForm'
import SkillChips from '../../components/jobs/SkillChips'
import StatusBadge from '../../components/jobs/StatusBadge'
import { downloadResume } from '../../api/resumes'

function ApplicantsModal({ job, onClose }) {
  const [items, setItems] = useState([])
  const [error, setError] = useState('')

  const load = () =>
    fetchApplicants(job.id)
      .then(setItems)
      .catch((e) => setError(apiError(e, 'Could not load applicants')))

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [job.id])

  const onStatusChange = async (applicationId, payload) => {
    try {
      await updateApplicationStatus(applicationId, payload)
      load()
    } catch (e) {
      setError(apiError(e, 'Could not update application'))
      throw e
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal wide" onClick={(e) => e.stopPropagation()}>
        <div className="page-head">
          <h3>Applicants — {job.title}</h3>
          <Link className="btn btn-ghost btn-sm" to={`/recruiter/applications?job_id=${job.id}`}>
            Open all applications
          </Link>
        </div>
        {error && <div className="alert error">{error}</div>}
        {items.length ? (
          <div className="applicant-list">
            {items.map((a) => (
              <ApplicantCard
                key={a.application_id}
                application={a}
                onStatusChange={onStatusChange}
                onDownloadResume={(_appId, resumeId, name) => downloadResume(resumeId, name)}
              />
            ))}
          </div>
        ) : (
          <p className="muted">No applications yet.</p>
        )}
        <button className="btn btn-ghost" onClick={onClose}>Close</button>
      </div>
    </div>
  )
}

export default function JobsManage() {
  const [jobs, setJobs] = useState([])
  const [skills, setSkills] = useState([])
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState(null)
  const [applicantsJob, setApplicantsJob] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const load = () => {
    fetchMyJobs().then(setJobs).catch((e) => setError(apiError(e, 'Could not load jobs')))
  }

  useEffect(() => {
    load()
    fetchSkills().then((s) => setSkills(s.map((x) => x.name))).catch(() => {})
  }, [])

  const onSave = async (payload) => {
    setBusy(true)
    setError('')
    try {
      if (editing) await updateJob(editing.id, payload)
      else await createJob(payload)
      setShowForm(false)
      setEditing(null)
      load()
    } catch (e) {
      setError(apiError(e, 'Could not save job'))
    } finally {
      setBusy(false)
    }
  }

  const onToggleActive = async (job) => {
    setBusy(true)
    setError('')
    try {
      await updateJob(job.id, { is_active: !job.is_active })
      load()
    } catch (e) {
      setError(apiError(e))
    } finally {
      setBusy(false)
    }
  }

  const onDelete = async (id) => {
    if (!window.confirm('Delete this job and its applications?')) return
    setBusy(true)
    setError('')
    try {
      await deleteJob(id)
      load()
    } catch (e) {
      setError(apiError(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>My job postings</h1>
          <p className="muted">
            {jobs.length} posting{jobs.length === 1 ? '' : 's'} ·{' '}
            <Link to="/recruiter/applications">manage all applications →</Link>
          </p>
        </div>
        <button
          className="btn btn-primary"
          onClick={() => {
            setEditing(null)
            setShowForm(!showForm)
          }}
        >
          {showForm && !editing ? 'Hide form' : '+ Post job'}
        </button>
      </div>
      {error && <div className="alert error">{error}</div>}
      {showForm && (
        <JobForm
          initial={editing}
          skillOptions={skills}
          busy={busy}
          onCancel={() => {
            setShowForm(false)
            setEditing(null)
          }}
          onSubmit={onSave}
        />
      )}
      <div className="job-list">
        {jobs.map((j) => (
          <div className="card job-card" key={j.id}>
            <div className="job-head">
              <div>
                <h3>{j.title}</h3>
                <p className="muted">
                  {j.company_name} · {j.location} · {j.job_type.replace('_', ' ')} ·{' '}
                  <StatusBadge status={j.status} />
                </p>
              </div>
              <span className="score-tag neutral">
                {j.application_count ?? 0} applicant{(j.application_count ?? 0) === 1 ? '' : 's'}
              </span>
            </div>
            <SkillChips skills={j.skills_required} />
            <div className="job-actions">
              <button className="btn btn-sm" onClick={() => setApplicantsJob(j)}>
                View applicants ({j.application_count ?? 0})
              </button>
              <button className="btn btn-ghost btn-sm" onClick={() => { setEditing(j); setShowForm(true); }}>
                Edit
              </button>
              <button className="btn btn-ghost btn-sm" onClick={() => onToggleActive(j)}>
                {j.is_active ? 'Close' : 'Reopen'}
              </button>
              <button className="btn btn-danger btn-sm" onClick={() => onDelete(j.id)}>
                Delete
              </button>
            </div>
          </div>
        ))}
        {!jobs.length && <p className="muted">No jobs posted yet.</p>}
      </div>
      {applicantsJob && (
        <ApplicantsModal job={applicantsJob} onClose={() => setApplicantsJob(null)} />
      )}
    </div>
  )
}