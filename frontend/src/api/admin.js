import client, { apiError } from './client'

/**
 * Read-only views over every student's records, for the admin inspection
 * screens. These exist so an admin can confirm the platform is recording what
 * it should; none of them can change anything.
 */

/** DRF returns a bare array from APIView and {results: []} from ListAPIView. */
const rows = (data) => (Array.isArray(data) ? data : data?.results ?? [])

const query = (params = {}) => {
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '' && value !== 'all') {
      search.set(key, value)
    }
  })
  const text = search.toString()
  return text ? `?${text}` : ''
}

const withError = (message, run) =>
  run().catch((e) => {
    throw new Error(apiError(e, message))
  })

// ------------------------------------------------------------------ resumes
export const fetchAdminResumes = (filters = {}) =>
  withError('Could not load resumes', () =>
    client.get(`/resumes/admin/${query(filters)}`).then(({ data }) => rows(data)),
  )

export const fetchAdminResumeAnalysis = (resumeId) =>
  withError('Could not load that resume analysis', () =>
    client.get(`/resumes/admin/${resumeId}/analysis/`).then(({ data }) => data),
  )

// ------------------------------------------------------------- applications
export const fetchAdminApplications = (filters = {}) =>
  withError('Could not load applications', () =>
    client.get(`/admin/applications/${query(filters)}`).then(({ data }) => rows(data)),
  )

// ---------------------------------------------------------------- interviews
export const fetchAdminInterviews = (filters = {}) =>
  withError('Could not load interviews', () =>
    client.get(`/interviews/admin/${query(filters)}`).then(({ data }) => rows(data)),
  )

/** Any student's transcript. The detail endpoint already admits admins. */
export const fetchAdminInterview = (sessionId) =>
  withError('Could not load that interview', () =>
    client.get(`/interviews/${sessionId}/`).then(({ data }) => data),
  )

// ------------------------------------------------------------ quiz attempts
export const fetchAdminAttempts = (filters = {}) =>
  withError('Could not load quiz attempts', () =>
    client.get(`/quiz-attempts/${query(filters)}`).then(({ data }) => rows(data)),
  )

export const fetchAdminAttempt = (attemptId) =>
  withError('Could not load that quiz attempt', () =>
    client.get(`/quiz-attempts/${attemptId}/`).then(({ data }) => data),
  )
