import client from './client'

export const fetchQuizzes = () => client.get('/quizzes/').then(({ data }) => data?.results ?? data)

export const fetchQuiz = (id) => client.get(`/quizzes/${id}/`).then(({ data }) => data)

export const startQuiz = (id) =>
  client.post(`/quizzes/${id}/start/`, {}).then(({ data }) => data)

export const submitQuiz = (attemptId, answers) =>
  client
    .post(`/quizzes/attempts/${attemptId}/submit/`, { answers })
    .then(({ data }) => data)

export const fetchMyAttempts = () =>
  client.get('/quizzes/attempts/mine/').then(({ data }) => data?.results ?? data)