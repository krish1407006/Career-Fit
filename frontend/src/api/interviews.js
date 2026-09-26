import client from './client'

export const startInterview = (payload) =>
  client.post('/interviews/start/', payload).then(({ data }) => data)

export const answerInterview = (sessionId, answer, clientToken = '') =>
  client
    .post(`/interviews/${sessionId}/answer/`, {
      answer,
      client_token: clientToken || undefined,
    })
    .then(({ data }) => data)

export const fetchMyInterviews = () =>
  client.get('/interviews/mine/').then(({ data }) => data?.results ?? data)

export const fetchInterview = (sessionId) =>
  client.get(`/interviews/${sessionId}/`).then(({ data }) => data)

/** Resumable session, or null when the student has nothing in progress. */
export const fetchActiveInterview = () =>
  client.get('/interviews/active/').then(({ data }) => data).catch((error) => {
    if (error?.response?.status === 404) return null
    throw error
  })

export const completeInterview = (sessionId) =>
  client.post(`/interviews/${sessionId}/complete/`, {}).then(({ data }) => data)

export const cancelInterview = (sessionId) =>
  client.post(`/interviews/${sessionId}/cancel/`, {}).then(({ data }) => data)

export const fetchInterviewReport = (sessionId) =>
  client.get(`/interviews/${sessionId}/report/`).then(({ data }) => data)
