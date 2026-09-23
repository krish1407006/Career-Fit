import client from './client'

export const startInterview = (payload) =>
  client.post('/interviews/start/', payload).then(({ data }) => data)

export const answerInterview = (sessionId, answer) =>
  client
    .post(`/interviews/${sessionId}/answer/`, { answer })
    .then(({ data }) => data)

export const fetchMyInterviews = () =>
  client.get('/interviews/mine/').then(({ data }) => data?.results ?? data)

export const fetchInterview = (sessionId) =>
  client.get(`/interviews/${sessionId}/`).then(({ data }) => data)