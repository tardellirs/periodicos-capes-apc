import { describe, it, expect } from 'vitest'
import { applyFilters, sortJournals, getUniqueAreas } from './filters'
import type { Journal, Filters } from './types'
import { EMPTY_FILTERS } from './types'

// ─── Fixtures ────────────────────────────────────────────────────────────────

function j(overrides: Partial<Journal> = {}): Journal {
  return {
    id: 1,
    title: 'Test Journal',
    publisher: 'Elsevier',
    issn: '1234-5678',
    eissn: '8765-4321',
    oa: 'Hybrid',
    license: 'CC BY',
    area: 'Computação',
    main_discipline: 'Computer Science',
    imprint: 'Elsevier',
    url: null,
    qualis_best: 'A1',
    impact_factor: null,
    acronym: null,
    cites_per_doc: 4.5,
    quartile: 'Q1',
    sjr: 1.2,
    h_index: 100,
    metric_source: 'scimago',
    qualis: [{ area: 'COMPUTAÇÃO', estrato: 'A1' }],
    ...overrides,
  }
}

const filters = (overrides: Partial<Filters> = {}): Filters => ({
  ...EMPTY_FILTERS,
  ...overrides,
})

// ─── applyFilters — text search ──────────────────────────────────────────────

describe('applyFilters — q (title search)', () => {
  it('empty q matches everything', () => {
    const journals = [j({ title: 'Nature' }), j({ title: 'Science' })]
    expect(applyFilters(journals, filters())).toHaveLength(2)
  })

  it('matches exact title substring (case-insensitive)', () => {
    const journals = [j({ title: 'Nature Biotechnology' }), j({ title: 'Science' })]
    expect(applyFilters(journals, filters({ q: 'nature' }))).toHaveLength(1)
    expect(applyFilters(journals, filters({ q: 'NATURE' }))).toHaveLength(1)
  })

  it('matches partial title', () => {
    const journals = [j({ title: 'ACM Computing Surveys' }), j({ title: 'IEEE Transactions' })]
    expect(applyFilters(journals, filters({ q: 'computing' }))).toHaveLength(1)
  })

  it('strips accents for comparison', () => {
    const journals = [j({ title: 'Revista Científica' }), j({ title: 'Science' })]
    expect(applyFilters(journals, filters({ q: 'cientifica' }))).toHaveLength(1)
    expect(applyFilters(journals, filters({ q: 'Científica' }))).toHaveLength(1)
  })

  it('returns empty when no match', () => {
    const journals = [j({ title: 'Nature' }), j({ title: 'Science' })]
    expect(applyFilters(journals, filters({ q: 'xyz' }))).toHaveLength(0)
  })
})

// ─── applyFilters — ISSN search ──────────────────────────────────────────────

describe('applyFilters — issn', () => {
  it('matches by print ISSN with dash', () => {
    const journals = [j({ issn: '1234-5678' })]
    expect(applyFilters(journals, filters({ issn: '1234-5678' }))).toHaveLength(1)
  })

  it('matches by print ISSN without dash', () => {
    const journals = [j({ issn: '1234-5678' })]
    expect(applyFilters(journals, filters({ issn: '12345678' }))).toHaveLength(1)
  })

  it('matches by eISSN', () => {
    const journals = [j({ issn: null, eissn: '8765-4321' })]
    expect(applyFilters(journals, filters({ issn: '8765-4321' }))).toHaveLength(1)
  })

  it('matches partial ISSN', () => {
    const journals = [j({ issn: '1234-5678' }), j({ issn: '9999-0000' })]
    expect(applyFilters(journals, filters({ issn: '1234' }))).toHaveLength(1)
  })

  it('does not match wrong ISSN', () => {
    const journals = [j({ issn: '1234-5678' })]
    expect(applyFilters(journals, filters({ issn: '0000-0000' }))).toHaveLength(0)
  })

  it('handles journal with no ISSN gracefully', () => {
    const journals = [j({ issn: null, eissn: null })]
    expect(applyFilters(journals, filters({ issn: '1234' }))).toHaveLength(0)
  })

  it('empty issn matches everything', () => {
    const journals = [j(), j()]
    expect(applyFilters(journals, filters({ issn: '' }))).toHaveLength(2)
  })
})

// ─── applyFilters — publisher ─────────────────────────────────────────────────

describe('applyFilters — publishers', () => {
  it('empty publisher list matches all', () => {
    const journals = [j({ publisher: 'ACM' }), j({ publisher: 'IEEE' })]
    expect(applyFilters(journals, filters({ publishers: [] }))).toHaveLength(2)
  })

  it('single publisher filters correctly', () => {
    const journals = [j({ publisher: 'ACM' }), j({ publisher: 'IEEE' }), j({ publisher: 'Elsevier' })]
    expect(applyFilters(journals, filters({ publishers: ['ACM'] }))).toHaveLength(1)
  })

  it('multiple publishers work as OR', () => {
    const journals = [j({ publisher: 'ACM' }), j({ publisher: 'IEEE' }), j({ publisher: 'Elsevier' })]
    expect(applyFilters(journals, filters({ publishers: ['ACM', 'IEEE'] }))).toHaveLength(2)
  })

  it('no match returns empty', () => {
    const journals = [j({ publisher: 'ACM' })]
    expect(applyFilters(journals, filters({ publishers: ['Wiley'] }))).toHaveLength(0)
  })
})

// ─── applyFilters — area ──────────────────────────────────────────────────────

describe('applyFilters — area', () => {
  it('empty area list matches all', () => {
    const journals = [j({ area: 'Computação' }), j({ area: 'Medicina' })]
    expect(applyFilters(journals, filters({ areas: [] }))).toHaveLength(2)
  })

  it('single area match', () => {
    const journals = [j({ area: 'Computação' }), j({ area: 'Medicina' })]
    expect(applyFilters(journals, filters({ areas: ['Computação'] }))).toHaveLength(1)
  })

  it('multiple areas work as OR', () => {
    const journals = [j({ area: 'Computação' }), j({ area: 'Medicina' }), j({ area: 'Química' })]
    expect(applyFilters(journals, filters({ areas: ['Computação', 'Medicina'] }))).toHaveLength(2)
  })

  it('no match returns empty', () => {
    const journals = [j({ area: 'Computação' })]
    expect(applyFilters(journals, filters({ areas: ['Química'] }))).toHaveLength(0)
  })
})

// ─── applyFilters — qualis ────────────────────────────────────────────────────

describe('applyFilters — qualis', () => {
  it('empty qualis list matches all', () => {
    const journals = [j({ qualis_best: 'A1' }), j({ qualis_best: 'B3' })]
    expect(applyFilters(journals, filters({ qualis: [] }))).toHaveLength(2)
  })

  it('single stratum filter', () => {
    const journals = [j({ qualis_best: 'A1' }), j({ qualis_best: 'B3' }), j({ qualis_best: 'A1' })]
    expect(applyFilters(journals, filters({ qualis: ['A1'] }))).toHaveLength(2)
  })

  it('multiple strata work as OR', () => {
    const journals = [
      j({ qualis_best: 'A1' }),
      j({ qualis_best: 'A2' }),
      j({ qualis_best: 'B1' }),
    ]
    expect(applyFilters(journals, filters({ qualis: ['A1', 'A2'] }))).toHaveLength(2)
  })

  it('journal with null qualis_best excluded when filter active', () => {
    const journals = [j({ qualis_best: null }), j({ qualis_best: 'A1' })]
    expect(applyFilters(journals, filters({ qualis: ['A1'] }))).toHaveLength(1)
  })
})

// ─── applyFilters — open access type ─────────────────────────────────────────

describe('applyFilters — oa', () => {
  it('empty oa matches all', () => {
    const journals = [j({ oa: 'Hybrid' }), j({ oa: 'Full Open Access' })]
    expect(applyFilters(journals, filters({ oa: '' }))).toHaveLength(2)
  })

  it('filters by oa type', () => {
    const journals = [j({ oa: 'Hybrid' }), j({ oa: 'Full Open Access' })]
    expect(applyFilters(journals, filters({ oa: 'Full Open Access' }))).toHaveLength(1)
  })
})

// ─── applyFilters — combinations ─────────────────────────────────────────────

describe('applyFilters — combined filters (AND logic)', () => {
  const journals = [
    j({ title: 'IEEE Access',      publisher: 'IEEE',     qualis_best: 'A3', area: 'Engenharias', oa: 'Full Open Access' }),
    j({ title: 'ACM Computing',    publisher: 'ACM',      qualis_best: 'A1', area: 'Computação',  oa: 'Full Open Access' }),
    j({ title: 'Nature Medicine',  publisher: 'Springer Nature', qualis_best: 'A1', area: 'Medicina', oa: 'Hybrid' }),
    j({ title: 'Lancet',           publisher: 'Elsevier', qualis_best: 'A1', area: 'Medicina',    oa: 'Hybrid' }),
  ]

  it('publisher + qualis', () => {
    const result = applyFilters(journals, filters({ publishers: ['ACM'], qualis: ['A1'] }))
    expect(result).toHaveLength(1)
    expect(result[0].title).toBe('ACM Computing')
  })

  it('area + oa', () => {
    const result = applyFilters(journals, filters({ areas: ['Medicina'], oa: 'Hybrid' }))
    expect(result).toHaveLength(2)
  })

  it('text + publisher + qualis', () => {
    const result = applyFilters(journals, filters({ q: 'lancet', publishers: ['Elsevier'], qualis: ['A1'] }))
    expect(result).toHaveLength(1)
    expect(result[0].publisher).toBe('Elsevier')
  })

  it('all filters active, no match', () => {
    const result = applyFilters(journals, filters({
      q: 'IEEE',
      publishers: ['ACM'],  // contradicts q='IEEE'
      qualis: ['A1'],
    }))
    expect(result).toHaveLength(0)
  })

  it('empty journals array', () => {
    expect(applyFilters([], filters({ q: 'nature' }))).toHaveLength(0)
  })
})

// ─── applyFilters — quartile ─────────────────────────────────────────────────

describe('applyFilters — quartiles', () => {
  it('empty quartile list matches all', () => {
    const journals = [j({ quartile: 'Q1' }), j({ quartile: 'Q3' })]
    expect(applyFilters(journals, filters({ quartiles: [] }))).toHaveLength(2)
  })

  it('single quartile filter', () => {
    const journals = [j({ quartile: 'Q1' }), j({ quartile: 'Q2' }), j({ quartile: 'Q1' })]
    expect(applyFilters(journals, filters({ quartiles: ['Q1'] }))).toHaveLength(2)
  })

  it('multiple quartiles work as OR', () => {
    const journals = [j({ quartile: 'Q1' }), j({ quartile: 'Q2' }), j({ quartile: 'Q4' })]
    expect(applyFilters(journals, filters({ quartiles: ['Q1', 'Q2'] }))).toHaveLength(2)
  })

  it('journal with null quartile excluded when filter active', () => {
    const journals = [j({ quartile: null }), j({ quartile: 'Q1' })]
    expect(applyFilters(journals, filters({ quartiles: ['Q1'] }))).toHaveLength(1)
  })
})

// ─── applyFilters — minCites ─────────────────────────────────────────────────

describe('applyFilters — minCites', () => {
  it('null minCites matches all', () => {
    const journals = [j({ cites_per_doc: 1 }), j({ cites_per_doc: 9 })]
    expect(applyFilters(journals, filters({ minCites: null }))).toHaveLength(2)
  })

  it('filters journals below threshold', () => {
    const journals = [j({ cites_per_doc: 2 }), j({ cites_per_doc: 5 }), j({ cites_per_doc: 8 })]
    expect(applyFilters(journals, filters({ minCites: 5 }))).toHaveLength(2)
  })

  it('threshold is inclusive', () => {
    const journals = [j({ cites_per_doc: 5 })]
    expect(applyFilters(journals, filters({ minCites: 5 }))).toHaveLength(1)
  })

  it('journal with null cites excluded when threshold active', () => {
    const journals = [j({ cites_per_doc: null }), j({ cites_per_doc: 6 })]
    expect(applyFilters(journals, filters({ minCites: 1 }))).toHaveLength(1)
  })
})

// ─── sortJournals ─────────────────────────────────────────────────────────────

describe('sortJournals', () => {
  it('null sort leaves order unchanged', () => {
    const journals = [j({ id: 1, cites_per_doc: 1 }), j({ id: 2, cites_per_doc: 9 })]
    expect(sortJournals(journals, null).map(x => x.id)).toEqual([1, 2])
  })

  it('sorts by cites_per_doc descending', () => {
    const journals = [j({ id: 1, cites_per_doc: 2 }), j({ id: 2, cites_per_doc: 9 }), j({ id: 3, cites_per_doc: 5 })]
    expect(sortJournals(journals, { key: 'cites_per_doc', dir: 'desc' }).map(x => x.id)).toEqual([2, 3, 1])
  })

  it('sorts by cites_per_doc ascending', () => {
    const journals = [j({ id: 1, cites_per_doc: 2 }), j({ id: 2, cites_per_doc: 9 }), j({ id: 3, cites_per_doc: 5 })]
    expect(sortJournals(journals, { key: 'cites_per_doc', dir: 'asc' }).map(x => x.id)).toEqual([1, 3, 2])
  })

  it('nulls always sink to the bottom regardless of direction', () => {
    const journals = [j({ id: 1, cites_per_doc: null }), j({ id: 2, cites_per_doc: 9 }), j({ id: 3, cites_per_doc: 5 })]
    expect(sortJournals(journals, { key: 'cites_per_doc', dir: 'desc' }).map(x => x.id)).toEqual([2, 3, 1])
    expect(sortJournals(journals, { key: 'cites_per_doc', dir: 'asc' }).map(x => x.id)).toEqual([3, 2, 1])
  })

  it('does not mutate the input array', () => {
    const journals = [j({ id: 1, cites_per_doc: 2 }), j({ id: 2, cites_per_doc: 9 })]
    sortJournals(journals, { key: 'cites_per_doc', dir: 'desc' })
    expect(journals.map(x => x.id)).toEqual([1, 2])
  })

  it('sorts by title', () => {
    const journals = [j({ id: 1, title: 'Zebra' }), j({ id: 2, title: 'Alpha' })]
    expect(sortJournals(journals, { key: 'title', dir: 'asc' }).map(x => x.id)).toEqual([2, 1])
  })

  it('sorts by qualis_best with A1 best-first on desc', () => {
    const journals = [j({ id: 1, qualis_best: 'B2' }), j({ id: 2, qualis_best: 'A1' }), j({ id: 3, qualis_best: 'A3' })]
    expect(sortJournals(journals, { key: 'qualis_best', dir: 'desc' }).map(x => x.id)).toEqual([2, 3, 1])
    expect(sortJournals(journals, { key: 'qualis_best', dir: 'asc' }).map(x => x.id)).toEqual([1, 3, 2])
  })

  it('qualis_best nulls sink to the bottom regardless of direction', () => {
    const journals = [j({ id: 1, qualis_best: null }), j({ id: 2, qualis_best: 'A1' }), j({ id: 3, qualis_best: 'C' })]
    expect(sortJournals(journals, { key: 'qualis_best', dir: 'desc' }).map(x => x.id)).toEqual([2, 3, 1])
    expect(sortJournals(journals, { key: 'qualis_best', dir: 'asc' }).map(x => x.id)).toEqual([3, 2, 1])
  })
})

// ─── getUniqueAreas ───────────────────────────────────────────────────────────

describe('getUniqueAreas', () => {
  it('returns unique areas sorted', () => {
    const journals = [
      j({ area: 'Química' }),
      j({ area: 'Computação' }),
      j({ area: 'Química' }),  // duplicate
      j({ area: 'Medicina' }),
    ]
    const areas = getUniqueAreas(journals)
    expect(areas).toHaveLength(3)
    expect(areas[0]).toBe('Computação') // sorted pt-BR
    expect(areas).toContain('Medicina')
    expect(areas).toContain('Química')
  })

  it('ignores null areas', () => {
    const journals = [j({ area: null }), j({ area: 'Computação' })]
    expect(getUniqueAreas(journals)).toHaveLength(1)
  })

  it('empty array returns empty', () => {
    expect(getUniqueAreas([])).toHaveLength(0)
  })
})
