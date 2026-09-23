import { useCallback, useEffect, useState } from 'react'
import { apiError } from '../../api/client'
import {
  answerInterview,
  fetchMyInterviews,
  startInterview,
} from '../../api/interviews'

const PRESET_ROLES = [
  'Python Developer',
  'Django Backend Developer',
  'Frontend React Developer',
  'Full Stack Developer',
  'Data Analyst',
  'Machine Learning Engineer',
]

function ScoreTag({ score }) {
  const cls = score >= 70 ? 'ok' : score >= 40 ? 'warn' : 'bad'
  return <span className={`score-tag ${cls}`}>{score}/100</span>
}

function TurnRow({ turn }) {
  if (turn.kind === 'question') {
    return (
      <div className="card interview-turn q">
        <p className="muted small">Interviewer</p>
        <p className="summary">{turn.content}</p>
      </div>
    )
  }
  if (turn.kind === 'answer') {
    return (
      <div className="card interview-turn a">
        <p className="muted small">You</p>
        <p className="summary">{turn.content}</p>
      </div>
    )
  }
  return (
    <div className="card interview-turn e">
      <p className="muted small">Feedback</p>
      {turn.score !== null && <ScoreTag score={turn.score} />}
      <p className="summary">{turn.content}</p>
      {turn.suggestions && <p className="muted small">Tip: {turn.suggestions}</p>}
    </div>
  )
}

export default function Interview() {
  const [position, setPosition] = useState('')
  const [total, setTotal] = useState(5)
  const [starting, setStarting] = useState(false)
  const [session, setSession] = useState(null)
  const [turns, setTurns] = useState([])
  const [answer, setAnswer] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const [history, setHistory] = useState([])

  const loadHistory = useCallback(() => {
    fetchMyInterviews().then(setHistory).catch(() => {})
  }, [])

  useEffect(() => {
    loadHistory()
  }, [loadHistory])

  const onStart = async () => {
    setError('')
    setStarting(true)
    try {
      const data = await startInterview({ position, total_questions: total })
      setSession(data)
      setTurns(data.turns)
    } catch (e) {
      setError(apiError(e, 'Could not start interview'))
    } finally {
      setStarting(false)
    }
  }

  const onSubmit = async () => {
    setError('')
    setSending(true)
    try {
      const res = await answerInterview(session.id, answer)
      if (res.completed) {
        setTurns([
          ...turns,
          { kind: 'answer', content: answer },
          { kind: 'evaluation', ...res.evaluation },
        ])
        setSession({ ...session, report: res.report, status: 'completed' })
      } else {
        setTurns([
          ...turns,
          { kind: 'answer', content: answer },
          { kind: 'evaluation', ...res.evaluation },
          { kind: 'question', content: res.next_question },
        ])
      }
      setAnswer('')
      loadHistory()
    } catch (e) {
      setError(apiError(e, 'Could not submit answer'))
    } finally {
      setSending(false)
    }
  }

  const done = session?.status === 'completed'
  const answeredQuestions = turns.filter((t) => t.kind === 'question').length
  const currentNumber = done ? answeredQuestions : Math.max(answeredQuestions, 1)

  if (!session) {
    return (
      <div className="page">
        <h1>AI mock interview</h1>
        <p className="muted">
          Practice with an AI interviewer. Answer each question honestly; you get
          per-answer feedback and a final report.
        </p>
        {error && <div className="alert error">{error}</div>}
        <div className="card card-sheet" style={{ display: 'grid', gap: 14 }}>
          <label>
            Target role
            <input
              list="preset-roles"
              placeholder="e.g. Python Developer"
              value={position}
              onChange={(e) => setPosition(e.target.value)}
            />
          </label>
          <datalist id="preset-roles">
            {PRESET_ROLES.map((r) => <option key={r} value={r} />)}
          </datalist>
          <label>
            Number of questions (1–10)
            <input type="number" min={1} max={10} value={total}
              onChange={(e) => setTotal(e.target.value)} />
          </label>
          <button className="btn btn-primary" onClick={onStart} disabled={starting || !position.trim()}>
            {starting ? 'Starting…' : 'Start interview'}
          </button>
        </div>

        {history.length > 0 && (
          <>
            <h2 className="section-title">Past interviews</h2>
            <div className="app-table-wrap">
              <table className="app-table">
                <thead>
                  <tr><th>Role</th><th>Status</th><th>Questions</th><th>Date</th></tr>
                </thead>
                <tbody>
                  {history.map((h) => (
                    <tr key={h.id}>
                      <td>{h.position}</td>
                      <td><span className={`badge ${h.status === 'completed' ? 'analyzed' : h.status === 'aborted' ? 'failed' : 'processing'}`}>{h.status}</span></td>
                      <td>{h.question_index}/{h.total_questions}</td>
                      <td>{new Date(h.created_at).toLocaleDateString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    )
  }

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>{session.position}</h1>
          <p className="muted">
            Question {currentNumber} of {session.total_questions}
          </p>
        </div>
        <button className="btn btn-ghost" onClick={() => { setSession(null); setTurns([]); setAnswer('') }}>
          New interview
        </button>
      </div>
      {error && <div className="alert error">{error}</div>}

      <div className="interview-thread">
        {turns.map((t, i) => <TurnRow key={i} turn={t} />)}

        {!done && (
          <>
            <div className="card interview-turn a">
              <label>
                Your answer
                <textarea
                  rows={5}
                  placeholder="Type your answer here…"
                  value={answer}
                  onChange={(e) => setAnswer(e.target.value)}
                />
              </label>
            </div>
            <button className="btn btn-primary" onClick={onSubmit} disabled={sending || !answer.trim()}>
              {sending ? 'Submitting…' : 'Submit answer'}
            </button>
          </>
        )}
      </div>

      {done && (
        <div className="card result-card">
          <h2>Interview complete</h2>
          <p className="summary" style={{ color: 'var(--text)' }}>{session.report}</p>
        </div>
      )}
    </div>
  )
}