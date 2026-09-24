import { useCallback, useEffect, useState } from 'react'
import { apiError } from '../../api/client'
import { applyToJob, fetchJobs } from '../../api/jobs'
import JobCard from '../../components/jobs/JobCard'

const PAGE_SIZE = 5

const JOB_TYPES = [
  ['', 'All types'],
  ['full_time', 'Full-time'],
  ['part_time', 'Part-time'],
  ['internship', 'Internship'],
  ['contract', 'Contract'],
]

export default function Jobs() {
  const [jobs, setJobs] = useState([])
  const [count, setCount] = useState(0)
  const [page, setPage] = useState(1)
  const [filters, setFilters] = useState({ q: '', job_type: '', location: '' })
  const [error, setError] = useState('')
  const [busyJob, setBusyJob] = useState(null)

  const load = useCallback(() => {
    setError('')
    const params = { page, page_size: PAGE_SIZE }
    Object.entries(filters).forEach(([k, v]) => {
      if (v) params[k] = v
    })
    fetchJobs(params)
      .then((data) => {
        const rows = Array.isArray(data) ? data : data.results ?? []
        const total = Array.isArray(data) ? data.length : data.count ?? rows.length
        setJobs(rows)
        setCount(total)
      })
      .catch((e) => setError(apiError(e, 'Could not load jobs')))
  }, [page, filters])

  useEffect(() => {
    load()
  }, [load])

  const setFilter = (key) => (e) => {
    setPage(1)
    setFilters((f) => ({ ...f, [key]: e.target.value }))
  }

  const onApply = async (job) => {
    setBusyJob(job.id)
    setError('')
    try {
      await applyToJob(job.id)
      load()
    } catch (e) {
      setError(apiError(e, 'Could not apply'))
    } finally {
      setBusyJob(null)
    }
  }

  const pages = Math.max(1, Math.ceil(count / PAGE_SIZE))

  return (
    <div className="page">
      <h1>Recommended jobs</h1>
      <p className="muted">
        Ranked by how many of your skills match each posting. Open a job for the
        full breakdown and eligibility.
      </p>
      {error && <div className="alert error">{error}</div>}
      <div className="filter-bar">
        <input
          className="search"
          placeholder="Search by role, company or location…"
          value={filters.q}
          onChange={setFilter('q')}
        />
        <select value={filters.job_type} onChange={setFilter('job_type')} aria-label="Job type">
          {JOB_TYPES.map(([value, label]) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>
        <input
          placeholder="Location"
          value={filters.location}
          onChange={setFilter('location')}
        />
      </div>
      <div className="job-list">
        {jobs.map((j) => (
          <JobCard key={j.id} job={j} busy={busyJob === j.id} onApply={onApply} />
        ))}
        {!jobs.length && <p className="muted">No jobs match your search.</p>}
      </div>
      {pages > 1 && (
        <div className="pagination">
          <button
            className="btn btn-ghost btn-sm"
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
          >
            ← Previous
          </button>
          <span className="muted small">
            Page {page} of {pages} · {count} jobs
          </span>
          <button
            className="btn btn-ghost btn-sm"
            disabled={page >= pages}
            onClick={() => setPage((p) => p + 1)}
          >
            Next →
          </button>
        </div>
      )}
    </div>
  )
}