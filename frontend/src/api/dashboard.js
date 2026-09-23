import client from './client'

export const fetchDashboard = () => client.get('/dashboard/').then(({ data }) => data)