import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiError } from '../../api/client'
import { fetchQuizzes } from '../../api/quizzes'
import { plural } from '../../lib/format'
import { categoryLabel } from '../../lib/labels'

const DIFFS = [
  { value: 'all', label: 'All' },
  { value: 'easy', label: 'Easy' },
  { value: 'medium', label: 'Medium' },
  { value: 'hard', label: 'Hard' },
]

export default function QuizList() {
  const [quizzes, setQuizzes] = useState([])
  const [error, setError] = useState('')
  const [diff, setDiff] = useState('all')

  const load = useCallback(() => {
    // The error is cleared when fresh data lands rather than before the
    // request, so the effect that loads on mount does not set state
    // synchronously and trigger a second render pass for nothing.
    fetchQuizzes()
      .then((rows) => {
        setQuizzes(rows)
        setError('')
      })
      .catch((e) => setError(apiError(e)))
  }, [])

  useEffect(() => {
    load()
  }, [load])

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Skill quizzes</h1>
          <p className="muted">
            Test your technical and aptitude readiness. Each quiz allows one attempt; pass mark is 60%.
          </p>
        </div>
        <Link to="/student/quizzes/history" className="btn btn-ghost">
          My attempts
        </Link>
      </div>
      {error && <div className="alert error">{error}</div>}
      <div className="filters" style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 14 }}>
        <label style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          Difficulty
          <select value={diff} onChange={(e) => setDiff(e.target.value)}>
            {DIFFS.map((d) => <option key={d.value} value={d.value}>{d.label}</option>)}
          </select>
        </label>
      </div>
      <div className="job-list">
        {quizzes
          .filter((qz) => diff === 'all' || qz.difficulty === diff)
          .map((qz) => (
          <div key={qz.id} className="card quiz-card">
            <div className="job-head">
              <div>
                <h3>
                  <Link to={`/student/quizzes/${qz.id}`}>{qz.title}</Link>
                </h3>
                <p className="muted">
                  {categoryLabel(qz.category)} · {qz.difficulty} · {plural(qz.total_questions, 'question')} ·{' '}
                  {qz.duration_minutes ? `${qz.duration_minutes} min` : 'No time limit'}
                </p>
              </div>
              {qz.attempted && qz.status === 'completed' && (
                <span className={`score-tag ${qz.score_percent >= 60 ? 'ok' : 'bad'}`}>
                  {qz.score_percent}%
                </span>
              )}
            </div>
            <span className={`chip quiz-cat ${qz.category}`}>{categoryLabel(qz.category)}</span>
            <p className="summary">{qz.description}</p>
            <div className="job-actions">
              <Link
                to={`/student/quizzes/${qz.id}`}
                className="btn btn-primary btn-sm"
              >
                {qz.attempted && qz.status === 'completed' ? 'View result' : qz.attempted && qz.status === 'in_progress' ? 'Resume' : 'Take quiz'}
              </Link>
            </div>
          </div>
        ))}
        {quizzes.filter((qz) => diff === 'all' || qz.difficulty === diff).length === 0 && <p className="muted">No quizzes match this filter.</p>}
      </div>
    </div>
  )
}