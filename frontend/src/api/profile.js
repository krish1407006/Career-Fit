import client from './client'

export const fetchProfile = () => client.get('/profile/').then(({ data }) => data)

export const updateProfile = (payload) => client.put('/profile/', payload).then(({ data }) => data)

// Education
export const fetchEducation = () => client.get('/education/').then(({ data }) => data)
export const addEducation = (payload) => client.post('/education/', payload).then(({ data }) => data)
export const updateEducation = (id, payload) =>
  client.put(`/education/${id}/`, payload).then(({ data }) => data)
export const deleteEducation = (id) => client.delete(`/education/${id}/`)

// Projects
export const fetchProjects = () => client.get('/projects/').then(({ data }) => data)
export const addProject = (payload) => client.post('/projects/', payload).then(({ data }) => data)
export const updateProject = (id, payload) =>
  client.put(`/projects/${id}/`, payload).then(({ data }) => data)
export const deleteProject = (id) => client.delete(`/projects/${id}/`)

// Certifications
export const fetchCertifications = () => client.get('/certifications/').then(({ data }) => data)
export const addCertification = (payload) =>
  client.post('/certifications/', payload).then(({ data }) => data)
export const updateCertification = (id, payload) =>
  client.put(`/certifications/${id}/`, payload).then(({ data }) => data)
export const deleteCertification = (id) => client.delete(`/certifications/${id}/`)

// Skills (reuse the global Skill catalog, per-student membership)
export const fetchMySkills = () => client.get('/profile/skills/').then(({ data }) => data)
export const addSkill = (name) => client.post('/profile/skills/', { name }).then(({ data }) => data)
export const removeSkill = (id) => client.delete(`/profile/skills/${id}/`)