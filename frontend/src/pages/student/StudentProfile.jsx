import { useEffect, useRef, useState } from 'react'
import { apiError } from '../../api/client'
import { fetchProfile } from '../../api/profile'
import {
  addCertification,
  addEducation,
  addProject,
  addSkill,
  deleteCertification,
  deleteEducation,
  deleteProject,
  removeSkill,
  updateCertification,
  updateEducation,
  updateProject,
  updateProfile,
} from '../../api/profile'
import { deleteResume, downloadResume, analyzeResume, uploadResume } from '../../api/resumes'
import ResumeAnalysisCard from '../../components/resume/ResumeAnalysisCard'

// ---------------------------------------------------------------------------
// Personal information
// ---------------------------------------------------------------------------
const PROFILE_FIELDS = [
  ['full_name', 'Full name', 'text'],
  ['phone', 'Phone', 'text'],
  ['college', 'College / Institute', 'text'],
  ['degree', 'Degree', 'text'],
  ['branch', 'Branch', 'text'],
  ['graduation_year', 'Graduation year', 'number'],
  ['cgpa', 'CGPA', 'decimal'],
  ['location', 'Location', 'text'],
] // bio and preferred lists rendered separately below

function PersonalCard({ profile, onSaved }) {
  const [form, setForm] = useState(() => ({
    full_name: profile?.full_name || '',
    college: profile?.college || '',
    degree: profile?.degree || '',
    branch: profile?.branch || '',
    graduation_year: profile?.graduation_year ?? '',
    cgpa: profile?.cgpa ?? '',
    phone: profile?.phone || '',
    location: profile?.location || '',
    bio: profile?.bio || '',
    preferred_roles: profile?.preferred_roles || [],
    preferred_technologies: profile?.preferred_technologies || [],
  }))
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState({ type: '', text: '' })

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value })
  const setList = (key) => (e) =>
    setForm({
      ...form,
      [key]: e.target.value.split(',').map((s) => s.trim()).filter(Boolean),
    })

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setMsg({ type: '', text: '' })
    try {
      await updateProfile(form)
      setMsg({ type: 'ok', text: 'Personal information saved.' })
      onSaved?.()
    } catch (err) {
      setMsg({ type: 'error', text: apiError(err, 'Failed to save profile') })
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="card">
      <div className="section-head">
        <h3>Personal information</h3>
      </div>
      {msg.text && <div className={`alert ${msg.type}`}>{msg.text}</div>}
      <form onSubmit={submit} className="profile-form">
        <div className="row">
          {PROFILE_FIELDS.map(([key, label, type]) => (
            <label key={key}>
              {label}
              <input
                type={type === 'decimal' ? 'number' : type}
                step={type === 'decimal' ? '0.01' : undefined}
                value={form[key] ?? ''}
                onChange={set(key)}
              />
            </label>
          ))}
        </div>
        <div className="row">
          <label>
            Preferred roles (comma separated) — e.g. SDE, Django Developer
            <input value={(form.preferred_roles || []).join(', ')} onChange={setList('preferred_roles')} />
          </label>
          <label>
            Preferred technologies (comma separated) — e.g. Python, React
            <input
              value={(form.preferred_technologies || []).join(', ')}
              onChange={setList('preferred_technologies')}
            />
          </label>
        </div>
        <label>
          About / Bio
          <textarea rows={3} value={form.bio || ''} onChange={set('bio')} placeholder="A short summary about you..." />
        </label>
        <button className="btn btn-primary" disabled={busy}>
          {busy ? 'Saving…' : 'Save'}
        </button>
      </form>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Skills
// ---------------------------------------------------------------------------
function SkillsCard({ skills, onChanged }) {
  const [name, setName] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const add = async (e) => {
    e.preventDefault()
    if (!name.trim()) return
    setBusy(true)
    setError('')
    try {
      await addSkill(name.trim())
      setName('')
      onChanged?.()
    } catch (err) {
      setError(apiError(err, 'Could not add skill'))
    } finally {
      setBusy(false)
    }
  }

  const remove = async (id) => {
    try {
      await removeSkill(id)
      onChanged?.()
    } catch (err) {
      setError(apiError(err, 'Could not remove skill'))
    }
  }

  return (
    <div className="card">
      <div className="section-head">
        <h3>Skills</h3>
      </div>
      {error && <div className="alert error">{error}</div>}
      {skills.length ? (
        <div className="chips">
          {skills.map((s) => (
            <button
              key={s.id}
              type="button"
              className={`chip remove ${s.source === 'ai' ? 'ai-chip' : ''}`}
              onClick={() => remove(s.id)}
              title={s.source === 'ai' ? 'Detected by AI — click to remove' : 'Manually added — click to remove'}
            >
              {s.name} ×
            </button>
          ))}
        </div>
      ) : (
        <p className="muted">No skills added yet. Add a few to boost your profile.</p>
      )}
      <form className="chip-add-row" onSubmit={add}>
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Add a skill, e.g. Python" />
        <button className="btn btn-sm" disabled={busy || !name.trim()}>
          Add
        </button>
      </form>
      {skills.some((s) => s.source === 'ai') && (
        <p className="muted small">
          Skills highlighted in blue were detected by AI resume analysis. Your manually added skills are never removed.
        </p>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Generic string field config
// ---------------------------------------------------------------------------
const FIELD_TYPES = {
  text: { inputType: 'text', parse: (v) => v },
  textarea: { inputType: 'textarea', parse: (v) => v },
  number: { inputType: 'number', parse: (v) => (v === '' ? null : Number(v)) },
  decimal: { inputType: 'number', parse: (v) => (v === '' ? null : Number(v)), step: '0.01' },
  date: { inputType: 'date', parse: (v) => v || null },
  url: { inputType: 'url', parse: (v) => v },
  list: { inputType: 'text', parse: (v) => v.split(',').map((s) => s.trim()).filter(Boolean), join: true },
  bool: { inputType: 'checkbox', parse: (v) => Boolean(v) },
}

function ItemForm({ fields, value, title, onClose, onSubmit }) {
  const [form, setForm] = useState(() => {
    const out = {}
    fields.forEach((f) => {
      const raw = value?.[f.key] ?? f.default ?? ''
      out[f.key] = Array.isArray(raw) ? raw.join(', ') : raw
    })
    return out
  })
  const [busy, setBusy] = useState(false)

  const set = (key) => (e) =>
    setForm({ ...form, [key]: e.target.type === 'checkbox' ? e.target.checked : e.target.value })

  const submit = (e) => {
    e.preventDefault()
    const payload = {}
    fields.forEach((f) => {
      const cfg = FIELD_TYPES[f.type] || FIELD_TYPES.text
      const raw = form[f.key]
      payload[f.key] = f.type === 'list' ? cfg.parse(raw) : cfg.parse(raw ?? '')
    })
    setBusy(true)
    onSubmit(payload)
      .then(() => onClose())
      .catch((err) => {
        setBusy(false)
        alert(apiError(err, 'Could not save'))
      })
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <form className="modal" onClick={(e) => e.stopPropagation()} onSubmit={submit}>
        <h3>{title}</h3>
        {fields.map((f) => {
          const cfg = FIELD_TYPES[f.type] || FIELD_TYPES.text
          return (
            <label key={f.key}>
              {f.label}
              {f.type === 'list'
                ? <input type="text" value={form[f.key]} onChange={set(f.key)} placeholder={f.placeholder} />
                : cfg.inputType === 'textarea'
                  ? <textarea rows={3} value={form[f.key]} onChange={set(f.key)} placeholder={f.placeholder} />
                  : cfg.inputType === 'checkbox'
                    ? <div className="check-row"><input type="checkbox" checked={form[f.key]} onChange={set(f.key)} /> Currently studying here</div>
                    : <input type={cfg.inputType} step={cfg.step} value={form[f.key]} onChange={set(f.key)} placeholder={f.placeholder} />}
            </label>
          )
        })}
        <div className="actions">
          <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" disabled={busy}>{busy ? 'Saving…' : 'Save'}</button>
        </div>
      </form>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Generic list + add/edit/delete section
// ---------------------------------------------------------------------------
function CrudSection({ title, items, fields, emptyText, renderItem, empty, onAdd, onUpdate, onDelete }) {
  const [open, setOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [error, setError] = useState('')

  const startAdd = () => {
    setEditing(empty)
    setOpen(true)
  }
  const startEdit = (item) => {
    setEditing(item)
    setOpen(true)
  }
  const handleSubmit = (payload) =>
    (editing?.id ? onUpdate(editing.id, payload) : onAdd(payload))

  const handleDelete = async (id) => {
    if (!window.confirm(`Delete this ${title === 'Education' ? 'entry' : title.toLowerCase().slice(0, -1)}?`)) return
    try {
      await onDelete(id)
    } catch (err) {
      setError(apiError(err, 'Delete failed'))
    }
  }

  return (
    <div className="card">
      <div className="section-head">
        <h3>{title}</h3>
        <button className="btn btn-sm btn-primary" onClick={startAdd}>Add</button>
      </div>
      {error && <div className="alert error">{error}</div>}
      {items.length ? (
        <ul className="item-list">
          {items.map((item) => (
            <li key={item.id} className="list-item">
              <div className="list-item-body">{renderItem(item)}</div>
              <div className="resume-actions">
                <button className="btn btn-ghost btn-sm" onClick={() => startEdit(item)}>Edit</button>
                <button className="btn btn-danger btn-sm" onClick={() => handleDelete(item.id)}>Delete</button>
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <p className="muted">{emptyText}</p>
      )}
      {open && (
        <ItemForm
          fields={fields}
          value={editing}
          title={editing?.id ? `Edit ${title}` : `Add ${title}`}
          onClose={() => { setOpen(false); setEditing(null) }}
          onSubmit={handleSubmit}
        />
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Resume
// ---------------------------------------------------------------------------
function ResumeCard({ resume, onChanged }) {
  const [busy, setBusy] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [analysis, setAnalysis] = useState(null)
  const [error, setError] = useState('')
  const [dragOver, setDragOver] = useState(false)
  const inputRef = useRef(null)

  useEffect(() => {
    setAnalysis(resume?.analysis ?? null)
  }, [resume?.id, resume?.analysis?.updated_at, resume?.analysis?.status])

  const handleFile = async (file) => {
    if (!file) return
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setError('Only PDF files are supported.')
      return
    }
    setBusy(true)
    setError('')
    try {
      await uploadResume(file)
      setAnalysis(null)
      onChanged?.()
    } catch (err) {
      setError(apiError(err, 'Upload failed'))
    } finally {
      setBusy(false)
    }
  }

  const handleDelete = async () => {
    if (!window.confirm('Delete your current resume?')) return
    try {
      await deleteResume(resume.id)
      setAnalysis(null)
      onChanged?.()
    } catch (err) {
      setError(apiError(err, 'Delete failed'))
    }
  }

  const handleAnalyze = async () => {
    setAnalyzing(true)
    setError('')
    try {
      const data = await analyzeResume(resume.id)
      setAnalysis(data)
      onChanged?.()
    } catch (err) {
      setError(apiError(err, 'Could not analyse your resume'))
      onChanged?.()
    } finally {
      setAnalyzing(false)
    }
  }

  if (!resume) {
    return (
      <div className="card">
        <div className="section-head">
          <h3>Resume</h3>
        </div>
        {error && <div className="alert error">{error}</div>}
        <input
          ref={inputRef}
          type="file"
          accept=".pdf"
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
          {busy ? 'Uploading…' : 'Click or drop your resume (PDF) here'}
        </div>
        <p className="muted">Only PDF files up to 10 MB are accepted. Uploading a new file replaces your current resume.</p>
      </div>
    )
  }

  return (
    <>
      <div className="card">
        <div className="section-head">
          <h3>Resume</h3>
          <div className="resume-actions">
            <button
              className="btn btn-primary btn-sm"
              onClick={handleAnalyze}
              disabled={analyzing}
              title="Extract text and get AI feedback"
            >
              {analyzing ? 'Analyzing…' : analysis?.has_analysis ? 'Re-analyze resume' : 'Analyze resume'}
            </button>
            <button className="btn btn-ghost btn-sm" onClick={() => downloadResume(resume.id, resume.original_name)}>
              Download
            </button>
            <button className="btn btn-ghost btn-sm" onClick={() => inputRef.current?.click()} disabled={busy}>
              Replace
            </button>
            <button className="btn btn-danger btn-sm" onClick={handleDelete}>Delete</button>
          </div>
        </div>
        {error && <div className="alert error">{error}</div>}
        <input
          ref={inputRef}
          type="file"
          accept=".pdf"
          hidden
          onChange={(e) => handleFile(e.target.files[0])}
        />
        <div className="resume-head">
          <div>
            <strong>{resume.original_name}</strong>
            <span className={`badge ${resume.status}`}>{resume.status}</span>
          </div>
          <p className="muted">{new Date(resume.uploaded_at).toLocaleString()}</p>
        </div>
        {analyzing && (
          <p className="muted small">
            Reading your PDF and analysing it. This usually takes a few seconds.
          </p>
        )}
        {!analysis && !analyzing && (
          <p className="muted small">
            Run AI analysis to get detected skills, strengths, skill gaps and improvement suggestions.
          </p>
        )}
      </div>
      <ResumeAnalysisCard analysis={analysis} />
    </>
  )
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------
const EDUCATION_FIELDS = [
  { key: 'institution', label: 'Institution', type: 'text' },
  { key: 'degree', label: 'Degree', type: 'text' },
  { key: 'field_of_study', label: 'Field of study / Branch', type: 'text' },
  { key: 'start_year', label: 'Start year', type: 'number' },
  { key: 'end_year', label: 'End year', type: 'number' },
  { key: 'cgpa', label: 'CGPA', type: 'decimal' },
  { key: 'is_current', label: 'Current', type: 'bool' },
]

const PROJECT_FIELDS = [
  { key: 'title', label: 'Project title', type: 'text' },
  { key: 'description', label: 'Description', type: 'textarea' },
  { key: 'technologies', label: 'Technologies used (comma separated)', type: 'list' },
  { key: 'link', label: 'Project URL', type: 'url' },
]

const CERT_FIELDS = [
  { key: 'name', label: 'Certification name', type: 'text' },
  { key: 'issuer', label: 'Issuing organization', type: 'text' },
  { key: 'issue_date', label: 'Issue date', type: 'date' },
  { key: 'credential_url', label: 'Credential URL', type: 'url' },
]

export default function StudentProfile() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  const load = () =>
    fetchProfile()
      .then(setData)
      .catch((e) => setError(apiError(e, 'Could not load your profile')))

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  if (!data && !error) return <div className="page-stub">Loading your profile…</div>
  if (error && !data) return <div className="page"><div className="alert error">{error}</div></div>

  return (
    <div className="page">
      <div className="page-head">
        <h1>My profile</h1>
        <span className="muted">Completion: {data.completion}%</span>
      </div>
      <div className="scorebar">
        <div className="bar">
          <div className="bar-fill" style={{ width: `${data.completion}%` }} />
        </div>
      </div>
      {error && <div className="alert error">{error}</div>}
      <div className="profile-grid">
        <PersonalCard profile={data.profile} onSaved={load} />
        <SkillsCard skills={data.skills} onChanged={load} />
        <CrudSection
          title="Education"
          items={data.education}
          fields={EDUCATION_FIELDS}
          empty={{}}
          emptyText="No education added yet."
          onAdd={addEducation}
          onUpdate={updateEducation}
          onDelete={deleteEducation}
          renderItem={(e) => (
            <>
              <strong>{e.degree} {e.field_of_study && `· ${e.field_of_study}`}</strong>
              <p>{e.institution}{e.is_current && ' · Currently studying'}</p>
              <p className="muted">
                {[e.start_year, e.end_year].filter(Boolean).join(' – ')}
                {e.cgpa ? ` · CGPA ${e.cgpa}` : ''}
              </p>
            </>
          )}
        />
        <CrudSection
          title="Projects"
          items={data.projects}
          fields={PROJECT_FIELDS}
          empty={{}}
          emptyText="No projects added yet."
          onAdd={addProject}
          onUpdate={updateProject}
          onDelete={deleteProject}
          renderItem={(p) => (
            <>
              <strong>{p.title}</strong>
              {p.link && <a className="muted small" href={p.link} target="_blank" rel="noreferrer"> · open</a>}
              {p.description && <p>{p.description}</p>}
              {p.technologies?.length > 0 && (
                <div className="chips">
                  {p.technologies.map((t) => <span key={t} className="chip">{t}</span>)}
                </div>
              )}
            </>
          )}
        />
        <CrudSection
          title="Certifications"
          items={data.certifications}
          fields={CERT_FIELDS}
          empty={{}}
          emptyText="No certifications added yet."
          onAdd={addCertification}
          onUpdate={updateCertification}
          onDelete={deleteCertification}
          renderItem={(c) => (
            <>
              <strong>{c.name}</strong>
              {c.issuer && <p>{c.issuer}</p>}
              <p className="muted">
                {c.issue_date ? new Date(c.issue_date).toLocaleDateString(undefined, { year: 'numeric', month: 'short' }) : ''}
                {c.credential_url && ` · `}
                {c.credential_url && <a href={c.credential_url} target="_blank" rel="noreferrer">credential</a>}
              </p>
            </>
          )}
        />
        <ResumeCard resume={data.resume} onChanged={load} />
      </div>
    </div>
  )
}