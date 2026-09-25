import { expect, test } from '@playwright/test'

test('upload, review, ask, compare, prepare, export, and delete', async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write'])
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Understand the fine print.' })).toBeVisible()
  await page.screenshot({ path: 'test-results/empty-desktop.png', fullPage: true })

  const input = page.getByLabel('Upload a PDF, DOCX, or TXT document')
  await input.setInputFiles({ name: 'Lease-v1.txt', mimeType: 'text/plain', buffer: Buffer.from('1. Rent\nTenant must pay $1,200 each month.\n\n2. Termination\nEither party may terminate with 30 days written notice.\n\n3. Governing Law\nCalifornia law applies to this agreement.') })
  await expect(page.getByRole('heading', { name: 'Lease-v1.txt' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Sections' })).toBeVisible()
  await page.screenshot({ path: 'test-results/filled-desktop.png', fullPage: true })
  await page.setViewportSize({ width: 1586, height: 992 })
  await page.screenshot({ path: 'test-results/filled-concept-size.png', fullPage: true })
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.getByLabel('Reading level').selectOption('detailed')
  await page.getByRole('button', { name: 'Generate overview' }).click()
  await expect(page.locator('.summary-result .answer-box')).toBeVisible({ timeout: 120_000 })
  await page.reload()
  await expect(page.getByLabel('Reading level')).toHaveValue('detailed')
  await expect(page.locator('.summary-result .answer-box')).toBeVisible()

  await page.locator('.section-toggle').filter({ hasText: '2. Termination' }).click()
  await expect(page.locator('.section-detail .original-text')).toContainText('30 days written notice')
  await page.getByRole('button', { name: 'Explain this section' }).click()
  await expect(page.locator('.section-detail .answer-box')).toBeVisible({ timeout: 120_000 })

  await page.getByRole('button', { name: 'Ask', exact: true }).click()
  await page.getByLabel('What would you like to understand?').fill('How much notice is required to terminate?')
  await page.getByRole('button', { name: 'Ask', exact: true }).last().click()
  await expect(page.locator('blockquote').first()).toContainText('30 days', { timeout: 120_000 })
  await page.getByRole('button', { name: 'Copy text' }).click()
  expect(await page.evaluate(() => navigator.clipboard.readText())).toContain('30 days')
  await page.reload()
  await page.getByRole('button', { name: 'Ask', exact: true }).click()
  await expect(page.locator('.conversation-history .question-line')).toContainText('How much notice is required to terminate?')

  await input.setInputFiles({ name: 'Lease-v2.txt', mimeType: 'text/plain', buffer: Buffer.from('1. Rent\nTenant must pay $1,300 each month.\n\n2. Termination\nEither party may terminate with 60 days written notice.\n\n3. Governing Law\nCalifornia law applies to this agreement.') })
  await expect(page.getByRole('heading', { name: 'Lease-v2.txt' })).toBeVisible()
  await page.getByRole('button', { name: 'Compare', exact: true }).click()
  await page.locator('.compare-picker input[type="checkbox"]:not(:checked)').first().check()
  await expect(page.getByRole('button', { name: 'Compare selected' })).toBeEnabled()
  await page.getByRole('button', { name: 'Compare selected' }).click()
  await expect(page.getByText('60 days written notice')).toBeVisible()
  await expect(page.getByText('30 days written notice')).toBeVisible()

  await page.getByRole('button', { name: 'Prepare', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Before you decide' })).toBeVisible()
  await page.getByLabel('What do you want to understand or resolve? Add facts you want to bring to a professional.').fill('I want to understand my renewal options.')
  const downloadPromise = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Markdown' }).click()
  const download = await downloadPromise
  expect(download.suggestedFilename()).toContain('lawyer-prep')

  page.once('dialog', dialog => dialog.accept())
  await page.getByRole('button', { name: 'Delete my data' }).click()
  await expect(page.getByRole('heading', { name: 'Understand the fine print.' })).toBeVisible()
})

test('mobile empty view has no horizontal overflow', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Understand the fine print.' })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390)
  await page.screenshot({ path: 'test-results/empty-mobile.png', fullPage: true })
  const input = page.getByLabel('Upload a PDF, DOCX, or TXT document')
  await input.setInputFiles({ name: 'Mobile-v1.txt', mimeType: 'text/plain', buffer: Buffer.from('1. Payment\nThe customer must pay $200 each month.\n\n2. Termination\nEither party may terminate with 30 days notice.') })
  await expect(page.getByRole('heading', { name: 'Mobile-v1.txt' })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390)
  await page.screenshot({ path: 'test-results/filled-mobile.png', fullPage: true })
  await input.setInputFiles({ name: 'Mobile-v2.txt', mimeType: 'text/plain', buffer: Buffer.from('1. Payment\nThe customer must pay $250 each month.\n\n2. Termination\nEither party may terminate with 60 days notice.') })
  await expect(page.getByRole('heading', { name: 'Mobile-v2.txt' })).toBeVisible()
  await expect(page.getByRole('button', { name: /Mobile-v1.txt/ })).toBeVisible()
  await page.getByRole('button', { name: 'Compare', exact: true }).click()
  await page.locator('.compare-picker input[type="checkbox"]:not(:checked)').first().check()
  await expect(page.getByRole('button', { name: 'Compare selected' })).toBeEnabled()
  await page.getByRole('button', { name: 'Compare selected' }).click()
  await expect(page.locator('.comparison-results')).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390)
  await page.screenshot({ path: 'test-results/compare-mobile.png', fullPage: true })
  page.once('dialog', dialog => dialog.accept())
  await page.getByRole('button', { name: 'Delete my data' }).click()
  await expect(page.getByRole('heading', { name: 'Understand the fine print.' })).toBeVisible()
})

test('hosted preview accurately describes provider-neutral tunnel handling', async ({ page }) => {
  await page.route('**/api/status', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      model_available: true,
      model: 'Ollama local model',
      disclaimer: 'Legal information, not legal advice.',
      hosted_preview: true,
    }),
  }))

  await page.goto('/')

  await expect(page.getByRole('note')).toContainText('secure tunnel provider')
  await expect(page.locator('body')).not.toContainText('localhost.run')
})

test('hosted service describes cloud processing and storage', async ({ page }) => {
  await page.route('**/api/status', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      model_available: true,
      model: 'Ollama local model',
      disclaimer: 'Legal information, not legal advice.',
      hosted_preview: false,
      hosted_service: true,
    }),
  }))

  await page.goto('/')
  await expect(page.getByRole('note')).toContainText('Hosted evaluation service')
  await expect(page.getByText('Hosted workspace')).toBeVisible()
  await expect(page.locator('body')).not.toContainText('this computer and tunnel')
})
