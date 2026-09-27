import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchAdminAttempt, fetchAdminAttempts } from '../../api/admin'

const formatDate = (value) => {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString()
}

const optionText = (row, index) =>
  row.options?.[index] ?? (index === null || index === undefined ? 'No answer' : `Option ${index + 1}`)

/**
 * Read-only view of every quiz attempt, with the per-question review the
 * student saw after submitting. Also covers attempts left mid-quiz.
 */
export default function AdminAttempts() {
  const [attempts, setAttempts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('all')
  const [openId, setOpenId] = useState(null)
  const [detail, setDetail] = useState(null)
  const [detailError, setDetailError] = useState('')
  const [detailLoading, setDetailLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setAttempts(await fetchAdminAttempts())
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
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
      setDetail(await fetchAdminAttempt(id))
    } catch (e) {
      setDetailError(e.message)
    } finally {
      setDetailLoading(false)
    }
  }

  const term = search.trim().toLowerCase()
  const visible = attempts.filter((attempt) => {
    if (status !== 'all' && attempt.status !== status) return false
    if (!term) return true
    return [attempt.student_username, attempt.quiz_title, attempt.quiz_category]
      .filter(Boolean)
      .some((value) => value.toLowerCase().includes(term))
  })

  const done = attempts.filter((a) => a.status === 'completed')
  const average = done.length
    ? Math.round(done.reduce((sum, a) => sum + (a.score_percent || 0), 0) / done.length)
    : 0

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Quiz attempts</h1>
          <p className="muted">
            Every attempt submitted by every account, with the server-side score. Read only.
          </p>
        </div>
        <button className="btn btn-ghost" onClick={load} disabled={loading}>
          {loading ? 'Loading…' : 'Refresh'}
        </button>
      </div>

      {error && <div className="alert error">{error}</div>}

      <div className="cards">
        <div className="card stat-card">
          <div className="stat-value">{attempts.length}</div>
          <div className="stat-label">Attempts</div>
        </div>
        <div className="card stat-card">
          <div className="stat-value">{done.length}</div>
          <div className="stat-label">Submitted</div>
          <div className="stat-sub">
            {attempts.length - done.length} left in progress
          </div>
        </div>
        <div className="card stat-card">
          <div className="stat-value">{average}%</div>
          <div className="stat-label">Average score</div>
        </div>
        <div className="card stat-card">
          <div className="stat-value">{attempts.filter((a) => a.passed).length}</div>
          <div className="stat-label">Passed</div>
          <div className="stat-sub">60% or higher</div>
        </div>
      </div>

      <div className="filter-bar">
        <input
          className="search"
          placeholder="Search student or quiz"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="all">All statuses</option>
          <option value="completed">Submitted</option>
          <option value="in_progress">In progress</option>
        </select>
      </div>

      <div className="app-table-wrap">
        <table className="app-table">
          <thead>
            <tr>
              <th>Student</th>
              <th>Quiz</th>
              <th>Category</th>
              <th>Result</th>
              <th>Score</th>
              <th>Status</th>
              <th>Started</th>
              <th aria-label="Actions" />
            </tr>
          </thead>
          <tbody>
            {loading && <tr><td colSpan={8} className="muted">Loading attempts…</td></tr>}
            {!loading && visible.length === 0 && (
              <tr><td colSpan={8} className="muted">No attempts match your search.</td></tr>
            )}
            {visible.map((attempt) => (
              <tr key={attempt.id}>
                <td><strong>{attempt.student_username}</strong></td>
                <td>{attempt.quiz_title}</td>
                <td className="muted small">{attempt.quiz_difficulty}</td>
                <td>
                  {attempt.status === 'completed' ? (
                    <span className={`score-tag ${attempt.passed ? 'ok' : 'bad'}`}>
                      {attempt.correct_count}/{attempt.total}
                    </span>
                  ) : (
                    <span className="muted small">—</span>
                  )}
                </td>
                <td>
                  {attempt.status === 'completed'
                    ? <span className={attempt.passed ? 'ok' : 'bad'}>{attempt.score_percent}%</span>
                    : <span className="muted">—</span>}
                </td>
                <td>
                  <span className={`badge ${attempt.status === 'completed' ? 'ok' : 'processing'}`}>
                    {attempt.status.replace('_', ' ')}
                  </span>
                </td>
                <td className="muted small">{formatDate(attempt.started_at)}</td>
                <td>
                  <button
                    className="btn btn-ghost btn-sm"
                    onClick={() => toggle(attempt.id)}
                  >
                    {openId === attempt.id ? 'Close' : 'View review'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {openId && (
        <div>
          <h2 className="section-title">Question review</h2>
          {detailLoading && <p className="muted">Loading review…</p>}
          {detailError && <div className="alert error">{detailError}</div>}
          {detail && (
            <div className="app-list">
              {detail.per_question?.length === 0 && (
                <p className="muted">
                  This attempt was never submitted, so there is no review to show.
                </p>
              )}
              {detail.per_question?.map((row, index) => (
                <div
                  className={`card card-sheet review-item ${row.is_correct ? 'ok' : 'bad'}`}
                  key={row.question_id ?? index}
                >
                  <div className="page-head">
                    <span className="review-q">
                      Q{index + 1}. {row.text}
                    </span>
                    <span className={`score-tag ${row.is_correct ? 'ok' : 'bad'}`}>
                      {row.is_correct ? 'Correct' : 'Incorrect'}
                    </span>
                  </div>
                  <p className="muted small">
                    Answered: {optionText(row, row.chosen_index)} · Correct answer:{' '}
                    {optionText(row, row.correct_index)}
                  </p>
                  {row.explanation && (
                    <p className="remarks-row">{row.explanation}</p>
                  )}
                </div>
              ))}
            </div>
          )}
          <p className="back-link">
            <Link to="/admin">Back to admin dashboard</Link>
          </p>
        </div>
      )}
    </div>
  )
}
