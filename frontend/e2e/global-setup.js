import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { request } from '@playwright/test'

const here = path.dirname(fileURLToPath(import.meta.url))
const authDir = path.join(here, '.auth')

const PAGE_ORIGIN = 'http://localhost:5173'
const API_BASE = 'http://127.0.0.1:8000'

const ACCOUNTS = [
  { name: 'student', username: 'student1', password: 'Student@123' },
  { name: 'admin', username: 'admin', password: 'Admin@123' },
  { name: 'recruiter', username: 'acme_recruiter', password: 'Recruiter@123' },
]

// Upload tests delete and replace resumes, so they get their own throwaway
// student rather than mutating the seeded demo account.
const E2E_STUDENT = {
  name: 'e2e-student',
  username: 'e2e_student',
  email: 'e2e_student@careerfit.test',
  password: 'E2eStudent@123',
}

const writeState = (name, access, refresh) => {
  const state = {
    cookies: [],
    origins: [
      {
        origin: PAGE_ORIGIN,
        localStorage: [
          { name: 'careerai_access', value: access },
          { name: 'careerai_refresh', value: refresh },
        ],
      },
    ],
  }
  fs.writeFileSync(path.join(authDir, `${name}.json`), JSON.stringify(state, null, 2))
}

export default async function globalSetup() {
  fs.mkdirSync(authDir, { recursive: true })
  const api = await request.newContext({ baseURL: API_BASE })
  try {
    for (const { name, username, password } of ACCOUNTS) {
      const res = await api.post('/api/auth/login/', { data: { username, password } })
      if (!res.ok()) {
        throw new Error(`Login failed for ${name}: ${res.status()} ${await res.text()}`)
      }
      const { access, refresh } = await res.json()
      writeState(name, access, refresh)
    }

    // Registering twice is expected on a second run; login is the source of truth.
    await api.post('/api/auth/register/', {
      data: {
        username: E2E_STUDENT.username,
        email: E2E_STUDENT.email,
        password: E2E_STUDENT.password,
        first_name: 'E2E',
        last_name: 'Student',
        role: 'student',
      },
    })
    const login = await api.post('/api/auth/login/', {
      data: { username: E2E_STUDENT.username, password: E2E_STUDENT.password },
    })
    if (!login.ok()) {
      throw new Error(`Login failed for ${E2E_STUDENT.name}: ${login.status()} ${await login.text()}`)
    }
    const { access, refresh } = await login.json()
    writeState(E2E_STUDENT.name, access, refresh)
  } finally {
    await api.dispose()
  }
}
