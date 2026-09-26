import { useCallback, useEffect, useState } from 'react'
import { apiError } from '../../api/client'
import {
  answerInterview,
  cancelInterview,
  completeInterview,
  fetchActiveInterview,
  fetchMyInterviews,
  startInterview,
} from '../../api/interviews'
import { speechRecognitionSupported, speechSynthesisSupported, UNSUPPORTED_MESSAGE } from '../../lib/speech'
import InterviewReport from '../../components/interviews/InterviewReport'
import VoiceInterviewPanel from '../../components/interviews/VoiceInterviewPanel'

const PRESET_ROLES = [
  'Python Developer',
  'Django Backend Developer',
  'Frontend React Developer',
  'Full Stack Developer',
  'Data Analyst',
  'Machine Learning Engineer',
]

const STATUS_BADGE = {
  completed: 'analyzed',
  cancelled: 'failed',
  aborted: 'failed',
  in_progress: 'processing',
}

export default function Interview() {
  const [position, setPosition] = useState('')
  const [job, setJob] = useState('')
  const [total, setTotal] = useState(5)
  const [starting, setStarting] = useState(false)
  const [session, setSession] = useState(null)
  const [error, setError] = useState('')
  const [history, setHistory] = useState([])
  const [active, setActive] = useState(null)
  const [report, setReport] = useState(null)
  const [mode, setMode] = useState('voice')

  const loadHistory = useCallback(() => {
    fetchMyInterviews().then(setHistory).catch(() => {})
  }, [])

  // On mount: restore an in-progress interview so a browser refresh never loses
  // the session, and offer "Resume interview" instead of forcing a new one.
  useEffect(() => {
    loadHistory()
    fetchActiveInterview()
      .then((data) => setActive(data || null))
      .catch(() => {})
  }, [loadHistory])

  const onStart = async () => {
    setError('')
    setStarting(true)
    try {
      const data = await startInterview({
        position,
        total_questions: total,
        job: job ? Number(job) : null,
        mode,
      })
      setSession(data)
      setReport(null)
      setActive(null)
      loadHistory()
    } catch (e) {
      setError(apiError(e, 'Could not start interview'))
    } finally {
      setStarting(false)
    }
  }

  const onResume = async () => {
    setError('')
    setStarting(true)
    try {
      const data = await startInterview({ position: active.position, resume: true })
      setSession(data)
      setReport(null)
      loadHistory()
    } catch (e) {
      setError(apiError(e, 'Could not resume interview'))
    } finally {
      setStarting(false)
    }
  }

  const onAnswered = async (text, token) => {
    const res = await answerInterview(session.id, text, token)
    setSession(res.session)
    loadHistory()
    return res
  }

  const onCompleted = async (fallbackReport) => {
    const finalReport = fallbackReport || (await completeInterview(session.id).catch(() => null))?.report
    setReport(finalReport)
    setSession((current) => ({ ...current, status: 'completed' }))
    setActive(null)
    loadHistory()
  }

  const onEnd = async () => {
    setError('')
    try {
      const res = await completeInterview(session.id)
      setReport(res.report || null)
      setSession((current) => ({ ...current, status: res.session?.status || 'completed' }))
    } catch (e) {
      setError(apiError(e, 'Could not finish the interview'))
    }
    setActive(null)
    loadHistory()
  }

  const onCancel = async () => {
    await cancelInterview(session.id).catch(() => {})
    setSession(null)
    fetchActiveInterview().then((data) => setActive(data || null)).catch(() => {})
    loadHistory()
  }

  const voiceOk = speechRecognitionSupported()

  // ---------------- Live interview ----------------
  if (session) {
    return (
      <div className="page">
        {error && <div className="alert error">{error}</div>}
        <VoiceInterviewPanel
          session={session}
          onAnswered={onAnswered}
          onCompleted={onCompleted}
          onEnd={onEnd}
        />
        {session.status !== 'in_progress' && (
          <>
            <div className="voice-controls">
              <button className="btn btn-ghost" onClick={() => { setSession(null); setReport(null); loadHistory() }}>
                Back to interviews
              </button>
              <button className="btn btn-ghost" onClick={onCancel}>Discard this interview</button>
            </div>
            {report && <InterviewReport report={report} position={session.position} />}
          </>
        )}
      </div>
    )
  }

  // ---------------- Setup / history ----------------
  return (
    <div className="page">
      <h1>AI mock interview</h1>
      <p className="muted">
        A real-time, voice-based mock interview. The AI interviewer asks a question out
        loud, you answer by speaking, and it evaluates your answer before choosing the
        next question.
      </p>

      {error && <div className="alert error">{error}</div>}

      {active && (
        <div className="card card-sheet resume-interview">
          <div className="page-head">
            <div>
              <h2>Interview in progress</h2>
              <p className="muted">
                {active.position} · {active.answered_count ?? 0}/{active.total_questions} answered
                {' · '}
                {active.mode === 'voice' ? 'voice mode' : 'text mode'}
              </p>
            </div>
            <button className="btn btn-primary" onClick={onResume} disabled={starting}>
              {starting ? 'Resuming…' : 'Resume interview'}
            </button>
          </div>
          {active.current_question && (
            <p className="muted small">Next question: “{active.current_question.content}”</p>
          )}
        </div>
      )}

      <div className="card card-sheet" style={{ display: 'grid', gap: 14 }}>
        <h2 className="section-title">Start a new interview</h2>
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
          Job posting id (optional)
          <input
            type="number"
            min={1}
            placeholder="Paste a job id to tailor questions to its required skills"
            value={job}
            onChange={(e) => setJob(e.target.value)}
          />
        </label>
        <label>
          Number of questions (1–10)
          <input
            type="number"
            min={1}
            max={10}
            value={total}
            onChange={(e) => setTotal(e.target.value)}
          />
        </label>
        <label>
          Interview mode
          <select value={mode} onChange={(e) => setMode(e.target.value)}>
            <option value="voice">Voice (speak and listen)</option>
            <option value="text">Text only</option>
          </select>
        </label>

        {!voiceOk && <div className="alert warn">{UNSUPPORTED_MESSAGE}</div>}
        {mode === 'voice' && !speechSynthesisSupported() && (
          <div className="alert warn">
            This browser cannot read questions aloud, so they will appear as text only.
          </div>
        )}

        <button
          className="btn btn-primary"
          onClick={onStart}
          disabled={starting || !position.trim() || Boolean(active)}
        >
          {starting ? 'Starting…' : 'Start interview'}
        </button>
        {active && (
          <p className="muted small">
            Finish or discard the interview in progress before starting a new one.
          </p>
        )}
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
                    <td>
                      <span className={`badge ${STATUS_BADGE[h.status] || 'processing'}`}>
                        {String(h.status || '').replace('_', ' ')}
                      </span>
                    </td>
                    <td>{h.answered_count ?? h.question_index}/{h.total_questions}</td>
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
