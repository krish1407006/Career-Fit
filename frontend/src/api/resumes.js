import client from './client'

export const fetchResumes = () => client.get('/resumes/').then(({ data }) => data)

export const uploadResume = (file) => {
  const form = new FormData()
  form.append('file', file)
  return client
    .post('/resumes/', form, { headers: { 'Content-Type': 'multipart/form-data' } })
    .then(({ data }) => data)
}

export const deleteResume = (id) => client.delete(`/resumes/${id}/`)