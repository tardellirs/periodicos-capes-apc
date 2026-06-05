import { test, expect } from '@playwright/test'

const BASE = 'http://localhost:5173'

test.describe('Page load', () => {
  test('renders header, hero and table', async ({ page }) => {
    await page.goto(BASE)
    await page.waitForSelector('.journal-table tbody tr', { timeout: 10000 })

    await expect(page.locator('.header-logo')).toContainText('Periódicos')
    await expect(page.locator('.hero h1')).toContainText('Acordos de Publicação')
    await expect(page.locator('#catalog-count')).toContainText('4.983')
    await expect(page.locator('.journal-table tbody tr')).toHaveCount(25)
  })

  test('has correct page title and lang', async ({ page }) => {
    await page.goto(BASE)
    await expect(page).toHaveTitle(/Periódicos CAPES/)
    const lang = await page.getAttribute('html', 'lang')
    expect(lang).toBe('pt-BR')
  })

  test('sidebar shows all filter sections', async ({ page }) => {
    await page.goto(BASE)
    await expect(page.locator('#filter-q')).toBeVisible()
    await expect(page.locator('#filter-issn')).toBeVisible()
    await expect(page.locator('#area-toggle')).toBeVisible()
    await expect(page.locator('#filter-oa')).toBeVisible()
    await expect(page.locator('.qualis-chips')).toBeVisible()
    await expect(page.locator('.faq-card')).toBeVisible()
  })
})

test.describe('Text search filter', () => {
  test('filters by title (case-insensitive)', async ({ page }) => {
    await page.goto(BASE)
    await page.waitForSelector('.journal-table tbody tr', { timeout: 10000 })

    await page.fill('#filter-q', 'ACM Computing')
    await page.waitForTimeout(400)
    await expect(page.locator('#catalog-count')).toContainText('de 4.983')
    const rows = page.locator('.journal-table tbody tr')
    await expect(rows.first().locator('.journal-title')).toContainText('ACM Computing')
  })

  test('shows empty state when no match', async ({ page }) => {
    await page.goto(BASE)
    await page.waitForSelector('.journal-table tbody tr', { timeout: 10000 })
    await page.fill('#filter-q', 'xyzxyzxyz_nonexistent')
    await page.waitForTimeout(400)
    await expect(page.locator('#table-state-msg')).toBeVisible()
    await expect(page.locator('#table-state-msg')).toContainText('Nenhum periódico')
  })

  test('updates URL when filtering', async ({ page }) => {
    await page.goto(BASE)
    await page.waitForSelector('.journal-table tbody tr', { timeout: 10000 })
    await page.fill('#filter-q', 'IEEE')
    await page.waitForTimeout(400)
    expect(page.url()).toContain('q=IEEE')
  })
})

test.describe('ISSN filter', () => {
  test('finds journal by print ISSN', async ({ page }) => {
    await page.goto(BASE)
    await page.waitForSelector('.journal-table tbody tr', { timeout: 10000 })
    // ACM Computing Surveys ISSN
    await page.fill('#filter-issn', '0360-0300')
    await page.waitForTimeout(400)
    await expect(page.locator('#catalog-count')).toContainText('1 de')
    await expect(page.locator('.journal-title').first()).toContainText('ACM Computing Surveys')
  })

  test('finds journal by eISSN', async ({ page }) => {
    await page.goto(BASE)
    await page.waitForSelector('.journal-table tbody tr', { timeout: 10000 })
    await page.fill('#filter-issn', '1557-7341')
    await page.waitForTimeout(400)
    await expect(page.locator('#catalog-count')).toContainText('1 de')
  })

  test('ISSN and title search are independent', async ({ page }) => {
    await page.goto(BASE)
    await page.waitForSelector('.journal-table tbody tr', { timeout: 10000 })
    await page.fill('#filter-q', 'ACM')
    await page.fill('#filter-issn', '0001-0782')
    await page.waitForTimeout(400)
    // Communications of the ACM has ISSN 0001-0782
    await expect(page.locator('#catalog-count')).toContainText('1 de')
  })
})

test.describe('Publisher filter', () => {
  test('ACM checkbox shows 73 journals', async ({ page }) => {
    await page.goto(BASE)
    await page.waitForSelector('.journal-table tbody tr', { timeout: 10000 })
    await page.check('input[value="ACM"]')
    await page.waitForTimeout(300)
    await expect(page.locator('#catalog-count')).toContainText('73 de')
  })

  test('multiple publishers combine as OR', async ({ page }) => {
    await page.goto(BASE)
    await page.waitForSelector('.journal-table tbody tr', { timeout: 10000 })
    await page.check('input[value="ACM"]')
    await page.check('input[value="ACS"]')
    await page.waitForTimeout(300)
    const text = await page.locator('#catalog-count').textContent()
    // 73 + 51 = 124
    expect(text).toContain('124 de')
  })

  test('URL reflects publisher filter', async ({ page }) => {
    await page.goto(BASE)
    await page.waitForSelector('.journal-table tbody tr', { timeout: 10000 })
    await page.check('input[value="IEEE"]')
    await page.waitForTimeout(300)
    expect(page.url()).toContain('pub=IEEE')
  })
})

test.describe('Qualis chip filter', () => {
  test('A1 chip activates and filters', async ({ page }) => {
    await page.goto(BASE)
    await page.waitForSelector('.journal-table tbody tr', { timeout: 10000 })
    const chip = page.locator('.qualis-chip[data-stratum="A1"]')
    await chip.click()
    await page.waitForTimeout(300)
    await expect(chip).toHaveClass(/active/)
    await expect(chip).toHaveAttribute('aria-pressed', 'true')
    const count = await page.locator('#catalog-count').textContent()
    expect(count).toContain('1.528 de')
  })

  test('chip toggles off on second click', async ({ page }) => {
    await page.goto(BASE)
    await page.waitForSelector('.journal-table tbody tr', { timeout: 10000 })
    const chip = page.locator('.qualis-chip[data-stratum="A1"]')
    await chip.click()
    await page.waitForTimeout(200)
    await chip.click()
    await page.waitForTimeout(300)
    await expect(chip).not.toHaveClass(/active/)
    await expect(page.locator('#catalog-count')).toContainText('4.983')
  })

  test('multiple strata combine as OR', async ({ page }) => {
    await page.goto(BASE)
    await page.waitForSelector('.journal-table tbody tr', { timeout: 10000 })
    await page.locator('.qualis-chip[data-stratum="A1"]').click()
    await page.locator('.qualis-chip[data-stratum="A2"]').click()
    await page.waitForTimeout(300)
    const count = await page.locator('#catalog-count').textContent()
    // A1=1528 + A2=904 = 2432
    expect(count).toContain('2.432 de')
  })
})

test.describe('Quartile filter', () => {
  test('Q1 chip activates, filters and reflects in URL', async ({ page }) => {
    await page.goto(BASE)
    await page.waitForSelector('.journal-table tbody tr', { timeout: 10000 })
    const chip = page.locator('.qualis-chip[data-quartile="Q1"]')
    await chip.click()
    await page.waitForTimeout(300)
    await expect(chip).toHaveClass(/active/)
    await expect(chip).toHaveAttribute('aria-pressed', 'true')
    await expect(page.locator('#catalog-count')).toContainText('de 4.983')
    expect(page.url()).toContain('quart=Q1')
  })
})

test.describe('Min cites filter', () => {
  test('filters journals below threshold', async ({ page }) => {
    await page.goto(BASE)
    await page.waitForSelector('.journal-table tbody tr', { timeout: 10000 })
    await page.locator('#filter-mincites').fill('10')
    await page.waitForTimeout(300)
    await expect(page.locator('#catalog-count')).toContainText('de 4.983')
    expect(page.url()).toContain('minc=10')
  })
})

test.describe('Sort by cites/doc', () => {
  test('clicking header sorts descending then ascending', async ({ page }) => {
    await page.goto(BASE)
    await page.waitForSelector('.journal-table tbody tr', { timeout: 10000 })

    const firstMetric = () =>
      page.locator('.journal-table tbody tr').first().locator('.metric-value').textContent()

    await page.locator('#sort-cites').click()
    await page.waitForTimeout(300)
    await expect(page.locator('#th-metric')).toHaveAttribute('aria-sort', 'descending')
    expect(page.url()).toContain('sort=cites_per_doc%3Adesc')
    const topDesc = parseFloat((await firstMetric()) ?? '0')

    await page.locator('#sort-cites').click()
    await page.waitForTimeout(300)
    await expect(page.locator('#th-metric')).toHaveAttribute('aria-sort', 'ascending')
    const topAsc = parseFloat((await firstMetric()) ?? '0')

    expect(topDesc).toBeGreaterThan(topAsc)
  })
})

test.describe('Sort by Qualis', () => {
  test('clicking header surfaces A1 first (desc)', async ({ page }) => {
    await page.goto(BASE)
    await page.waitForSelector('.journal-table tbody tr', { timeout: 10000 })

    await page.locator('#sort-qualis').click()
    await page.waitForTimeout(300)
    await expect(page.locator('#th-qualis')).toHaveAttribute('aria-sort', 'descending')
    expect(page.url()).toContain('sort=qualis_best%3Adesc')

    const firstQualis = page.locator('.journal-table tbody tr').first().locator('.qualis-badge')
    await expect(firstQualis).toHaveText('A1')
  })
})

test.describe('Area filter', () => {
  test('populates area dropdown after data loads', async ({ page }) => {
    await page.goto(BASE)
    await page.waitForSelector('.journal-table tbody tr', { timeout: 10000 })
    await page.locator('#area-toggle').click()
    const options = await page.locator('#area-options .multiselect-option').count()
    expect(options).toBeGreaterThan(30) // 38 areas
  })

  test('filters by area (multi-select)', async ({ page }) => {
    await page.goto(BASE)
    await page.waitForSelector('.journal-table tbody tr', { timeout: 10000 })
    await page.locator('#area-toggle').click()
    await page.locator('#area-options .multiselect-option', { hasText: 'Computação' })
      .first().locator('input[type="checkbox"]').check()
    await page.waitForTimeout(300)
    const count = await page.locator('#catalog-count').textContent()
    // Should show a subset (e.g. "311 de 4.983 periódicos"), not the full list
    expect(count).toContain('de 4.983')
    expect(count).toMatch(/^\d+\.?\d* de/) // starts with a number less than 4.983
    const n = parseInt(count!.replace(/\./g, ''))
    expect(n).toBeLessThan(4983)
  })
})

test.describe('Clear filters', () => {
  test('Limpar button resets all filters', async ({ page }) => {
    await page.goto(BASE)
    await page.waitForSelector('.journal-table tbody tr', { timeout: 10000 })
    await page.fill('#filter-q', 'IEEE')
    await page.check('input[value="ACM"]')
    await page.waitForTimeout(400)
    await page.click('#btn-clear-filters')
    await page.waitForTimeout(300)
    await expect(page.locator('#filter-q')).toHaveValue('')
    await expect(page.locator('input[value="ACM"]')).not.toBeChecked()
    await expect(page.locator('#catalog-count')).toContainText('4.983')
  })
})

test.describe('Journal detail modal', () => {
  test('opens on Ver detalhes click', async ({ page }) => {
    await page.goto(BASE)
    await page.waitForSelector('.journal-table tbody tr', { timeout: 10000 })
    const btn = page.locator('.btn-detail').nth(3)
    await btn.scrollIntoViewIfNeeded()
    await btn.click({ force: true })
    await expect(page.locator('dialog')).toBeVisible()
    await expect(page.locator('#dialog-title')).toBeVisible()
  })

  test('modal shows ISSN, area, oa type, editora', async ({ page }) => {
    await page.goto(BASE)
    await page.waitForSelector('.journal-table tbody tr', { timeout: 10000 })
    await page.locator('.btn-detail').nth(3).click({ force: true })
    await page.waitForSelector('dialog[open]')
    const body = page.locator('.dialog-body')
    await expect(body.getByText('ÁREA PRINCIPAL')).toBeVisible()
    await expect(body.getByText('TIPO DE ACESSO')).toBeVisible()
    await expect(body.getByText('EDITORA')).toBeVisible()
  })

  test('closes with Fechar button', async ({ page }) => {
    await page.goto(BASE)
    await page.waitForSelector('.journal-table tbody tr', { timeout: 10000 })
    await page.locator('.btn-detail').nth(3).click({ force: true })
    await page.waitForSelector('dialog[open]')
    await page.locator('#dialog-close-btn').click({ force: true })
    await expect(page.locator('dialog')).not.toBeVisible()
  })

  test('closes with X button', async ({ page }) => {
    await page.goto(BASE)
    await page.waitForSelector('.journal-table tbody tr', { timeout: 10000 })
    await page.locator('.btn-detail').nth(3).click({ force: true })
    await page.waitForSelector('dialog[open]')
    await page.locator('.dialog-close').click({ force: true })
    await expect(page.locator('dialog')).not.toBeVisible()
  })
})

test.describe('Pagination', () => {
  test('shows 25 rows per page by default', async ({ page }) => {
    await page.goto(BASE)
    await page.waitForSelector('.journal-table tbody tr', { timeout: 10000 })
    await expect(page.locator('.journal-table tbody tr')).toHaveCount(25)
  })

  test('pagination controls rendered for 4983 journals', async ({ page }) => {
    await page.goto(BASE)
    await page.waitForSelector('.pagination', { timeout: 10000 })
    const pages = page.locator('.page-btn')
    const count = await pages.count()
    expect(count).toBeGreaterThan(3) // prev, 1, 2, ..., next at minimum
  })

  test('next page loads different journals', async ({ page }) => {
    await page.goto(BASE)
    await page.waitForSelector('.journal-table tbody tr', { timeout: 10000 })
    const firstTitle = await page.locator('.journal-title').first().textContent()
    // Click page 2 — scope to pagination nav, use exact aria-label
    await page.locator('#pagination [aria-label="Página 2"]').click()
    await page.waitForTimeout(300)
    const newFirstTitle = await page.locator('.journal-title').first().textContent()
    expect(newFirstTitle).not.toBe(firstTitle)
  })

  test('URL contains page number when navigating', async ({ page }) => {
    await page.goto(BASE)
    await page.waitForSelector('.journal-table tbody tr', { timeout: 10000 })
    await page.locator('#pagination [aria-label="Página 2"]').click()
    await page.waitForTimeout(200)
    expect(page.url()).toContain('page=2')
  })

  test('URL state restored on navigation', async ({ page }) => {
    await page.goto(`${BASE}?q=IEEE&page=2`)
    await page.waitForSelector('.journal-table tbody tr', { timeout: 10000 })
    await expect(page.locator('#filter-q')).toHaveValue('IEEE')
  })
})

test.describe('Accessibility', () => {
  test('filter sidebar has aria-label', async ({ page }) => {
    await page.goto(BASE)
    await expect(page.locator('.filter-sidebar')).toHaveAttribute('aria-label', 'Filtros de pesquisa')
  })

  test('Qualis chips have aria-pressed', async ({ page }) => {
    await page.goto(BASE)
    const chip = page.locator('.qualis-chip[data-stratum="A1"]')
    await expect(chip).toHaveAttribute('aria-pressed', 'false')
    await chip.click()
    await expect(chip).toHaveAttribute('aria-pressed', 'true')
  })

  test('catalog count has aria-live', async ({ page }) => {
    await page.goto(BASE)
    await expect(page.locator('#catalog-count')).toHaveAttribute('aria-live', 'polite')
  })

  test('table has accessible caption/label', async ({ page }) => {
    await page.goto(BASE)
    await expect(page.locator('.journal-table')).toHaveAttribute('aria-labelledby', 'catalog-title')
  })
})
