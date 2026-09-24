import { useState } from 'react'
import StatusBadge from './StatusBadge'
import SkillChips from './SkillChips'

const STATUSES = ['applied', 'shortlisted', 'interview', 'selected', 'rejected']

export default function ApplicantCard({ application, onStatusChange, onDownloadResume }) {
  const [status, setStatus] = useState(application.status)
  const [remarks, setRemarks] = useState(application.remarks || '')
  const [busy, setBusy] = useState(false)
  const [saved, setSaved] = useState(false)

  const profile = application.profile || {}
  const resume = application.resume || {}
  const changed = status !== application.status || remarks !== (application.remarks || '')

  const save = async () => {
    if (!changed) return
    setBusy(true)
    try {
      await onStatusChange(application.application_id, { status, remarks })
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="card applicant">
      <div className="applicant-head">
        <div>
          <strong>{profile.full_name || application.username}</strong>{' '}
          <StatusBadge status={status} />
          <p className="muted small">
            {profile.college || '—'} · {profile.branch || '—'} · Class of{' '}
            {profile.graduation_year || '—'} · CGPA {profile.cgpa || '—'}
            <br />
            {application.email} · Match {application.match_score}% · Applied{' '}
            {new Date(application.applied_at).toLocaleDateString()}
          </p>
        </div>
      </div>
      {profile.skills?.length > 0 && <SkillChips skills={profile.skills} />}
      {application.cover_note && <p className="summary">“{application.cover_note}”</p>}
      {resume.name && (
        <div className="applicant-resume">
          <p className="muted small">
            Resume {resume.name}
            {resume.score !== null && resume.score !== undefined && (
              <> · score <strong>{resume.score}/100</strong> ({resume.source || 'analysis'})</>
            )}
            {onDownloadResume && (
              <button
                className="btn btn-ghost btn-sm link-btn"
                onClick={() => onDownloadResume(application.application_id, resume.id, resume.name)}
              >
                Download
              </button>
            )}
          </p>
          {resume.skills?.length > 0 && (
            <SkillChips skills={resume.skills.slice(0, 12)} />
          )}
        </div>
      )}
      <div className="applicant-controls">
        <label className="control-cell">Status
          <select
            className="status-select"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
          >
            {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select></label>
        <label className="control-cell">Remarks
          <textarea
            rows={2}
            value={remarks}
            onChange={(e) => setRemarks(e.target.value)}
            placeholder="Optional note for the candidate…"
          /></label>
      </div>
      <div className="job-actions">
        <button className="btn btn-primary btn-sm" onClick={save} disabled={!changed || busy}>
          {busy ? 'Saving…' : 'Save'}
        </button>
        {changed && !busy && !saved && <span className="muted small">Unsaved changes</span>}
        {saved && <span className="ok small">Saved</span>}
      </div>
    </div>
  )
}