import type { Journal, Filters } from './types'
import { EMPTY_FILTERS, PAGE_SIZE } from './types'
import { applyFilters, getUniqueAreas } from './filters'

type Listener = () => void

interface State {
  all: Journal[]
  filtered: Journal[]
  areas: string[]
  filters: Filters
  page: number
  loading: boolean
  error: string | null
}

const state: State = {
  all: [],
  filtered: [],
  areas: [],
  filters: { ...EMPTY_FILTERS },
  page: 1,
  loading: true,
  error: null,
}

const listeners = new Set<Listener>()

function notify(): void {
  listeners.forEach(fn => fn())
}

export function subscribe(fn: Listener): () => void {
  listeners.add(fn)
  return () => listeners.delete(fn)
}

export function getState(): Readonly<State> {
  return state
}

export function getPage(): Journal[] {
  const start = (state.page - 1) * PAGE_SIZE
  return state.filtered.slice(start, start + PAGE_SIZE)
}

export function getTotalPages(): number {
  return Math.max(1, Math.ceil(state.filtered.length / PAGE_SIZE))
}

export async function loadData(): Promise<void> {
  try {
    const res = await fetch('./data.json')
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data: Journal[] = await res.json()
    state.all = data
    state.areas = getUniqueAreas(data)
    state.filtered = data
    state.loading = false
  } catch (err) {
    state.loading = false
    state.error = String(err)
  }
  notify()
}

export function setFilters(partial: Partial<Filters>): void {
  Object.assign(state.filters, partial)
  state.page = 1
  state.filtered = applyFilters(state.all, state.filters)
  syncURL()
  notify()
}

export function setPage(page: number): void {
  state.page = Math.max(1, Math.min(page, getTotalPages()))
  if (typeof window !== 'undefined') window.scrollTo({ top: 0, behavior: 'smooth' })
  syncURL()
  notify()
}

export function clearFilters(): void {
  state.filters = { ...EMPTY_FILTERS }
  state.page = 1
  state.filtered = state.all
  syncURL()
  notify()
}

// ─── URL sync ────────────────────────────────────────────────────────────────

function syncURL(): void {
  const params = new URLSearchParams()
  const f = state.filters
  if (f.q) params.set('q', f.q)
  if (f.issn) params.set('issn', f.issn)
  if (f.publishers.length) params.set('pub', f.publishers.join(','))
  if (f.areas.length) params.set('area', f.areas.join('~'))
  if (f.qualis.length) params.set('qualis', f.qualis.join(','))
  if (f.oa) params.set('oa', f.oa)
  if (state.page > 1) params.set('page', String(state.page))
  const qs = params.toString()
  history.replaceState(null, '', qs ? `?${qs}` : location.pathname)
}

export function restoreFromURL(): void {
  const params = new URLSearchParams(location.search)
  state.filters = {
    q: params.get('q') ?? '',
    issn: params.get('issn') ?? '',
    publishers: params.get('pub') ? params.get('pub')!.split(',') : [],
    areas: params.get('area') ? params.get('area')!.split('~') : [],
    qualis: params.get('qualis') ? params.get('qualis')!.split(',') : [],
    oa: params.get('oa') ?? '',
  }
  state.page = parseInt(params.get('page') ?? '1', 10)
}
