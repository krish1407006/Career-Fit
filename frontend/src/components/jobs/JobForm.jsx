import { useState } from 'react'

const emptyForm = {
  company_name: '',
  title: '',
  description: '',
  responsibilities: '',
  skills_required: '',
  preferred_skills: '',
  job_type: 'full_time',
  location: '',
  salary_range: '',
  education_required: '',
  min_cgpa: '',
  experience_required: '',
  openings: 1,
  is_active: true,
  application_deadline: '',
}

const toCSV = (list) => (list || []).join(', ')

const fromCSV = (value) =>
  (value || '')
    .split(/[,\n]/)
    .map((s) => s.trim())
    .filter(Boolean)

export default function JobForm({
  initial,
  skillOptions = [],
  onSubmit,
  onCancel,
  busy,
  submitLabel,
}) {
  const [form, setForm] = useState(
    initial
      ? {
          ...emptyForm,
          ...initial,
          skills_required: toCSV(initial.skills_required),
          preferred_skills: toCSV(initial.preferred_skills),
        }
      : emptyForm,
  )

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value })

  const submit = (e) => {
    e.preventDefault()
    const payload = {
      ...form,
      responsibilities: fromCSV(form.responsibilities),
      skills_required: fromCSV(form.skills_required),
      preferred_skills: fromCSV(form.preferred_skills),
      min_cgpa: form.min_cgpa === '' ? null : form.min_cgpa,
      application_deadline: form.application_deadline || null,
    }
    onSubmit(payload)
  }

  const label = submitLabel || (initial ? 'Save changes' : 'Post job')

  return (
    <form className="auth-card card-sheet" onSubmit={submit}>
      <h3>{initial ? 'Edit job posting' : 'Post a new job'}</h3>
      <div className="row">
        <label>Company name
          <input value={form.company_name} onChange={set('company_name')} required /></label>
        <label>Job title
          <input value={form.title} onChange={set('title')} placeholder="e.g. Python Developer" required /></label>
      </div>
      <label>Description
        <textarea rows={3} value={form.description} onChange={set('description')} required /></label>
      <label>Responsibilities (comma separated)
        <input value={form.responsibilities} onChange={set('responsibilities')} /></label>
      <div className="row">
        <label>Required skills (comma separated)
          <input
            list="job-required-options"
            value={form.skills_required}
            onChange={set('skills_required')}
            placeholder="e.g. Python, Django, PostgreSQL"
          />
          <datalist id="job-required-options">
            {skillOptions.map((s) => <option key={s} value={s} />)}
          </datalist></label>
        <label>Preferred skills (comma separated)
          <input
            list="job-preferred-options"
            value={form.preferred_skills}
            onChange={set('preferred_skills')}
            placeholder="e.g. Docker, Redis"
          />
          <datalist id="job-preferred-options">
            {skillOptions.map((s) => <option key={s} value={s} />)}
          </datalist></label>
      </div>
      <div className="row">
        <label>Type
          <select value={form.job_type} onChange={set('job_type')}>
            <option value="full_time">Full-time</option>
            <option value="part_time">Part-time</option>
            <option value="internship">Internship</option>
            <option value="contract">Contract</option>
          </select></label>
        <label>Location
          <input value={form.location} onChange={set('location')} placeholder="Remote / Bengaluru" required /></label>
      </div>
      <div className="row">
        <label>Education required
          <input value={form.education_required} onChange={set('education_required')} placeholder="e.g. B.E./B.Tech in CS/IT" /></label>
        <label>Experience required
          <input value={form.experience_required} onChange={set('experience_required')} placeholder="e.g. 1-3 years" /></label>
        <label>Min CGPA (0-10)
          <input type="number" min="0" max="10" step="0.01" value={form.min_cgpa} onChange={set('min_cgpa')} /></label>
        <label>Salary range
          <input value={form.salary_range} onChange={set('salary_range')} placeholder="8-14 LPA" /></label>
        <label>Openings
          <input type="number" min="1" value={form.openings} onChange={set('openings')} /></label>
        <label>Application deadline
          <input type="date" value={form.application_deadline} onChange={set('application_deadline')} /></label>
      </div>
      <label className="check-row">
        <input
          type="checkbox"
          checked={form.is_active}
          onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
        />
        Job is open for applications
      </label>
      <div className="row actions">
        <button type="button" className="btn btn-ghost" onClick={onCancel}>Cancel</button>
        <button className="btn btn-primary" disabled={busy}>
          {busy ? 'Saving…' : label}
        </button>
      </div>
    </form>
  )
}