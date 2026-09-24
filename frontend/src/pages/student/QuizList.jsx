import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiError } from '../../api/client'
import { fetchQuizzes } from '../../api/quizzes'

const CATEGORY_LABELS = {
  python: 'Python',
  javascript: 'JavaScript',
  django: 'Django',
  sql: 'SQL',
  dbms: 'DBMS',
  operating_systems: 'Operating Systems',
  computer_networks: 'Computer Networks',
  data_structures: 'Data Structures',
  aptitude: 'Aptitude',
  logical_reasoning: 'Logical Reasoning',
}

export const categoryLabel = (cat) => CATEGORY_LABELS[cat] || cat

export default function QuizList() {
  const [quizzes, setQuizzes] = useState([])
  const [error, setError] = useState('')

  const load = useCallback(() => {
    setError('')
    fetchQuizzes().then(setQuizzes).catch((e) => setError(apiError(e)))
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
      <div className="job-list">
        {quizzes.map((qz) => (
          <div key={qz.id} className="card quiz-card">
            <div className="job-head">
              <div>
                <h3>
                  <Link to={`/student/quizzes/${qz.id}`}>{qz.title}</Link>
                </h3>
                <p className="muted">
                  {categoryLabel(qz.category)} · {qz.difficulty} · {qz.total_questions} questions ·{' '}
                  {qz.duration_minutes ? `${qz.duration_minutes} min` : 'No time limit'}
                </p>
              </div>
              {qz.attempted && (
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
                {qz.attempted ? 'View' : 'Take quiz'}
              </Link>
            </div>
          </div>
        ))}
        {!quizzes.length && <p className="muted">No quizzes available yet.</p>}
      </div>
    </div>
  )
}