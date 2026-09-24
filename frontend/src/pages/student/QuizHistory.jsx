import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiError } from '../../api/client'
import { fetchMyAttempts } from '../../api/quizzes'
import { categoryLabel } from './QuizList'

export default function QuizHistory() {
  const [attempts, setAttempts] = useState([])
  const [error, setError] = useState('')

  const load = useCallback(() => {
    setError('')
    fetchMyAttempts().then(setAttempts).catch((e) => setError(apiError(e)))
  }, [])

  useEffect(() => {
    load()
  }, [load])

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>My attempts</h1>
          <p className="muted">Review your past quiz results.</p>
        </div>
        <Link to="/student/quizzes" className="btn btn-ghost">Back to quizzes</Link>
      </div>
      {error && <div className="alert error">{error}</div>}
      {attempts.length ? (
        <div className="app-table-wrap">
          <table className="app-table">
            <thead>
              <tr><th>Quiz</th><th>Category</th><th>Score</th><th>Status</th><th>Submitted</th><th /></tr>
            </thead>
            <tbody>
              {attempts.map((a) => {
                const done = a.status === 'completed' && a.submitted_at
                return (
                  <tr key={a.id}>
                    <td>{a.quiz_title}</td>
                    <td>{categoryLabel(a.quiz_category)}</td>
                    <td>{done ? `${a.score_percent}% (${a.correct_count}/${a.total})` : '—'}</td>
                    <td>
                      <span className={`badge ${done ? (a.score_percent >= 60 ? 'analyzed' : 'failed') : 'neutral'}`}>
                        {done ? (a.score_percent >= 60 ? 'Passed' : 'Failed') : 'In progress'}
                      </span>
                    </td>
                    <td>{done ? new Date(a.submitted_at).toLocaleString() : '—'}</td>
                    <td>
                      {done ? (
                        <Link to={`/student/quizzes/${a.quiz}/result?attempt=${a.id}`}>
                          View
                        </Link>
                      ) : (
                        <Link to={`/student/quizzes/${a.quiz}/attempt`}>Resume</Link>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="muted">You haven’t attempted any quizzes yet.</p>
      )}
    </div>
  )
}