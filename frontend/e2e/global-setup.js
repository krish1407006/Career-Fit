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
  } finally {
    await api.dispose()
  }
}
