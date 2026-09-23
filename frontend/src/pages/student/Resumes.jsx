import { useEffect, useRef, useState } from 'react'
import { apiError } from '../../api/client'
import { deleteResume, fetchResumes, uploadResume } from '../../api/resumes'

function Skills({ skills }) {
  if (!skills?.length) return <p className="muted">No skills detected yet.</p>
  return (
    <div className="chips">
      {skills.map((s) => (
        <span key={s} className="chip">{s}</span>
      ))}
    </div>
  )
}

function AnalysisCard({ resume, onDelete }) {
  const a = resume.analysis
  return (
    <div className="card resume-card">
      <div className="resume-head">
        <div>
          <strong>{resume.original_name}</strong>
          <span className={`badge ${resume.status}`}>{resume.status}</span>
        </div>
        <div className="resume-actions">
          <a className="btn btn-ghost btn-sm" href={resume.file_url} download>
            Download
          </a>
          <button className="btn btn-ghost btn-sm" onClick={() => onDelete(resume.id)}>
            Delete
          </button>
        </div>
      </div>
      <p className="muted">{new Date(resume.uploaded_at).toLocaleString()}</p>
      {a && (
        <>
          <div className="scorebar">
            <span className={a.score >= 70 ? 'ok' : a.score >= 40 ? 'warn' : 'bad'}>
              Resume score: {a.score}/100
            </span>
            <div className="bar">
              <div className="bar-fill" style={{ width: `${a.score}%` }} />
            </div>
          </div>
          <h4>Detected skills</h4>
          <Skills skills={a.skills} />
          {a.summary && <p className="summary">{a.summary}</p>}
          {a.suggestions?.length > 0 && (
            <>
              <h4>Suggestions</h4>
              <ul className="suggestions">
                {a.suggestions.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ul>
            </>
          )}
          <p className="muted">
            Source: <em>{a.source === 'ai' ? 'AI analysis' : 'offline analysis'}</em>
          </p>
        </>
      )}
    </div>
  )
}

export default function Resumes() {
  const [items, setItems] = useState([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [dragOver, setDragOver] = useState(false)
  const inputRef = useRef(null)

  const load = () =>
    fetchResumes().then(setItems).catch((e) => setError(apiError(e, 'Failed to load resumes')))

  useEffect(() => {
    load()
  }, [])

  const handleFile = async (file) => {
    if (!file) return
    setBusy(true)
    setError('')
    try {
      const created = await uploadResume(file)
      setItems((prev) => [created, ...prev])
    } catch (err) {
      setError(apiError(err, 'Upload failed'))
    } finally {
      setBusy(false)
    }
  }

  const onDelete = async (id) => {
    if (!window.confirm('Delete this resume?')) return
    try {
      await deleteResume(id)
      setItems((prev) => prev.filter((r) => r.id !== id))
    } catch (err) {
      setError(apiError(err, 'Delete failed'))
    }
  }

  return (
    <div className="page">
      <h1>Resume analysis</h1>
      <p className="muted">
        Upload your resume (PDF, DOCX or TXT). The system extracts your skills and gives a
        score with suggestions. Works with AI or offline analysis.
      </p>

      {error && <div className="alert error">{error}</div>}

      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.docx,.txt"
        hidden
        onChange={(e) => handleFile(e.target.files[0])}
      />
      <div
        className={`dropzone ${dragOver ? 'over' : ''}`}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragOver(false)
          handleFile(e.dataTransfer.files[0])
        }}
      >
        {busy ? 'Analyzing your resume…' : 'Click or drop your resume here'}
      </div>

      <div className="resume-list">
        {items.map((r) => (
          <AnalysisCard key={r.id} resume={r} onDelete={onDelete} />
        ))}
        {!items.length && !busy && <p className="muted">No resumes uploaded yet.</p>}
      </div>
    </div>
  )
}