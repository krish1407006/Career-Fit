import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchAdminInterview, fetchAdminInterviews } from '../../api/admin'
import InterviewReport from '../../components/interviews/InterviewReport'

const STATUSES = ['in_progress', 'completed', 'cancelled', 'aborted']

const STATUS_BADGE = {
  in_progress: 'processing',
  completed: 'ok',
  cancelled: 'bad',
  aborted: 'bad',
}

const TURN_CLASS = { question: 'q', answer: 'a', evaluation: 'e' }
const TURN_LABEL = { question: 'AI asked', answer: 'Student answered', evaluation: 'AI feedback' }

const formatDate = (value) => {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString()
}

/**
 * Read-only view of every mock interview, with its full transcript.
 *
 * The detail endpoint already lets an admin read any session, so this screen
 * shows exactly the conversation and report the student saw. Only the recognised
 * transcript is ever stored: no microphone audio is kept.
 */
export default function AdminInterviews() {
  const [sessions, setSessions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('all')
  const [openId, setOpenId] = useState(null)
  const [detail, setDetail] = useState(null)
  const [detailError, setDetailError] = useState('')
  const [detailLoading, setDetailLoading] = useState(false)

  const load = useCallback(() => {
    fetchAdminInterviews()
      .then((rows) => {
        setSessions(rows)
        setError('')
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const toggle = async (id) => {
    if (openId === id) {
      setOpenId(null)
      setDetail(null)
      setDetailError('')
      return
    }
    setOpenId(id)
    setDetail(null)
    setDetailError('')
    setDetailLoading(true)
    try {
      setDetail(await fetchAdminInterview(id))
    } catch (e) {
      setDetailError(e.message)
    } finally {
      setDetailLoading(false)
    }
  }

  const term = search.trim().toLowerCase()
  const visible = sessions.filter((session) => {
    if (status !== 'all' && session.status !== status) return false
    if (!term) return true
    return [session.student_username, session.student_email, session.position, session.job_title]
      .filter(Boolean)
      .some((value) => value.toLowerCase().includes(term))
  })

  const stuck = sessions.filter((s) => s.status === 'in_progress').length

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Mock interviews</h1>
          <p className="muted">
            Every interview session, who ran it and how far it got. Open one to read the
            transcript and the report. Read only.
          </p>
        </div>
        <button className="btn btn-ghost" onClick={load} disabled={loading}>
          {loading ? 'Loading…' : 'Refresh'}
        </button>
      </div>

      {error && <div className="alert error">{error}</div>}
      {stuck > 0 && (
        <div className="alert warn">
          {stuck} session(s) are still marked in progress. A session stays there if the
          browser was closed mid-interview; the student resumes or cancels it.
        </div>
      )}

      <div className="cards">
        <div className="card stat-card">
          <div className="stat-value">{sessions.length}</div>
          <div className="stat-label">Sessions</div>
        </div>
        <div className="card stat-card">
          <div className="stat-value">
            {sessions.filter((s) => s.has_report).length}
          </div>
          <div className="stat-label">With a report</div>
        </div>
        <div className="card stat-card">
          <div className="stat-value">
            {sessions.reduce((sum, s) => sum + (s.answers || 0), 0)}
          </div>
          <div className="stat-label">Answers recorded</div>
        </div>
      </div>

      <div className="filter-bar">
        <input
          className="search"
          placeholder="Search student, role or job"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="all">All statuses</option>
          {STATUSES.map((value) => (
            <option key={value} value={value}>{value.replace('_', ' ')}</option>
          ))}
        </select>
      </div>

      <div className="app-table-wrap">
        <table className="app-table">
          <thead>
            <tr>
              <th>Student</th>
              <th>Target role</th>
              <th>Mode</th>
              <th>Progress</th>
              <th>Status</th>
              <th>Report</th>
              <th>Started</th>
              <th aria-label="Actions" />
            </tr>
          </thead>
          <tbody>
            {loading && <tr><td colSpan={8} className="muted">Loading interviews…</td></tr>}
            {!loading && visible.length === 0 && (
              <tr><td colSpan={8} className="muted">No interviews match your search.</td></tr>
            )}
            {visible.map((session) => (
              <tr key={session.id}>
                <td>
                  <strong>{session.student_username}</strong>
                  <div className="muted small">{session.student_email || '—'}</div>
                </td>
                <td>
                  {session.position}
                  {session.job_title && <div className="muted small">{session.job_title}</div>}
                </td>
                <td className="muted small">{session.mode}</td>
                <td>{session.answers}/{session.total_questions}</td>
                <td>
                  <span className={`badge ${STATUS_BADGE[session.status] || 'neutral'}`}>
                    {session.status.replace('_', ' ')}
                  </span>
                </td>
                <td>
                  {session.has_report
                    ? <span className="score-tag ok">{session.report_score ?? '—'}/10</span>
                    : <span className="muted small">none</span>}
                </td>
                <td className="muted small">{formatDate(session.started_at || session.created_at)}</td>
                <td>
                  <button
                    className="btn btn-ghost btn-sm"
                    onClick={() => toggle(session.id)}
                  >
                    {openId === session.id ? 'Close' : 'View transcript'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {openId && (
        <div>
          <h2 className="section-title">Transcript</h2>
          {detailLoading && <p className="muted">Loading transcript…</p>}
          {detailError && <div className="alert error">{detailError}</div>}
          {detail && (
            <>
              <div className="card card-sheet">
                <div className="page-head">
                  <div>
                    <h3>{detail.position}</h3>
                    <p className="muted small">
                      {detail.student?.username} · {detail.mode} · {detail.status} ·{' '}
                      {detail.answers_answered ?? detail.answered_count} answered
                    </p>
                  </div>
                  <span className={`badge ${STATUS_BADGE[detail.status] || 'neutral'}`}>
                    {detail.state?.replace(/_/g, ' ')}
                  </span>
                </div>
                {detail.last_error && (
                  <div className="alert error">Last recorded error: {detail.last_error}</div>
                )}
                <div className="interview-thread" style={{ marginTop: 12 }}>
                  {(detail.turns || []).map((turn) => (
                    <div
                      className={`card card-sheet interview-turn ${TURN_CLASS[turn.kind] || ''}`}
                      key={turn.id}
                    >
                      <div className="page-head">
                        <strong className="muted small">{TURN_LABEL[turn.kind] || turn.kind}</strong>
                        {turn.score !== null && turn.score !== undefined && (
                          <span
                            className={`score-tag ${
                              turn.score >= 8 ? 'ok' : turn.score >= 5 ? 'warn' : 'bad'
                            }`}
                          >
                            {turn.score}/10
                          </span>
                        )}
                      </div>
                      <p className="summary">{turn.content}</p>
                      {turn.category && <p className="muted small">Category: {turn.category}</p>}
                      {turn.suggestions && (
                        <p className="muted small">Suggestions: {turn.suggestions}</p>
                      )}
                      <p className="muted small">
                        {turn.source || 'unknown source'} · {formatDate(turn.created_at)}
                      </p>
                    </div>
                  ))}
                  {(detail.turns || []).length === 0 && (
                    <p className="muted">No turns were recorded for this session.</p>
                  )}
                </div>
              </div>

              {detail.report_data && Object.keys(detail.report_data).length > 0 && (
                <InterviewReport
                  report={detail.report_data}
                  position={detail.position}
                />
              )}
            </>
          )}
          <p className="back-link">
            <Link to="/admin">Back to admin dashboard</Link>
          </p>
        </div>
      )}
    </div>
  )
}
