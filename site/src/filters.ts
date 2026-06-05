import type { Journal, Filters, Sort, SortKey } from './types'
import { QUALIS_STRATA } from './types'

function normalize(s: string): string {
  return s.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')
}

function matchesText(j: Journal, q: string): boolean {
  if (!q) return true
  const n = normalize(q)
  return (
    normalize(j.title).includes(n) ||
    (j.issn != null && j.issn.replace('-', '').includes(q.replace('-', ''))) ||
    (j.eissn != null && j.eissn.replace('-', '').includes(q.replace('-', '')))
  )
}

function matchesISSN(j: Journal, issn: string): boolean {
  if (!issn) return true
  const clean = issn.replace(/-/g, '').toLowerCase()
  return (
    (j.issn != null && j.issn.replace(/-/g, '').toLowerCase().includes(clean)) ||
    (j.eissn != null && j.eissn.replace(/-/g, '').toLowerCase().includes(clean))
  )
}

export function applyFilters(journals: Journal[], filters: Filters): Journal[] {
  return journals.filter(j => {
    if (!matchesText(j, filters.q)) return false
    if (!matchesISSN(j, filters.issn)) return false
    if (filters.publishers.length > 0 && !filters.publishers.includes(j.publisher ?? '')) return false
    if (filters.areas.length > 0 && !filters.areas.includes(j.area ?? '')) return false
    if (filters.qualis.length > 0 && !filters.qualis.includes(j.qualis_best ?? '')) return false
    if (filters.quartiles.length > 0 && !filters.quartiles.includes(j.quartile ?? '')) return false
    if (filters.minCites != null && (j.cites_per_doc == null || j.cites_per_doc < filters.minCites)) return false
    if (filters.oa && j.oa !== filters.oa) return false
    return true
  })
}

// Numeric sort value for a journal under a given key. Higher = "better", so
// 'desc' (the first click) always surfaces the strongest journals first:
// highest cites/doc, or best Qualis (A1). null = no value (sinks to bottom).
function sortValue(j: Journal, key: SortKey): number | null {
  if (key === 'cites_per_doc') return j.cites_per_doc
  if (key === 'qualis_best') {
    if (!j.qualis_best) return null
    const idx = QUALIS_STRATA.indexOf(j.qualis_best)
    return idx === -1 ? null : QUALIS_STRATA.length - idx  // A1 → highest
  }
  return null
}

// Sort a (already filtered) list. Journals missing the sort value sink to the
// bottom regardless of direction, so a sorted column never surfaces nulls.
export function sortJournals(journals: Journal[], sort: Sort | null): Journal[] {
  if (!sort) return journals
  const dir = sort.dir === 'asc' ? 1 : -1
  return [...journals].sort((a, b) => {
    if (sort.key === 'title') return a.title.localeCompare(b.title, 'pt') * dir
    const av = sortValue(a, sort.key)
    const bv = sortValue(b, sort.key)
    if (av == null && bv == null) return 0
    if (av == null) return 1
    if (bv == null) return -1
    return (av - bv) * dir
  })
}

export function getUniqueAreas(journals: Journal[]): string[] {
  const areas = new Set(journals.map(j => j.area).filter(Boolean) as string[])
  return Array.from(areas).sort((a, b) => a.localeCompare(b, 'pt'))
}
