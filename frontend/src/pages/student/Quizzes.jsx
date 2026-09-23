import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { apiError } from '../../api/client'
import { fetchMyAttempts, fetchQuizzes, startQuiz, submitQuiz } from '../../api/quizzes'

function CategoryTag({ category }) {
  return <span className={`chip quiz-cat ${category}`}>{category}</span>
}

function formatSeconds(total) {
  const m = String(Math.floor(total / 60)).padStart(2, '0')
  const s = String(total % 60).padStart(2, '0')
  return `${m}:${s}`
}

function Attempt({ data, onDone, onQuit }) {
  const [idx, setIdx] = useState(0)
  const [answers, setAnswers] = useState({})
  const [timeLeft, setTimeLeft] = useState(data.countdown_seconds)
  const [submitting, setSubmitting] = useState(false)
  const doneRef = useRef(false)

  const submit = useCallback(async () => {
    if (doneRef.current) return
    doneRef.current = true
    setSubmitting(true)
    try {
      const result = await submitQuiz(data.attempt_id, answers)
      onDone(result)
    } catch (e) {
      doneRef.current = false
      setSubmitting(false)
      alert(apiError(e, 'Could not submit'))
    }
  }, [answers, data.attempt_id, onDone])

  useEffect(() => {
    if (timeLeft <= 0) {
      submit()
      return
    }
    const t = setTimeout(() => setTimeLeft((v) => v - 1), 1000)
    return () => clearTimeout(t)
  }, [timeLeft, submit])

  const questions = data.questions
  const q = questions[idx]
  const answeredCount = Object.keys(answers).length

  const pick = (optIdx) =>
    setAnswers((prev) => ({ ...prev, [q.id]: optIdx }))

  return (
    <div>
      <div className="quiz-attempt-head">
        <div>
          <h2>{data.quiz.title}</h2>
          <p className="muted">
            Question {idx + 1} of {questions.length} · {answeredCount}/{questions.length} answered
          </p>
        </div>
        <div className="timer">{formatSeconds(timeLeft)}</div>
      </div>

      <div className="card quiz-question">
        <h3>{q.text}</h3>
        <div className="options">
          {q.options.map((opt, i) => {
            const selected = answers[q.id] === i
            return (
              <button
                key={i}
                className={`option ${selected ? 'selected' : ''}`}
                onClick={() => pick(i)}
              >
                <span className="option-key">{String.fromCharCode(65 + i)}</span>
                {opt}
              </button>
            )
          })}
        </div>
      </div>

      <div className="quiz-nav">
        <button
          className="btn btn-ghost"
          onClick={() => setIdx((i) => Math.max(0, i - 1))}
          disabled={idx === 0}
        >
          Previous
        </button>
        {idx < questions.length - 1 ? (
          <button className="btn btn-primary" onClick={() => setIdx((i) => i + 1)}>
            Next
          </button>
        ) : (
          <button className="btn btn-primary" onClick={submit} disabled={submitting}>
            {submitting ? 'Submitting…' : 'Submit quiz'}
          </button>
        )}
      </div>

      <div className="progress-dots">
        {questions.map((qq, i) => (
          <button
            key={qq.id}
            className={`dot ${i === idx ? 'current' : ''} ${answers[qq.id] !== undefined ? 'answered' : ''}`}
            onClick={() => setIdx(i)}
            title={`Question ${i + 1}`}
          />
        ))}
      </div>

      <div className="quiz-nav">
        <button className="btn btn-danger" onClick={onQuit} disabled={submitting}>
          Quit attempt
        </button>
      </div>
    </div>
  )
}

function Results({ result, title, onBack }) {
  const cls = result.passed ? 'ok' : 'bad'
  return (
    <div>
      <div className="card result-card">
        <div className={`result-score ${cls}`}>
          <span className="score-big">{result.score_percent}%</span>
          <span className={`badge ${cls}`}>
            {result.passed ? 'Passed' : 'Needs practice'}
          </span>
        </div>
        <h2>{title}</h2>
        <p className="muted">
          Scored {result.correct_count} of {result.total} questions correctly.
        </p>
      </div>

      <h2 className="section-title">Review</h2>
      {result.per_question.map((r) => {
        const q = result._questions?.find((qq) => qq.id === r.question_id)
        return (
          <div key={r.question_id} className={`card review-item ${r.is_correct ? 'ok' : 'bad'}`}>
            <p className="review-q">
              <span className={`badge ${r.is_correct ? 'ok' : 'bad'}`}>
                {r.is_correct ? 'Correct' : 'Incorrect'}
              </span>
              {q?.text}
            </p>
            {q && (
              <p className="muted small">
                Your answer: {q.options[r.your_index] ?? '—'} · Correct:{' '}
                {q.options[r.correct_index]}
              </p>
            )}
            <p className="small">{r.explanation}</p>
          </div>
        )
      })}

      <button className="btn btn-primary" onClick={onBack}>Back to quizzes</button>
    </div>
  )
}

export default function Quizzes() {
  const [quizzes, setQuizzes] = useState([])
  const [attempts, setAttempts] = useState([])
  const [error, setError] = useState('')
  const [active, setActive] = useState(null) // { attempt, questions } while taking
  const [result, setResult] = useState(null)
  const [lastQuestions, setLastQuestions] = useState([])
  const [lastTitle, setLastTitle] = useState('')

  const load = useCallback(() => {
    setError('')
    fetchQuizzes().then(setQuizzes).catch((e) => setError(apiError(e)))
    fetchMyAttempts().then(setAttempts).catch(() => {})
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const onStart = async (quiz) => {
    setError('')
    try {
      const data = await startQuiz(quiz.id)
      setResult(null)
      setLastTitle(data.quiz.title)
      setActive(data)
    } catch (e) {
      setError(apiError(e, 'Could not start quiz'))
    }
  }

  const onDone = (resultData) => {
    setLastQuestions(active.questions)
    setActive(null)
    setResult(resultData)
    load()
  }

  const memo = useMemo(() => ({
    ...(result || {}),
    _questions: lastQuestions,
  }), [result, lastQuestions])

  if (active && !result) {
    return (
      <div className="page">
        <Attempt
          data={active}
          onDone={onDone}
          onQuit={() => { setActive(null); setResult(null) }}
        />
      </div>
    )
  }

  if (result) {
    return (
      <div className="page">
        <Results
          result={memo}
          title={lastTitle}
          onBack={() => setResult(null)}
        />
      </div>
    )
  }

  return (
    <div className="page">
      <h1>Skill quizzes</h1>
      <p className="muted">
        Test your technical and aptitude readiness. Each quiz allows one attempt; pass mark is 60%.
      </p>
      {error && <div className="alert error">{error}</div>}
      <div className="job-list">
        {quizzes.map((qz) => (
          <div key={qz.id} className="card quiz-card">
            <div className="job-head">
              <div>
                <h3>{qz.title}</h3>
                <p className="muted">
                  {qz.category === 'aptitude' ? 'Aptitude' : qz.category === 'core' ? 'Core CS' : 'Technical'} ·{' '}
                  {qz.total_questions} questions · {qz.duration_minutes} min
                </p>
              </div>
              {qz.attempted && (
                <span className={`score-tag ${qz.score_percent >= 60 ? 'ok' : 'bad'}`}>
                  {qz.score_percent}%
                </span>
              )}
            </div>
            <CategoryTag category={qz.category} />
            <p className="summary">{qz.description}</p>
            <div className="job-actions">
              {qz.attempted && qz.attempt_id ? (
                <span className="badge analyzed">Attempted</span>
              ) : null}
              <button
                className="btn btn-primary btn-sm"
                onClick={() => onStart(qz)}
                disabled={qz.attempted}
              >
                {qz.attempted ? 'Completed' : 'Take quiz'}
              </button>
            </div>
          </div>
        ))}
        {!quizzes.length && <p className="muted">No quizzes available yet.</p>}
      </div>

      <h2 className="section-title">My attempts</h2>
      {attempts.length ? (
        <div className="app-table-wrap">
          <table className="app-table">
            <thead>
              <tr><th>Quiz</th><th>Category</th><th>Score</th><th>Status</th><th>Submitted</th></tr>
            </thead>
            <tbody>
              {attempts.map((a) => (
                <tr key={a.id}>
                  <td>{a.quiz_title}</td>
                  <td>{a.quiz_category}</td>
                  <td>{a.score_percent}% ({a.correct_count}/{a.total})</td>
                  <td>
                    <span className={`badge ${a.score_percent >= 60 ? 'analyzed' : 'failed'}`}>
                      {a.score_percent >= 60 ? 'Passed' : 'Failed'}
                    </span>
                  </td>
                  <td>{a.submitted_at ? new Date(a.submitted_at).toLocaleString() : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="muted">You haven’t attempted any quizzes yet.</p>
      )}
    </div>
  )
}