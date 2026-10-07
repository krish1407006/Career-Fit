import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig } from '@playwright/test'

const root = path.dirname(fileURLToPath(import.meta.url))
const backendDir = path.join(root, '..', 'backend')

export default defineConfig({
  testDir: './e2e',
  globalSetup: './e2e/global-setup.js',
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 2,
  retries: 0,
  reporter: [['list'], ['html', { open: 'never' }]],
  outputDir: 'test-results',
  use: {
    baseURL: 'http://localhost:5173',
    channel: 'chrome',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'off',
  },
  webServer: [
    {
      command: 'npm run dev',
      cwd: root,
      url: 'http://localhost:5173',
      reuseExistingServer: true,
      timeout: 60_000,
    },
    {
      command: '.\\.venv\\Scripts\\python.exe manage.py runserver 127.0.0.1:8000 --noreload',
      cwd: backendDir,
      url: 'http://127.0.0.1:8000/api/health/',
      reuseExistingServer: true,
      timeout: 60_000,
    },
  ],
})
