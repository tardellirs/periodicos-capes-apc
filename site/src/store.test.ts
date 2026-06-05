import { describe, it, expect, beforeEach, vi } from 'vitest'

// Mock fetch before importing store
const mockJournals = [
  { id: 1, title: 'ACM Computing Surveys', publisher: 'ACM', issn: '0360-0300', eissn: '1557-7341', oa: 'Full Open Access', license: 'CC BY', area: 'Computação', main_discipline: 'Computer Science', imprint: 'ACM', url: null, qualis_best: 'A1', impact_factor: null, acronym: null, qualis: [{ area: 'COMPUTAÇÃO', estrato: 'A1' }] },
  { id: 2, title: 'Nature',               publisher: 'Springer Nature', issn: '0028-0836', eissn: '1476-4687', oa: 'Hybrid', license: 'CC BY', area: 'Ciências Biológicas', main_discipline: 'Life Sciences', imprint: 'Springer', url: null, qualis_best: 'A1', impact_factor: 69.5, acronym: null, qualis: [{ area: 'MEDICINA I', estrato: 'A1' }] },
  { id: 3, title: 'IEEE Access',          publisher: 'IEEE', issn: '2169-3536', eissn: '2169-3536', oa: 'Full Open Access', license: null, area: 'Engenharias', main_discipline: null, imprint: 'IEEE', url: null, qualis_best: 'A3', impact_factor: 3.6, acronym: 'ACCESS', qualis: [{ area: 'COMPUTAÇÃO', estrato: 'A3' }] },
]

global.fetch = vi.fn().mockResolvedValue({
  ok: true,
  json: () => Promise.resolve(mockJournals),
} as Response)

// Mock history.replaceState
Object.defineProperty(global, 'location', {
  value: { search: '', pathname: '/' },
  writable: true,
})
global.history = { replaceState: vi.fn() } as unknown as History

// Mock window.scrollTo
global.scrollTo = vi.fn() as unknown as typeof window.scrollTo

// Import after mocks — use dynamic import to reset module state between tests
async function freshStore() {
  vi.resetModules()
  const mod = await import('./store')
  return mod
}

describe('store — loadData', () => {
  it('loads journals and sets state', async () => {
    const store = await freshStore()
    await store.loadData()
    const s = store.getState()
    expect(s.loading).toBe(false)
    expect(s.error).toBeNull()
    expect(s.all).toHaveLength(3)
    expect(s.filtered).toHaveLength(3)
    expect(s.areas).toContain('Computação')
    expect(s.areas).toContain('Ciências Biológicas')
  })

  it('handles fetch failure gracefully', async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error('Network error'))
    const store = await freshStore()
    await store.loadData()
    const s = store.getState()
    expect(s.loading).toBe(false)
    expect(s.error).toContain('Network error')
    // Restore
    global.fetch = vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve(mockJournals) } as Response)
  })

  it('handles non-ok HTTP response', async () => {
    global.fetch = vi.fn().mockResolvedValue({ ok: false, status: 404 } as Response)
    const store = await freshStore()
    await store.loadData()
    expect(store.getState().error).toBeTruthy()
    global.fetch = vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve(mockJournals) } as Response)
  })
})

describe('store — setFilters', () => {
  beforeEach(() => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockJournals),
    } as Response)
  })

  it('filters by publisher', async () => {
    const store = await freshStore()
    await store.loadData()
    store.setFilters({ publishers: ['ACM'] })
    expect(store.getState().filtered).toHaveLength(1)
    expect(store.getState().filtered[0].publisher).toBe('ACM')
  })

  it('filters by qualis', async () => {
    const store = await freshStore()
    await store.loadData()
    store.setFilters({ qualis: ['A1'] })
    expect(store.getState().filtered).toHaveLength(2) // ACM + Nature
  })

  it('filters by text', async () => {
    const store = await freshStore()
    await store.loadData()
    store.setFilters({ q: 'ieee' })
    expect(store.getState().filtered).toHaveLength(1)
    expect(store.getState().filtered[0].title).toBe('IEEE Access')
  })

  it('resets page to 1 on filter change', async () => {
    const store = await freshStore()
    await store.loadData()
    store.setPage(3)
    expect(store.getState().page).toBe(1) // only 3 journals, so page is capped at 1
    store.setFilters({ q: 'nature' })
    expect(store.getState().page).toBe(1)
  })

  it('partial update merges with existing filters', async () => {
    const store = await freshStore()
    await store.loadData()
    store.setFilters({ publishers: ['ACM'] })
    store.setFilters({ qualis: ['A1'] })
    const s = store.getState()
    // Both filters should be active — ACM + A1 = 1 journal
    expect(s.filters.publishers).toEqual(['ACM'])
    expect(s.filters.qualis).toEqual(['A1'])
    expect(s.filtered).toHaveLength(1)
  })
})

describe('store — clearFilters', () => {
  it('resets all filters and restores full list', async () => {
    const store = await freshStore()
    await store.loadData()
    store.setFilters({ publishers: ['ACM'], qualis: ['A1'], q: 'test' })
    expect(store.getState().filtered).toHaveLength(0)
    store.clearFilters()
    const s = store.getState()
    expect(s.filtered).toHaveLength(3)
    expect(s.filters.publishers).toHaveLength(0)
    expect(s.filters.qualis).toHaveLength(0)
    expect(s.filters.q).toBe('')
    expect(s.page).toBe(1)
  })
})

describe('store — pagination', () => {
  it('getPage returns correct slice', async () => {
    const store = await freshStore()
    await store.loadData()
    const page = store.getPage()
    expect(page).toHaveLength(3) // all 3 journals fit in one page (PAGE_SIZE=25)
  })

  it('getTotalPages is 1 for small dataset', async () => {
    const store = await freshStore()
    await store.loadData()
    expect(store.getTotalPages()).toBe(1)
  })

  it('setPage clamps to valid range', async () => {
    const store = await freshStore()
    await store.loadData()
    store.setPage(999)
    expect(store.getState().page).toBe(1) // max page with 3 journals
    store.setPage(0)
    expect(store.getState().page).toBe(1) // min page
  })
})

describe('store — subscribe / notify', () => {
  it('listener called after loadData', async () => {
    const store = await freshStore()
    const listener = vi.fn()
    store.subscribe(listener)
    await store.loadData()
    expect(listener).toHaveBeenCalledTimes(1)
  })

  it('listener called after setFilters', async () => {
    const store = await freshStore()
    await store.loadData()
    const listener = vi.fn()
    store.subscribe(listener)
    store.setFilters({ q: 'test' })
    expect(listener).toHaveBeenCalledTimes(1)
  })

  it('listener called after clearFilters', async () => {
    const store = await freshStore()
    await store.loadData()
    const listener = vi.fn()
    store.subscribe(listener)
    store.clearFilters()
    expect(listener).toHaveBeenCalledTimes(1)
  })

  it('unsubscribe stops notifications', async () => {
    const store = await freshStore()
    await store.loadData()
    const listener = vi.fn()
    const unsubscribe = store.subscribe(listener)
    unsubscribe()
    store.setFilters({ q: 'test' })
    expect(listener).not.toHaveBeenCalled()
  })
})
