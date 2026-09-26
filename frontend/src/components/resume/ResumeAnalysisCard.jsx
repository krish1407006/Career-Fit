const SECTIONS = [
  {
    key: 'strengths',
    title: 'Strengths',
    empty: 'No strengths detected yet.',
    variant: 'ok',
  },
  {
    key: 'skill_gaps',
    title: 'Skill gaps',
    empty: 'No obvious skill gaps found.',
    variant: 'bad',
  },
  {
    key: 'improvements',
    title: 'Improvement suggestions',
    empty: 'No suggestions yet.',
    variant: 'plain',
  },
  {
    key: 'recommended_roles',
    title: 'Recommended roles',
    empty: 'No role suggestions yet.',
    variant: 'plain',
  },
]

export default function ResumeAnalysisCard({ analysis }) {
  if (!analysis) return null

  const relevance = analysis.job_relevance || {}
  const failed = analysis.status === 'failed'

  return (
    <div className="card analysis-card">
      <div className="section-head">
        <h3>AI resume analysis</h3>
        <span className={`badge ${failed ? 'bad' : 'ok'}`}>
          {failed ? 'Analysis failed' : 'Analysis complete'}
        </span>
      </div>

      {analysis.notice && <div className="alert warn-box">{analysis.notice}</div>}
      {analysis.error_message && <div className="alert error">{analysis.error_message}</div>}

      {analysis.summary && (
        <div className="analysis-block">
          <h4>Resume summary</h4>
          <p className="summary">{analysis.summary}</p>
        </div>
      )}

      {analysis.score > 0 && (
        <div className="analysis-block">
          <h4>Resume quality</h4>
          <div className="analysis-score">
            <span className="score-big">{analysis.score}</span>
            <span className="muted small">{analysis.score_note}</span>
          </div>
        </div>
      )}

      {!!analysis.detected_skills?.length && (
        <div className="analysis-block">
          <h4>Detected skills</h4>
          <div className="chips">
            {analysis.detected_skills.map((skill) => (
              <span key={skill} className="chip ai-chip">{skill}</span>
            ))}
          </div>
        </div>
      )}

      {SECTIONS.map(({ key, title, empty, variant }) => (
        <div className="analysis-block" key={key}>
          <h4>{title}</h4>
          {analysis[key]?.length ? (
            <ul className={`analysis-list ${variant}`}>
              {analysis[key].map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          ) : (
            <p className="muted">{empty}</p>
          )}
        </div>
      ))}

      {relevance.job_id && (
        <div className="analysis-block">
          <h4>Job relevance — {relevance.job_title}</h4>
          <div className="analysis-score">
            <span className="score-big">{relevance.match_score}%</span>
            <span className="muted small">
              Skill match for {relevance.company_name} · {relevance.matched_skills?.length || 0}{' '}
              of {relevance.matched_skills?.length + relevance.missing_skills?.length || 0} required
              skills
            </span>
          </div>
          {!!relevance.missing_skills?.length && (
            <div className="chips">
              {relevance.missing_skills.map((skill) => (
                <span key={skill} className="chip miss-chip">{skill}</span>
              ))}
            </div>
          )}
        </div>
      )}

      <p className="muted small">
        Analysed {new Date(analysis.analyzed_at).toLocaleString()}
        {analysis.source === 'ai' ? ` · AI (${analysis.provider})` : ' · rule-based checker'}
      </p>
    </div>
  )
}
