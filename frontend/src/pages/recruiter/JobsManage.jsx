import { useEffect, useState } from 'react'
import { apiError } from '../../api/client'
import {
  createJob,
  deleteJob,
  fetchApplicants,
  fetchMyJobs,
  fetchSkills,
  updateApplicationStatus,
} from '../../api/jobs'

const emptyForm = {
  company_name: '',
  title: '',
  description: '',
  responsibilities: '',
  skills_required: '',
  job_type: 'full_time',
  location: '',
  salary_range: '',
  openings: 1,
  is_active: true,
}

function JobForm({ skillOptions, onDone, onCancel }) {
  const [form, setForm] = useState(emptyForm)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value })

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    const payload = {
      ...form,
      responsibilities: form.responsibilities.split(',').map((s) => s.trim()).filter(Boolean),
      skills_required: form.skills_required.split(',').map((s) => s.trim()).filter(Boolean),
    }
    try {
      await createJob(payload)
      onDone()
    } catch (err) {
      setError(apiError(err, 'Could not create job'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="auth-card card-sheet" onSubmit={submit}>
      <h3>Post a new job</h3>
      {error && <div className="alert error">{error}</div>}
      <div className="row">
        <label>Company name
          <input value={form.company_name} onChange={set('company_name')} required /></label>
        <label>Job title
          <input value={form.title} onChange={set('title')} required /></label>
      </div>
      <label>Description
        <textarea rows={3} value={form.description} onChange={set('description')} required /></label>
      <label>Responsibilities (comma separated)
        <input value={form.responsibilities} onChange={set('responsibilities')} /></label>
      <label>Required skills (comma separated)
        <input
          list="skill-options"
          value={form.skills_required}
          onChange={set('skills_required')}
          placeholder="e.g. Python, Django, PostgreSQL"
        />
        <datalist id="skill-options">
          {skillOptions.map((s) => <option key={s} value={s} />)}
        </datalist></label>
      <div className="row">
        <label>Type
          <select value={form.job_type} onChange={set('job_type')}>
            <option value="full_time">Full-time</option>
            <option value="part_time">Part-time</option>
            <option value="internship">Internship</option>
            <option value="contract">Contract</option>
          </select></label>
        <label>Location
          <input value={form.location} onChange={set('location')} required /></label>
        <label>Salary range
          <input value={form.salary_range} onChange={set('salary_range')} placeholder="8-14 LPA" /></label>
        <label>Openings
          <input type="number" min="1" value={form.openings} onChange={set('openings')} /></label>
      </div>
      <div className="row actions">
        <button type="button" className="btn btn-ghost" onClick={onCancel}>Cancel</button>
        <button className="btn btn-primary" disabled={busy}>{busy ? 'Posting…' : 'Post job'}</button>
      </div>
    </form>
  )
}

function Applicants({ job, onClose }) {
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

  const setStatus = async (id, status) => {
    try {
      await updateApplicationStatus(id, status)
      load()
    } catch (e) {
      setError(apiError(e))
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal wide" onClick={(e) => e.stopPropagation()}>
        <h3>Applicants — {job.title}</h3>
        {error && <div className="alert error">{error}</div>}
        {items.length ? (
          <div className="applicant-list">
            {items.map((a) => (
              <div className="card applicant" key={a.application_id}>
                <div className="applicant-head">
                  <div>
                    <strong>{a.profile?.full_name || a.username}</strong>{' '}
                    <span className={`badge ${a.status}`}>{a.status}</span>
                    <p className="muted small">
                      {a.profile?.college || '—'} · {a.profile?.branch || '—'} · Class of{' '}
                      {a.profile?.graduation_year || '—'} · CGPA {a.profile?.cgpa || '—'}
                      <br />{a.email} · Match {a.match_score}% as of{' '}
                      {new Date(a.applied_at).toLocaleDateString()}
                    </p>
                  </div>
                  <select
                    className="status-select"
                    value={a.status}
                    onChange={(e) => setStatus(a.application_id, e.target.value)}
                  >
                    {['applied', 'shortlisted', 'rejected', 'selected'].map((s) => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                </div>
                {a.cover_note && <p className="summary">“{a.cover_note}”</p>}
                {a.resume && (
                  <div className="applicant-resume">
                    <p className="muted small">
                      Resume score <strong>{a.resume.score}/100</strong> ({a.resume.source})
                    </p>
                    <div className="chips">
                      {a.resume.skills.slice(0, 12).map((s) => (
                        <span key={s} className="chip">{s}</span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
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
  const [applicantsJob, setApplicantsJob] = useState(null)
  const [error, setError] = useState('')

  const load = () => {
    fetchMyJobs().then(setJobs).catch((e) => setError(apiError(e, 'Could not load jobs')))
  }

  useEffect(() => {
    load()
    fetchSkills().then((s) => setSkills(s.map((x) => x.name))).catch(() => {})
  }, [])

  const onDelete = async (id) => {
    if (!window.confirm('Delete this job and its applications?')) return
    try {
      await deleteJob(id)
      load()
    } catch (e) {
      setError(apiError(e))
    }
  }

  return (
    <div className="page">
      <div className="page-head">
        <h1>My job postings</h1>
        <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>
          {showForm ? 'Hide form' : '+ Post job'}
        </button>
      </div>
      {error && <div className="alert error">{error}</div>}
      {showForm && (
        <JobForm skillOptions={skills} onCancel={() => setShowForm(false)} onDone={() => { setShowForm(false); load() }} />
      )}
      <div className="job-list">
        {jobs.map((j) => (
          <div className="card job-card" key={j.id}>
            <div className="job-head">
              <div>
                <h3>{j.title}</h3>
                <p className="muted">
                  {j.company_name} · {j.location} · {j.job_type.replace('_', ' ')} ·{' '}
                  {j.is_active ? <span className="badge analyzed">active</span> : <span className="badge failed">closed</span>}
                </p>
              </div>
              <span className="score-tag neutral">{j.application_count} applicants</span>
            </div>
            <div className="chips">
              {j.skills_required.map((s) => <span key={s} className="chip">{s}</span>)}
            </div>
            <div className="job-actions">
              <button className="btn btn-sm" onClick={() => setApplicantsJob(j)}>
                View applicants ({j.application_count})
              </button>
              <button className="btn btn-ghost btn-sm" onClick={() => onDelete(j.id)}>Delete</button>
            </div>
          </div>
        ))}
        {!jobs.length && <p className="muted">No jobs posted yet.</p>}
      </div>
      {applicantsJob && <Applicants job={applicantsJob} onClose={() => setApplicantsJob(null)} />}
    </div>
  )
}