import client from './client'

export const fetchDashboard = () => client.get('/dashboard/').then(({ data }) => data)
export const fetchStudentDashboard = () =>
  client.get('/dashboard/student/').then(({ data }) => data)
export const fetchRecruiterDashboard = () =>
  client.get('/dashboard/recruiter/').then(({ data }) => data)
export const fetchAdminDashboard = () =>
  client.get('/dashboard/admin/').then(({ data }) => data)