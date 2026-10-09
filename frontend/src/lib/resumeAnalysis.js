/**
 * Frontend helpers for resume analysis.
 *
 * The heavy lifting lives on the server (apps/resumes/analysis.py). These pure
 * helpers only shape the request and pick the right relevance block to show,
 * so the rules are testable without a DOM and are not repeated in components.
 */

/** Body for the analyze endpoint: job-scoped, or empty for a general analysis. */
export const analysisPayload = (jobId) => (jobId ? { job_id: jobId } : {})

/**
 * The stored relevance block, but only when it belongs to the job on screen.
 * Prevents a relevance block from a previous job being shown for a different one.
 */
export const relevanceForJob = (analysis, jobId) => {
  const relevance = analysis?.job_relevance
  if (!relevance?.job_id || jobId == null) return null
  return String(relevance.job_id) === String(jobId) ? relevance : null
}
