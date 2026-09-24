import { Link } from 'react-router-dom'
import SkillChips from './SkillChips'
import StatusBadge from './StatusBadge'

function MatchTag({ match }) {
  if (!match || match.score === null || match.score === undefined) return null
  const cls = match.score >= 70 ? 'ok' : match.score >= 40 ? 'warn' : 'bad'
  return <span className={`score-tag ${cls}`}>{match.score}% match</span>
}

export default function JobCard({ job, onApply, busy }) {
  const meta = [
    job.company_name,
    job.location,
    job.job_type?.replace('_', ' '),
    job.salary_range,
  ]
    .filter(Boolean)
    .join(' · ')

  return (
    <div className="card job-card">
      <div className="job-head">
        <div>
          <h3>
            <Link to={`/student/jobs/${job.id}`} className="job-title-link">
              {job.title}
            </Link>
          </h3>
          <p className="muted">{meta}</p>
        </div>
        {job.match && <MatchTag match={job.match} />}
      </div>
      <p className="summary">{job.description}</p>
      <SkillChips skills={job.skills_required} />
      {job.match && job.match.skill_gap.missing.length > 0 && (
        <p className="muted small">
          Missing: {job.match.skill_gap.missing.join(', ')}
        </p>
      )}
      <div className="job-actions">
        <Link className="btn btn-ghost btn-sm" to={`/student/jobs/${job.id}`}>
          View details
        </Link>
        {job.applied ? (
          <StatusBadge status={job.application_status} />
        ) : (
          <button
            className="btn btn-primary btn-sm"
            onClick={() => onApply(job)}
            disabled={busy}
          >
            {busy ? 'Applying…' : 'Apply'}
          </button>
        )}
      </div>
    </div>
  )
}