/**
 * Renders the job-role relevance block returned by resume analysis.
 *
 * Kept in one place so the resume card on the profile page and the "match for
 * this job" panel on a job page cannot drift apart. Renders nothing unless the
 * backend actually returned a relevance block (``job_id`` present).
 */
export default function JobRelevancePanel({ relevance }) {
  if (!relevance?.job_id) return null
  const matched = relevance.matched_skills?.length || 0
  const missing = relevance.missing_skills?.length || 0

  return (
    <div className="analysis-block">
      <h4>Job relevance — {relevance.job_title}</h4>
      <div className="analysis-score">
        <span className="score-big">{relevance.match_score}%</span>
        <span className="muted small">
          Skill match for {relevance.company_name} · {matched} of {matched + missing} required skills
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
  )
}
