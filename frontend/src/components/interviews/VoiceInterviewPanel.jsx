import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { apiError } from '../../api/client'
import { useSpeechRecognition } from '../../hooks/useSpeechRecognition'
import { useSpeechSynthesis } from '../../hooks/useSpeechSynthesis'
import { isUsableTranscript, makeClientToken, TTS_UNSUPPORTED_MESSAGE, UNSUPPORTED_MESSAGE } from '../../lib/speech'

/**
 * Real-time voice interview stage.
 *
 * Conversation state machine (the student can always see whose turn it is):
 *
 *   preparing -> ai_speaking -> awaiting_answer (your turn)
 *              -> listening -> processing -> evaluating -> next question -> ...
 *              -> completed
 *
 * Nothing records the microphone until the student presses the mic button, and
 * no answer is submitted without an explicit "Submit answer". Raw audio is never
 * uploaded or stored: only the recognised transcript goes to the backend.
 */

const STATE_LABEL = {
  preparing: 'Preparing interview',
  ai_speaking: 'AI is speaking',
  awaiting_answer: 'Your turn',
  listening: 'Listening',
  processing: 'Processing answer',
  evaluating: 'AI is evaluating',
  completed: 'Interview completed',
}

export default function VoiceInterviewPanel({ session, onAnswered, onCompleted, onEnd }) {
  const [stage, setStage] = useState('ai_speaking')
  const [question, setQuestion] = useState(session?.current_question?.content || '')
  const category = session?.current_question?.category || ''
  const [transcript, setTranscript] = useState('')
  const [typed, setTyped] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [questionNumber, setQuestionNumber] = useState(
    (session?.question_index || 0) + 1,
  )
  const [total, setTotal] = useState(session?.total_questions || 5)
  const [spokeCurrent, setSpokeCurrent] = useState(false)
  const tokenRef = useRef('')
  const spokenIdsRef = useRef(new Set())

  const tts = useSpeechSynthesis()
  const stt = useSpeechRecognition({
    onFinal: (text) => {
      setTranscript(text)
      setError('')
    },
  })

  const voiceAvailable = stt.supported
  const ttsAvailable = tts.supported

  // Announce the current question, but only once per question.
  useEffect(() => {
    if (!question) return
    if (spokenIdsRef.current.has(question)) return
    spokenIdsRef.current.add(question)
    let cancelled = false
    setStage('ai_speaking')
    tts.speak(question).then((spoke) => {
      if (cancelled) return
      setSpokeCurrent(Boolean(spoke))
      setStage((current) => (current === 'ai_speaking' ? 'awaiting_answer' : current))
    })
    return () => {
      cancelled = true
    }
    // tts.speak identity changes when mute/voice changes; re-running on it would
    // restart the question, so it is intentionally not a dependency.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [question])

  useEffect(() => () => tts.cancel(), [tts])

  // A new question arrives: reset the answer surface.
  useEffect(() => {
    setTranscript('')
    setTyped('')
    setSpokeCurrent(false)
    stt.reset()
    tokenRef.current = makeClientToken()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [question])

  const answer = useMemo(
    () => (transcript.trim() ? transcript.trim() : typed.trim()),
    [transcript, typed],
  )

  const canSubmit = answer.length > 0 && !submitting && stage !== 'processing'

  const onMic = useCallback(() => {
    setError('')
    if (stt.listening) {
      stt.stop()
      setStage('awaiting_answer')
      return
    }
    setStage('listening')
    stt.start()
  }, [stt])

  const onSubmit = useCallback(async () => {
    if (!canSubmit) return
    const text = answer
    if (!isUsableTranscript(text, 2) && !typed.trim()) {
      setError('That answer is too short to evaluate. Add a little more detail, or type it instead.')
      return
    }
    setSubmitting(true)
    setError('')
    setStage('processing')
    stt.stop()
    try {
      const res = await onAnswered(text, tokenRef.current)
      if (res?.completed) {
        setStage('completed')
        tts.cancel()
        onCompleted?.(res.report || null)
        return
      }
      setStage('evaluating')
      setQuestionNumber((n) => n + 1)
      if (res?.total_questions) setTotal(res.total_questions)
      setQuestion(res?.next_question || '')
    } catch (err) {
      // The answer is already stored server-side, so the student can retry.
      setError(apiError(err, 'Could not submit your answer. Please try again.'))
      setStage('awaiting_answer')
    } finally {
      setSubmitting(false)
    }
  }, [answer, canSubmit, onAnswered, onCompleted, stt, tts, typed])

  const onRepeat = useCallback(() => {
    if (!question) return
    spokenIdsRef.current.delete(question)
    setStage('ai_speaking')
    tts.speak(question).then((spoke) => {
      setSpokeCurrent(Boolean(spoke))
      setStage('awaiting_answer')
    })
  }, [question, tts])

  const position = session?.position || ''
  const done = stage === 'completed'

  return (
    <div className="voice-interview">
      <div className="page-head">
        <div>
          <h1>AI voice interview</h1>
          <p className="muted">
            {position} · Question {Math.min(questionNumber, total)} of {total}
            {category ? ` · ${category}` : ''}
          </p>
        </div>
        <button className="btn btn-ghost" onClick={onEnd}>End interview</button>
      </div>

      <div className={`voice-stage stage-${stage}`} role="status" aria-live="polite">
        <span className="voice-stage-dot" aria-hidden="true" />
        {STATE_LABEL[stage] || 'Your turn'}
        {stage === 'ai_speaking' && tts.speaking && ' 🔊'}
        {stage === 'listening' && ' 🎤'}
      </div>

      {!voiceAvailable && (
        <div className="alert warn">
          {UNSUPPORTED_MESSAGE}
        </div>
      )}
      {!ttsAvailable && tts.muted === false && (
        <div className="alert warn">{TTS_UNSUPPORTED_MESSAGE}</div>
      )}

      {error && <div className="alert error">{error}</div>}

      <div className="voice-panel interviewer">
        <p className="muted small">AI INTERVIEWER</p>
        <p className="voice-question">{question || 'Preparing your first question…'}</p>
        <div className="voice-controls">
          <button className="btn btn-ghost" onClick={onRepeat} disabled={!question || tts.muted}>
            🔁 Repeat question
          </button>
          <button
            className="btn btn-ghost"
            onClick={tts.toggleMute}
            aria-pressed={tts.muted}
            disabled={!ttsAvailable}
          >
            {tts.muted ? '🔇 Speaker muted' : '🔊 Speaker on'}
          </button>
          {!ttsAvailable && <span className="muted small">Speech synthesis unavailable</span>}
        </div>
      </div>

      {!done && (
        <div className="voice-panel student">
          <p className="muted small">YOUR TURN</p>
          <div className="voice-controls">
            <button
              className={`btn ${stt.listening ? 'btn-danger' : 'btn-primary'} mic-btn`}
              onClick={onMic}
              disabled={!voiceAvailable || submitting}
            >
              {stt.listening ? '⏹ Stop recording' : '🎤 Start speaking'}
            </button>
            {stt.listening && <span className="listening-pulse">Listening…</span>}
          </div>

          {stt.error && <div className="alert warn">{stt.error}</div>}

          <label>
            Recognised transcript
            <textarea
              rows={3}
              value={transcript}
              onChange={(e) => setTranscript(e.target.value)}
              placeholder={voiceAvailable
                ? 'Your speech appears here. Review it before submitting.'
                : 'Voice input is unavailable here. Type your answer below.'}
            />
          </label>
          {stt.interim && <p className="muted small">Hearing: “{stt.interim}”</p>}

          <label>
            Or type / edit your answer
            <textarea
              rows={3}
              value={typed}
              onChange={(e) => setTyped(e.target.value)}
              placeholder="Type your answer here…"
            />
          </label>

          <div className="voice-controls">
            <button className="btn btn-primary" onClick={onSubmit} disabled={!canSubmit}>
              {submitting ? 'Submitting…' : 'Submit answer'}
            </button>
            {submitting && <span className="muted small">Evaluating your answer…</span>}
            {spokeCurrent && !stt.listening && !submitting && (
              <span className="muted small">You can answer now.</span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export { STATE_LABEL }

