import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { apiError } from '../../api/client'
import { fetchQuizzes, fetchQuiz, startQuiz } from '../../api/quizzes'
import { categoryLabel } from './QuizList'

export default function QuizDetails() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [quiz, setQuiz] = useState(null)
  const [row, setRow] = useState(null)
  const [error, setError] = useState('')
  const [starting, setStarting] = useState(false)

  const load = useCallback(() => {
    setError('')
    fetchQuiz(id).then(setQuiz).catch((e) => setError(apiError(e)))
    fetchQuizzes()
      .then((rows) => setRow(rows.find((q) => String(q.id) === String(id)) || null))
      .catch(() => {})
  }, [id])

  useEffect(() => {
    load()
  }, [load])

  const onStart = async () => {
    setError('')
    setStarting(true)
    try {
      await startQuiz(quiz.id)
      navigate(`/student/quizzes/${quiz.id}/attempt`)
    } catch (e) {
      const msg = apiError(e, 'Could not start quiz')
      if (/already completed/i.test(msg)) {
        const attempts = await fetchQuizzes().catch(() => [])
        const mine = attempts.find((q) => String(q.id) === String(quiz.id))
        if (mine?.attempt_id) {
          navigate(`/student/quizzes/${quiz.id}/result?attempt=${mine.attempt_id}`)
          return
        }
      }
      setError(msg)
      setStarting(false)
    }
  }

  if (error && !quiz) {
    return (
      <div className="page">
        <div className="alert error">{error}</div>
        <Link to="/student/quizzes" className="btn btn-ghost">Back to quizzes</Link>
      </div>
    )
  }

  if (!quiz) {
    return <div className="page-loading">Loading…</div>
  }

  const attempted = Boolean(row?.attempted && row?.attempt_id)

  return (
    <div className="page">
      <Link to="/student/quizzes" className="btn btn-ghost">← Back to quizzes</Link>
      {error && <div className="alert error">{error}</div>}
      <h1>{quiz.title}</h1>
      <p className="muted">
        {categoryLabel(quiz.category)} · {quiz.difficulty} · {quiz.total_questions} questions ·{' '}
        {quiz.duration_minutes ? `${quiz.duration_minutes} minutes` : 'No time limit'}
      </p>
      <div className="card">
        <p>{quiz.description}</p>
        <ul className="muted small">
          <li>One attempt allowed per quiz.</li>
          <li>Pass mark is 60%.</li>
          {quiz.duration_minutes && <li>Timer starts as soon as you begin.</li>}
        </ul>
        <div className="job-actions">
          {attempted ? (
            <Link
              to={`/student/quizzes/${quiz.id}/result?attempt=${row.attempt_id}`}
              className="btn btn-primary"
            >
              View result ({(row.score_percent ?? 0)}%)
            </Link>
          ) : (
            <button className="btn btn-primary" onClick={onStart} disabled={starting}>
              {starting ? 'Starting…' : 'Start quiz'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}