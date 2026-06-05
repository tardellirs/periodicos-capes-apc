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
  qualis: QualisEntry[]
}

export interface Filters {
  q: string       // title search
  issn: string    // ISSN / eISSN search (separate field)
  publishers: string[]
  areas: string[] // knowledge areas (multi-select)
  qualis: string[]
  oa: string
}

export const EMPTY_FILTERS: Filters = {
  q: '',
  issn: '',
  publishers: [],
  areas: [],
  qualis: [],
  oa: '',
}

export const PUBLISHERS = ['ACM', 'ACS', 'Elsevier', 'IEEE', 'Royal Society', 'Springer Nature', 'Wiley']

export const QUALIS_STRATA = ['A1', 'A2', 'A3', 'A4', 'B1', 'B2', 'B3', 'B4', 'C']

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
