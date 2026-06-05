export interface QualisEntry {
  area: string
  estrato: string
}

export interface Journal {
  id: number
  title: string
  publisher: string | null
  issn: string | null
  eissn: string | null
  oa: string | null          // open_access_type
  license: string | null
  area: string | null        // primary_area
  main_discipline: string | null
  imprint: string | null
  url: string | null
  qualis_best: string | null
  impact_factor: number | null
  acronym: string | null
  // Uniform citation metrics (same source for every journal — see add_metrics.py)
  cites_per_doc: number | null   // citations/doc, 2-year window
  quartile: string | null        // SJR best quartile Q1..Q4
  sjr: number | null
  h_index: number | null
  metric_source: string | null   // "scimago" | "openalex"
  qualis: QualisEntry[]
}

export interface Filters {
  q: string       // title search
  issn: string    // ISSN / eISSN search (separate field)
  publishers: string[]
  areas: string[] // knowledge areas (multi-select)
  qualis: string[]
  quartiles: string[]   // SJR quartile (multi-select)
  minCites: number | null  // minimum cites/doc
  oa: string
}

export const EMPTY_FILTERS: Filters = {
  q: '',
  issn: '',
  publishers: [],
  areas: [],
  qualis: [],
  quartiles: [],
  minCites: null,
  oa: '',
}

export type SortKey = 'title' | 'cites_per_doc' | 'qualis_best'
export interface Sort {
  key: SortKey
  dir: 'asc' | 'desc'
}

export const PUBLISHERS = ['ACM', 'ACS', 'Elsevier', 'IEEE', 'Royal Society', 'Springer Nature', 'Wiley']

export const QUALIS_STRATA = ['A1', 'A2', 'A3', 'A4', 'B1', 'B2', 'B3', 'B4', 'C']

export const QUARTILES = ['Q1', 'Q2', 'Q3', 'Q4']

export const STRATA_COLORS: Record<string, string> = {
  A1: '#00695c',
  A2: '#1565c0',
  A3: '#6a1b9a',
  A4: '#7b1fa2',
  B1: '#e65100',
  B2: '#bf360c',
  B3: '#b71c1c',
  B4: '#880e4f',
  C:  '#616161',
}

export const PAGE_SIZE = 25
