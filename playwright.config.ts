import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 240_000,
  expect: { timeout: 30_000 },
  use: { baseURL: 'http://127.0.0.1:8766', browserName: 'chromium', channel: 'chrome', headless: true, viewport: { width: 1440, height: 900 } },
  webServer: { command: `${process.env.PLAINCLAUSE_PYTHON || 'python'} -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8766`, url: 'http://127.0.0.1:8766/api/status', timeout: 120_000, reuseExistingServer: false, env: { PLAINCLAUSE_DB_PATH: 'test-results/e2e.db' } },
  reporter: 'list',
})
