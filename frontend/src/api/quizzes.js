import client from './client'

export const fetchQuizzes = () => client.get('/quizzes/').then(({ data }) => data?.results ?? data)

export const fetchQuiz = (id) => client.get(`/quizzes/${id}/`).then(({ data }) => data)

export const startQuiz = (id) =>
  client.post(`/quizzes/${id}/start/`, {}).then(({ data }) => data)

export const submitQuiz = (quizId, answers) =>
  client
    .post(`/quizzes/${quizId}/submit/`, { answers })
    .then(({ data }) => data)

export const submitAttempt = (attemptId, answers) =>
  client
    .post(`/quizzes/attempts/${attemptId}/submit/`, { answers })
    .then(({ data }) => data)

export const fetchMyAttempts = () =>
  client.get('/quiz-attempts/').then(({ data }) => data?.results ?? data)

export const fetchAttempt = (id) =>
  client.get(`/quiz-attempts/${id}/`).then(({ data }) => data)

export const fetchAdminQuizzes = () =>
  client.get('/quizzes/admin/').then(({ data }) => data?.results ?? data)

export const createAdminQuiz = (payload) =>
  client.post('/quizzes/admin/', payload).then(({ data }) => data)

export const updateAdminQuiz = (id, payload) =>
  client.put(`/quizzes/admin/${id}/`, payload).then(({ data }) => data)

export const deleteAdminQuiz = (id) =>
  client.delete(`/quizzes/admin/${id}/`)

export const createAdminQuestion = (payload) =>
  client.post('/quizzes/admin/questions/', payload).then(({ data }) => data)

export const updateAdminQuestion = (id, payload) =>
  client.patch(`/quizzes/admin/questions/${id}/`, payload).then(({ data }) => data)

export const deleteAdminQuestion = (id) =>
  client.delete(`/quizzes/admin/questions/${id}/`)