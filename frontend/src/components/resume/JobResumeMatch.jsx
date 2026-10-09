import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiError } from '../../api/client'
import { analyzeResume, fetchResumes } from '../../api/resumes'
import { relevanceForJob } from '../../lib/resumeAnalysis'
import JobRelevancePanel from './JobRelevancePanel'

/**
 * "Run my resume analysis for this job" panel.
 *
 * Uses the existing analyze endpoint with a ``job_id``. General analysis (no
 * job) stays on the profile page, unchanged; this only adds the job-scoped
 * entry point. Relevance is shown only when the backend returns it.
 */
export default function JobResumeMatch({ job }) {
  const [resume, setResume] = useState(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState('')
  const [analyzing, setAnalyzing] = useState(false)
  const [analyzeError, setAnalyzeError] = useState('')
  const [relevance, setRelevance] = useState(null)

  const load = useCallback(() => {
    fetchResumes()
      .then((data) => {
        const rows = Array.isArray(data) ? data : data.results ?? []
        const latest = rows[0] || null
        setResume(latest)
        setLoadError('')
        const stored = latest?.analysis?.job_relevance
        if (stored?.job_id === job.id) setRelevance(stored)
      })
      .catch((e) => setLoadError(apiError(e, 'Could not load your resume')))
      .finally(() => setLoading(false))
  }, [job.id])

  useEffect(() => {
    load()
  }, [load])

  const retryLoad = () => {
    setLoading(true)
    setLoadError('')
    load()
  }

  const runAnalysis = async () => {
    if (!resume) return
    setAnalyzing(true)
    setAnalyzeError('')
    try {
      const data = await analyzeResume(resume.id, job.id)
      setRelevance(data.job_relevance || null)
    } catch (e) {
      setAnalyzeError(apiError(e, 'Could not analyze your resume for this job'))
    } finally {
      setAnalyzing(false)
    }
  }

  if (loading) {
    return <div className="page-loading">Checking your resume…</div>
  }

  if (loadError) {
    return (
      <div className="card">
        <div className="alert error">{loadError}</div>
        <button className="btn btn-ghost btn-sm" onClick={retryLoad}>Retry</button>
      </div>
    )
  }

  if (!resume) {
    return (
      <div className="card">
        <h3>Resume match for this job</h3>
        <p className="muted">
          Upload a resume to analyze how well it fits this role, then re-run the
          analysis for any job you are targeting.
        </p>
        <Link className="btn btn-primary btn-sm" to="/student/profile">Upload resume</Link>
      </div>
    )
  }

  return (
    <div className="card">
      <div className="section-head">
        <h3>Resume match for this job</h3>
        {!job.is_active && <span className="badge bad">Job closed</span>}
      </div>

      {relevance && <JobRelevancePanel relevance={relevance} />}

      {!relevance && !analyzing && !job.is_active && (
        <p className="muted">
          This job is closed, so resume matching is not available for it.
        </p>
      )}

      {!relevance && !analyzing && job.is_active && (
        <p className="muted">
          Analyze your latest resume ({resume.original_name}) against this job to
          see your matching and missing skills.
        </p>
      )}

      {analyzing && (
        <p className="muted small">
          Analyzing your resume against this job. This usually takes a few seconds.
        </p>
      )}

      {analyzeError && <div className="alert error">{analyzeError}</div>}

      {job.is_active && (
        <div className="job-actions">
          <button className="btn btn-primary btn-sm" onClick={runAnalysis} disabled={analyzing}>
            {analyzing ? 'Analyzing…' : relevance ? 'Re-analyze for this job' : 'Analyze for this job'}
          </button>
          {analyzeError && (
            <button className="btn btn-ghost btn-sm" onClick={runAnalysis} disabled={analyzing}>
              Retry
            </button>
          )}
        </div>
      )}
    </div>
  )
}
