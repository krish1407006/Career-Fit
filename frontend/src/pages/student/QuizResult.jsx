import { useEffect, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { apiError } from '../../api/client'
import { fetchAttempt, fetchQuizzes } from '../../api/quizzes'
import { categoryLabel } from './QuizList'

function ReviewRow({ r }) {
  const chosen = r.chosen_index
  const chosenText = chosen === null ? '—' : (r.options[chosen] ?? '—')
  return (
    <div className={`card review-item ${r.is_correct ? 'ok' : 'bad'}`}>
      <p className="review-q">
        <span className={`badge ${r.is_correct ? 'ok' : 'bad'}`}>
          {r.is_correct ? 'Correct' : r.chosen_index === null ? 'Not answered' : 'Incorrect'}
        </span>
        {r.text}
      </p>
      <p className="muted small">Your answer: {chosenText}</p>
      {!r.is_correct && <p className="muted small">Correct answer: {r.options[r.correct_index]}</p>}
      {r.explanation && <p className="small">{r.explanation}</p>}
    </div>
  )
}

export default function QuizResult() {
  const { id } = useParams()
  const [params] = useSearchParams()
  const [attempt, setAttempt] = useState(null)
  const [error, setError] = useState('')
  const [missing, setMissing] = useState(false)

  useEffect(() => {
    let cancelled = false
    const paramId = params.get('attempt')
    const load = async () => {
      try {
        if (paramId) {
          const data = await fetchAttempt(paramId)
          if (cancelled) return
          setAttempt(data)
          return
        }
        const rows = await fetchQuizzes()
        const mine = rows.find((q) => String(q.id) === String(id))
        if (mine?.attempt_id) {
          const data = await fetchAttempt(mine.attempt_id)
          if (cancelled) return
          setAttempt(data)
        } else {
          setMissing(true)
        }
      } catch (e) {
        if (!cancelled) setError(apiError(e, 'Could not load result'))
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [id, params])

  if (missing) {
    return (
      <div className="page">
        <p className="muted">You haven’t attempted this quiz yet.</p>
        <Link to={`/student/quizzes/${id}`} className="btn btn-primary">Take quiz</Link>
      </div>
    )
  }

  if (error) {
    return (
      <div className="page">
        <div className="alert error">{error}</div>
        <Link to="/student/quizzes" className="btn btn-ghost">Back to quizzes</Link>
      </div>
    )
  }

  if (!attempt) {
    return <div className="page-loading">Loading result…</div>
  }

  const cls = attempt.passed ? 'ok' : 'bad'

  return (
    <div className="page">
      <div className="card result-card">
        <div className={`result-score ${cls}`}>
          <span className="score-big">{attempt.score_percent}%</span>
          <span className={`badge ${cls}`}>
            {attempt.passed ? 'Passed' : 'Needs practice'}
          </span>
        </div>
        <h2>{attempt.quiz_title}</h2>
        <p className="muted">
          {categoryLabel(attempt.quiz_category)} · {attempt.quiz_difficulty}
        </p>
        <p className="muted">
          Scored {attempt.correct_count} correct, {attempt.incorrect_count} incorrect of {attempt.total}.
        </p>
      </div>

      <h2 className="section-title">Review</h2>
      {attempt.per_question?.length ? (
        attempt.per_question.map((r) => <ReviewRow key={r.question_id} r={r} />)
      ) : (
        <p className="muted">No per-question review available.</p>
      )}

      <div className="job-actions">
        <Link to="/student/quizzes" className="btn btn-primary">Back to quizzes</Link>
        <Link to="/student/quizzes/history" className="btn btn-ghost">My attempts</Link>
      </div>
    </div>
  )
}