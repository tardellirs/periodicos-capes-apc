import type { Journal, Filters } from './types'

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
    if (filters.oa && j.oa !== filters.oa) return false
    return true
  })
}

export function getUniqueAreas(journals: Journal[]): string[] {
  const areas = new Set(journals.map(j => j.area).filter(Boolean) as string[])
  return Array.from(areas).sort((a, b) => a.localeCompare(b, 'pt'))
}
