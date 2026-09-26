/**
 * The Phase 7 interview report.
 *
 * Deliberately framed as self-practice: no hiring probability, no claim that
 * the score measures real ability, and no judgement about how someone speaks.
 */

const ScoreTag = ({ score }) => {
  if (score === null || score === undefined) return null
  const cls = score >= 8 ? 'ok' : score >= 5 ? 'warn' : 'bad'
  return <span className={`score-tag ${cls}`}>{score}/10</span>
}

const List = ({ items, empty, className = '' }) => {
  if (!items?.length) return <p className="muted small">{empty}</p>
  return (
    <ul className={`report-list ${className}`}>
      {items.map((item, i) => (
        <li key={i}>{item}</li>
      ))}
    </ul>
  )
}

export default function InterviewReport({ report, position }) {
  if (!report) return null
  const perQuestion = report.per_question || []

  return (
    <div className="card result-card interview-report">
      <div className="page-head">
        <div>
          <h2>Interview complete</h2>
          <p className="muted">
            {position || report.position} · {report.questions_answered ?? 0} answered
            {report.source ? ` · ${report.source === 'ai' ? 'AI coach' : 'offline engine'}` : ''}
          </p>
        </div>
        {report.score !== null && report.score !== undefined && (
          <ScoreTag score={report.score} />
        )}
      </div>

      {report.notice && <div className="alert warn">{report.notice}</div>}

      <section>
        <h3 className="section-title">Overall interview summary</h3>
        <p className="summary">{report.summary}</p>
        {report.score_note && <p className="muted small">{report.score_note}</p>}
      </section>

      <section>
        <h3 className="section-title">Questions answered</h3>
        <p className="muted">
          {report.questions_answered ?? 0} of {perQuestion.length} questions received an answer.
        </p>
      </section>

      <div className="report-grid">
        <section className="card card-sheet">
          <h4>Technical strengths</h4>
          <List items={report.technical_strengths} empty="No clear strength recorded yet." />
        </section>
        <section className="card card-sheet">
          <h4>Areas to improve</h4>
          <List items={report.areas_to_improve} empty="No improvement area recorded yet." />
        </section>
        <section className="card card-sheet">
          <h4>Technical topics to prepare</h4>
          <List items={report.topics_to_prepare} empty="No specific topic flagged." />
        </section>
      </div>

      <section>
        <h3 className="section-title">Question-wise feedback</h3>
        {perQuestion.length === 0 && (
          <p className="muted">No questions were answered in this interview.</p>
        )}
        {perQuestion.map((item, i) => (
          <div className="card card-sheet report-q" key={i}>
            <div className="page-head">
              <h4>
                Q{i + 1}. {item.question || '(question unavailable)'}
              </h4>
              <ScoreTag score={item.score} />
            </div>
            {item.category && <p className="muted small">Category: {item.category}</p>}
            <p className="muted small">Your answer</p>
            <p className="summary">{item.answer || <i>No answer submitted.</i>}</p>
            {item.feedback && (
              <>
                <p className="muted small">Evaluation</p>
                <p>{item.feedback}</p>
              </>
            )}
            {item.strengths?.length > 0 && (
              <>
                <p className="muted small">Strengths</p>
                <List items={item.strengths} />
              </>
            )}
            {item.improvements?.length > 0 && (
              <>
                <p className="muted small">Improvements</p>
                <List items={item.improvements} />
              </>
            )}
          </div>
        ))}
      </section>
    </div>
  )
}
