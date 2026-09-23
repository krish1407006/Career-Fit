import client from './client'

export const fetchJobs = (params = {}) =>
  client.get('/jobs/', { params }).then(({ data }) => data)

export const fetchMyJobs = () => client.get('/jobs/mine/').then(({ data }) => data?.results ?? data)

export const createJob = (payload) => client.post('/jobs/', payload).then(({ data }) => data)

export const updateJob = (id, payload) =>
  client.put(`/jobs/${id}/`, payload).then(({ data }) => data)

export const deleteJob = (id) => client.delete(`/jobs/${id}/`)

export const applyToJob = (jobId, coverNote = '') =>
  client.post(`/jobs/${jobId}/apply/`, { cover_note: coverNote }).then(({ data }) => data)

export const fetchApplicants = (jobId) =>
  client.get(`/jobs/${jobId}/applicants/`).then(({ data }) => data)

export const updateApplicationStatus = (applicationId, status) =>
  client.patch(`/applications/${applicationId}/status/`, { status }).then(({ data }) => data)

export const skillGap = (jobId) =>
  client.post('/skill-gap/', { job_id: jobId }).then(({ data }) => data)

export const fetchMyApplications = () =>
  client.get('/applications/mine/').then(({ data }) => data?.results ?? data)

export const fetchSkills = () => client.get('/skills/').then(({ data }) => data)