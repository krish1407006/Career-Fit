import { useEffect, useState } from 'react'
import { apiError } from '../../api/client'
import {
  createAdminQuiz,
  deleteAdminQuiz,
  fetchAdminQuizzes,
  updateAdminQuiz,
} from '../../api/quizzes'
import { categoryLabel } from '../student/QuizList'

const CATEGORIES = [
  'python', 'javascript', 'django', 'sql', 'dbms', 'operating_systems',
  'computer_networks', 'data_structures', 'aptitude', 'logical_reasoning',
]
const DIFFICULTIES = ['easy', 'medium', 'hard']

const emptyQuestion = () => ({
  id: null,
  text: '',
  options: 'A option|B option|C option|D option',
  correct: 'A',
  explanation: '',
  topic: '',
  difficulty: 'medium',
})

const emptyQuiz = {
  title: '',
  description: '',
  category: 'python',
  difficulty: 'medium',
  duration_minutes: 10,
  is_active: true,
  questions: [emptyQuestion()],
}

function optionsFromText(text) {
  return (text || '')
    .split('|')
    .map((s) => s.trim())
    .filter(Boolean)
}

function letters(n) {
  return Array.from({ length: n }, (_, i) => String.fromCharCode(65 + i))
}

function QuizEditor({ initial, busy, onSubmit, onCancel }) {
  const [form, setForm] = useState(() => {
    if (!initial) return { ...emptyQuiz, questions: [emptyQuestion()] }
    return {
      title: initial.title,
      description: initial.description,
      category: initial.category,
      difficulty: initial.difficulty,
      duration_minutes: initial.duration_minutes ?? '',
      is_active: initial.is_active,
      questions: (initial.questions || []).map((q) => ({
        id: q.id,
        text: q.text,
        options: (q.options || []).join(' | '),
        correct: q.options[q.correct_index] ? letters(q.options.length)[q.correct_index] : 'A',
        explanation: q.explanation,
        topic: q.topic,
        difficulty: q.difficulty,
      })),
    }
  })

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value })
  const setQuestion = (i, key) => (e) => {
    const questions = form.questions.map((q, idx) =>
      idx === i ? { ...q, [key]: e.target.value } : q)
    setForm({ ...form, questions })
  }

  const submit = (e) => {
    e.preventDefault()
    const payload = {
      title: form.title.trim(),
      description: form.description,
      category: form.category,
      difficulty: form.difficulty,
      duration_minutes: form.duration_minutes === '' || !form.duration_minutes
        ? null
        : Number(form.duration_minutes),
      is_active: form.is_active,
      questions: form.questions
        .filter((q) => q.text.trim())
        .map((q) => {
          const opts = optionsFromText(q.options)
          return {
            id: q.id || undefined,
            text: q.text.trim(),
            options: opts,
            correct_index: opts.length ? q.correct.charCodeAt(0) - 65 : 0,
            explanation: q.explanation,
            topic: q.topic,
            difficulty: q.difficulty,
          }
        }),
    }
    onSubmit(payload)
  }

  return (
    <form className="auth-card card-sheet" onSubmit={submit}>
      <h3>{initial ? `Edit quiz — ${initial.title}` : 'Create a new quiz'}</h3>
      <label>Title
        <input value={form.title} onChange={set('title')} placeholder="e.g. Python Fundamentals" required /></label>
      <label>Description
        <textarea rows={3} value={form.description} onChange={set('description')} /></label>
      <div className="row">
        <label>Category
          <select value={form.category} onChange={set('category')}>
            {CATEGORIES.map((c) => <option key={c} value={c}>{categoryLabel(c)}</option>)}
          </select></label>
        <label>Difficulty
          <select value={form.difficulty} onChange={set('difficulty')}>
            {DIFFICULTIES.map((d) => <option key={d} value={d}>{d}</option>)}
          </select></label>
      </div>
      <div className="row">
        <label>Duration (minutes, blank = no limit)
          <input type="number" min="1" value={form.duration_minutes} onChange={set('duration_minutes')} placeholder="e.g. 10" /></label>
        <label className="checkbox-line">
          <input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} />
          Active (visible to students)
        </label>
      </div>

      <h4>Questions</h4>
      {form.questions.map((q, i) => {
        const opts = optionsFromText(q.options)
        const lettersList = letters(Math.max(opts.length, 4))
        return (
          <div key={i} className="card question-draft">
            <div className="row row-top">
              <label className="grow">Question text
                <input value={q.text} onChange={setQuestion(i, 'text')} placeholder="Question" /></label>
              <button
                type="button"
                className="btn btn-danger btn-sm"
                onClick={() => setForm({
                  ...form,
                  questions: form.questions.filter((_, idx) => idx !== i),
                })}
                disabled={form.questions.length === 1}
              >
                Remove
              </button>
            </div>
            <label>Options (pipe separated)
              <input value={q.options} onChange={setQuestion(i, 'options')} placeholder="A option | B option | C option | D option" /></label>
            <div className="row">
              <label>Correct answer
                <select value={q.correct} onChange={setQuestion(i, 'correct')}>
                  {lettersList.map((l) => {
                    const idx = l.charCodeAt(0) - 65
                    return <option key={l} value={l} disabled={idx >= opts.length}>{l}</option>
                  })}
                </select></label>
              <label>Difficulty
                <select value={q.difficulty} onChange={setQuestion(i, 'difficulty')}>
                  {DIFFICULTIES.map((d) => <option key={d} value={d}>{d}</option>)}
                </select></label>
              <label>Topic
                <input value={q.topic} onChange={setQuestion(i, 'topic')} placeholder="e.g. OOP" /></label>
            </div>
            <label>Explanation (shown after submission)
              <textarea rows={2} value={q.explanation} onChange={setQuestion(i, 'explanation')} /></label>
          </div>
        )
      })}
      <button
        type="button"
        className="btn btn-ghost"
        onClick={() => setForm({ ...form, questions: [...form.questions, emptyQuestion()] })}
      >
        + Add question
      </button>

      <div className="row row-top">
        <button type="submit" className="btn btn-primary" disabled={busy}>
          {busy ? 'Saving…' : initial ? 'Save changes' : 'Create quiz'}
        </button>
        <button type="button" className="btn btn-ghost" onClick={onCancel}>Cancel</button>
      </div>
    </form>
  )
}

export default function AdminQuizzes() {
  const [quizzes, setQuizzes] = useState([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [editor, setEditor] = useState(null) // null = closed, false = create, object = editing

  const load = () => {
    fetchAdminQuizzes().then(setQuizzes).catch((e) => setError(apiError(e, 'Could not load quizzes')))
  }

  useEffect(() => {
    load()
  }, [])

  const onSave = async (payload) => {
    setBusy(true)
    setError('')
    try {
      if (editor) await updateAdminQuiz(editor.id, payload)
      else await createAdminQuiz(payload)
      setEditor(null)
      load()
    } catch (e) {
      setError(apiError(e, 'Could not save quiz'))
    } finally {
      setBusy(false)
    }
  }

  const onDelete = async (q) => {
    if (!window.confirm(`Delete quiz "${q.title}" (including its questions and attempts)?`)) return
    setBusy(true)
    setError('')
    try {
      await deleteAdminQuiz(q.id)
      load()
    } catch (e) {
      setError(apiError(e))
    } finally {
      setBusy(false)
    }
  }

  if (editor !== null) {
    return (
      <div className="page">
        <QuizEditor
          initial={editor || undefined}
          busy={busy}
          onSubmit={onSave}
          onCancel={() => setEditor(null)}
        />
        {error && <div className="alert error">{error}</div>}
      </div>
    )
  }

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Quiz management</h1>
          <p className="muted">{quizzes.length} quizzes in total.</p>
        </div>
        <button className="btn btn-primary" onClick={() => setEditor(false)}>+ New quiz</button>
      </div>
      {error && <div className="alert error">{error}</div>}
      {quizzes.length ? (
        <div className="app-table-wrap">
          <table className="app-table">
            <thead>
              <tr><th>Title</th><th>Category</th><th>Difficulty</th><th>Duration</th><th>Questions</th><th>Status</th><th /></tr>
            </thead>
            <tbody>
              {quizzes.map((q) => (
                <tr key={q.id}>
                  <td>{q.title}</td>
                  <td>{categoryLabel(q.category)}</td>
                  <td>{q.difficulty}</td>
                  <td>{q.duration_minutes ? `${q.duration_minutes} min` : 'None'}</td>
                  <td>{q.total_questions}</td>
                  <td>
                    <span className={`badge ${q.is_active ? 'analyzed' : 'neutral'}`}>
                      {q.is_active ? 'Active' : 'Hidden'}
                    </span>
                  </td>
                  <td>
                    <button className="btn btn-ghost btn-sm" onClick={() => setEditor(q)}>Edit</button>
                    <button
                      className="btn btn-danger btn-sm"
                      onClick={() => onDelete(q)}
                      disabled={busy}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="muted">No quizzes yet.</p>
      )}
    </div>
  )
}