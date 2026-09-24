import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { apiError } from '../../api/client'
import { startQuiz, submitQuiz } from '../../api/quizzes'

function formatSeconds(total) {
  const m = String(Math.floor(total / 60)).padStart(2, '0')
  const s = String(total % 60).padStart(2, '0')
  return `${m}:${s}`
}

function Confirmation({ onConfirm, onCancel }) {
  const [seconds, setSeconds] = useState(5)
  useEffect(() => {
    if (seconds === 0) return
    const t = setTimeout(() => setSeconds((v) => v - 1), 1000)
    return () => clearTimeout(t)
  }, [seconds])
  return (
    <div className="card">
      <h2>Submit quiz?</h2>
      <p className="muted">Your score will be frozen once submitted.</p>
      <div className="job-actions">
        <button className="btn btn-primary" onClick={onConfirm} disabled={seconds > 0}>
          {seconds > 0 ? `Confirm in ${seconds}s` : 'Confirm submit'}
        </button>
        <button className="btn btn-ghost" onClick={onCancel}>Keep going</button>
      </div>
    </div>
  )
}

export default function QuizAttempt() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [confirming, setConfirming] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [idx, setIdx] = useState(0)
  const [answers, setAnswers] = useState({})
  const [timeLeft, setTimeLeft] = useState(null)
  const doneRef = useRef(false)

  useEffect(() => {
    let cancelled = false
    startQuiz(id)
      .then((res) => {
        if (cancelled) return
        setData(res)
        if (typeof res.countdown_seconds === 'number') setTimeLeft(res.countdown_seconds)
      })
      .catch((e) => {
        const msg = apiError(e, 'Could not start quiz')
        if (/already completed/i.test(msg)) {
          navigate(`/student/quizzes/${id}/result`, { replace: true })
          return
        }
        if (cancelled) return
        setError(msg)
      })
    return () => {
      cancelled = true
    }
  }, [id, navigate])

  const goToResult = useCallback((attemptId) => {
    navigate(`/student/quizzes/${id}/result?attempt=${attemptId}`, { replace: true })
  }, [id, navigate])

  const submit = useCallback(async () => {
    if (doneRef.current || !data) return
    doneRef.current = true
    setSubmitting(true)
    try {
      const result = await submitQuiz(data.quiz.id, answers)
      goToResult(result.attempt_id)
    } catch (e) {
      const msg = apiError(e, 'Could not submit')
      const attemptId = e?.response?.data?.attempt_id
      doneRef.current = false
      setSubmitting(false)
      if (attemptId) {
        goToResult(attemptId)
        return
      }
      alert(msg)
    }
  }, [answers, data, goToResult])

  useEffect(() => {
    if (timeLeft === null || !data) return
    if (timeLeft <= 0) {
      submit()
      return
    }
    const t = setTimeout(() => setTimeLeft((v) => v - 1), 1000)
    return () => clearTimeout(t)
  }, [timeLeft, data, submit])

  if (error) {
    return (
      <div className="page">
        <div className="alert error">{error}</div>
        <button className="btn btn-primary" onClick={() => navigate(`/student/quizzes/${id}`)}>
          Back to quiz
        </button>
      </div>
    )
  }

  if (!data) {
    return <div className="page-loading">Preparing quiz…</div>
  }

  if (confirming) {
    return (
      <div className="page">
        <Confirmation
          onConfirm={submit}
          onCancel={() => setConfirming(false)}
        />
      </div>
    )
  }

  const { quiz, questions } = data
  const q = questions[idx]
  const answeredCount = Object.keys(answers).length

  const pick = (optIdx) => setAnswers((prev) => ({ ...prev, [q.id]: optIdx }))

  return (
    <div className="page">
      <div className="quiz-attempt-head">
        <div>
          <h2>{quiz.title}</h2>
          <p className="muted">
            Question {idx + 1} of {questions.length} · {answeredCount}/{questions.length} answered
          </p>
        </div>
        {timeLeft !== null && <div className="timer">{formatSeconds(timeLeft)}</div>}
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
          <button className="btn btn-primary" onClick={() => setConfirming(true)} disabled={submitting}>
            {submitting ? 'Submitting…' : 'Review & submit'}
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
        <button
          className="btn btn-danger"
          onClick={() => navigate(`/student/quizzes/${id}`)}
          disabled={submitting}
        >
          Quit attempt
        </button>
      </div>
    </div>
  )
}