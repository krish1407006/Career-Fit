import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchAdminResumeAnalysis, fetchAdminResumes } from '../../api/admin'
import { downloadResume } from '../../api/resumes'
import ResumeAnalysisCard from '../../components/resume/ResumeAnalysisCard'

const STATUS_BADGE = {
  analyzed: 'ok',
  uploaded: 'neutral',
  processing: 'processing',
  failed: 'bad',
}

const formatDate = (value) => {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString()
}

/**
 * Read-only view of every uploaded resume and its stored analysis.
 *
 * This is the screen for answering "did the upload and AI analysis actually
 * record something for each student?". Nothing here edits a student's resume.
 */
export default function AdminResumes() {
  const [resumes, setResumes] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('all')
  const [openId, setOpenId] = useState(null)
  const [analysis, setAnalysis] = useState(null)
  const [analysisError, setAnalysisError] = useState('')
  const [analysisLoading, setAnalysisLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setResumes(await fetchAdminResumes())
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  // Open the transcript-free analysis on demand so the table stays fast.
  const toggle = async (resume) => {
    if (openId === resume.id) {
      setOpenId(null)
      setAnalysis(null)
      setAnalysisError('')
      return
    }
    setOpenId(resume.id)
    setAnalysis(null)
    setAnalysisError('')
    setAnalysisLoading(true)
    try {
      setAnalysis(await fetchAdminResumeAnalysis(resume.id))
    } catch (e) {
      setAnalysisError(e.message)
    } finally {
      setAnalysisLoading(false)
    }
  }

  const term = search.trim().toLowerCase()
  const visible = resumes.filter((resume) => {
    if (status !== 'all' && resume.status !== status) return false
    if (!term) return true
    return [resume.student_username, resume.student_email, resume.original_name]
      .filter(Boolean)
      .some((value) => value.toLowerCase().includes(term))
  })

  const analysed = resumes.filter((r) => r.analysis?.has_analysis).length

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Resumes &amp; analyses</h1>
          <p className="muted">
            Every uploaded resume on the platform, with the analysis the student
            actually sees. Read only.
          </p>
        </div>
        <button className="btn btn-ghost" onClick={load} disabled={loading}>
          {loading ? 'Loading…' : 'Refresh'}
        </button>
      </div>

      {error && <div className="alert error">{error}</div>}

      <div className="cards">
        <div className="card stat-card">
          <div className="stat-value">{resumes.length}</div>
          <div className="stat-label">Resumes</div>
        </div>
        <div className="card stat-card">
          <div className="stat-value">{analysed}</div>
          <div className="stat-label">Analysed</div>
          <div className="stat-sub">Rest are uploaded but not analysed yet</div>
        </div>
        <div className="card stat-card">
          <div className="stat-value">
            {resumes.filter((r) => r.status === 'failed').length}
          </div>
          <div className="stat-label">Failed</div>
        </div>
      </div>

      <div className="filter-bar">
        <input
          className="search"
          placeholder="Search student, email or file name"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="all">All statuses</option>
          <option value="analyzed">Analysed</option>
          <option value="uploaded">Uploaded</option>
          <option value="processing">Processing</option>
          <option value="failed">Failed</option>
        </select>
      </div>

      <div className="app-table-wrap">
        <table className="app-table">
          <thead>
            <tr>
              <th>Student</th>
              <th>File</th>
              <th>Status</th>
              <th>Score</th>
              <th>Detected</th>
              <th>Source</th>
              <th>Uploaded</th>
              <th aria-label="Actions" />
            </tr>
          </thead>
          <tbody>
            {loading && <tr><td colSpan={8} className="muted">Loading resumes…</td></tr>}
            {!loading && visible.length === 0 && (
              <tr><td colSpan={8} className="muted">No resumes match your search.</td></tr>
            )}
            {visible.map((resume) => (
              <tr key={resume.id}>
                <td>
                  <strong>{resume.student_username}</strong>
                  <div className="muted small">{resume.student_email || '—'}</div>
                </td>
                <td>{resume.original_name}</td>
                <td>
                  <span className={`badge ${STATUS_BADGE[resume.status] || 'neutral'}`}>
                    {resume.status}
                  </span>
                </td>
                <td>{resume.analysis?.has_analysis ? `${resume.analysis.score}` : '—'}</td>
                <td>{resume.analysis?.detected_skills?.length || 0} skills</td>
                <td className="muted small">
                  {resume.analysis?.has_analysis
                    ? resume.analysis.source === 'ai' ? `AI · ${resume.analysis.provider}`
                      : 'Rule-based'
                    : '—'}
                </td>
                <td className="muted small">{formatDate(resume.uploaded_at)}</td>
                <td>
                  <div className="voice-controls">
                    {resume.analysis && (
                      <button
                        className="btn btn-ghost btn-sm"
                        onClick={() => toggle(resume)}
                      >
                        {openId === resume.id ? 'Hide analysis' : 'View analysis'}
                      </button>
                    )}
                    <button
                      className="btn btn-ghost btn-sm"
                      onClick={() =>
                        downloadResume(resume.id, resume.original_name).catch((e) =>
                          setError(e.message || 'Could not download that resume'),
                        )
                      }
                    >
                      Download
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {openId && (
        <div className="detail-block">
          <h2 className="section-title">Stored analysis</h2>
          {analysisLoading && <p className="muted">Loading analysis…</p>}
          {analysisError && <div className="alert error">{analysisError}</div>}
          {analysis && <ResumeAnalysisCard analysis={analysis} />}
          {analysis?.error_message && (
            <p className="muted small">
              Recorded error: {analysis.error_message}
            </p>
          )}
          <p className="muted small">
            Extracted resume text and the raw AI response are never sent to the browser,
            by design. Everything the student can read is shown above.
          </p>
          <p className="back-link">
            <Link to="/admin">Back to admin dashboard</Link>
          </p>
        </div>
      )}
    </div>
  )
}
