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

// Phase 6 - AI-powered resume analysis
export const analyzeResume = (id, jobId) =>
  client.post(`/resumes/${id}/analyze/`, jobId ? { job_id: jobId } : {}).then(({ data }) => data)

export const fetchResumeAnalysis = (id) =>
  client.get(`/resumes/${id}/analysis/`).then(({ data }) => data)

export const fetchResumeAnalysisById = (analysisId) =>
  client.get(`/resume-analyses/${analysisId}/`).then(({ data }) => data)


export const downloadResume = async (id, filename) => {
  const { data } = await client.get(`/resumes/${id}/download/`, { responseType: 'blob' })
  const url = URL.createObjectURL(data)
  const link = document.createElement('a')
  link.href = url
  link.download = filename || 'resume.pdf'
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}