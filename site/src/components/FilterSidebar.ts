import { getState, setFilters, clearFilters, subscribe } from '../store'
import type { Filters } from '../types'
import { PUBLISHERS, QUALIS_STRATA } from '../types'

export function createFilterSidebar(): HTMLElement {
  const sidebar = document.createElement('aside')
  sidebar.className = 'filter-sidebar'
  sidebar.setAttribute('aria-label', 'Filtros de pesquisa')

  sidebar.innerHTML = `
    <div class="filter-header">
      <h2>Filtros</h2>
      <button class="btn-clear" type="button" id="btn-clear-filters">Limpar</button>
    </div>
    <search>
      <div class="filter-body">

        <div class="filter-group">
          <label class="filter-label" for="filter-q">Nome do Periódico</label>
          <input
            class="filter-input"
            type="search"
            id="filter-q"
            name="q"
            placeholder="Ex: Nature, IEEE..."
            autocomplete="off"
          />
        </div>

        <div class="filter-group">
          <label class="filter-label" for="filter-issn">ISSN ou e-ISSN</label>
          <input
            class="filter-input"
            type="text"
            id="filter-issn"
            name="issn"
            placeholder="0000-0000"
            maxlength="9"
          />
        </div>

        <div class="filter-group">
          <span class="filter-label">Editora</span>
          <div class="checkbox-group" id="publisher-checkboxes">
            ${PUBLISHERS.map(p => `
              <label class="checkbox-label">
                <input type="checkbox" name="publisher" value="${p}" />
                ${p}
              </label>
            `).join('')}
          </div>
        </div>

        <div class="filter-group">
          <span class="filter-label" id="area-label">Área do Conhecimento</span>
          <div class="multiselect" id="area-multiselect">
            <button
              type="button"
              class="filter-input multiselect-toggle"
              id="area-toggle"
              aria-haspopup="listbox"
              aria-expanded="false"
              aria-labelledby="area-label area-toggle-text"
            >
              <span class="multiselect-toggle-text" id="area-toggle-text">Todas as Áreas</span>
              <span class="multiselect-caret" aria-hidden="true">▾</span>
            </button>
            <div class="multiselect-panel" id="area-panel" role="listbox" aria-multiselectable="true" hidden>
              <input
                type="search"
                class="multiselect-search"
                id="area-search"
                placeholder="Buscar área…"
                autocomplete="off"
                aria-label="Buscar área do conhecimento"
              />
              <div class="multiselect-options" id="area-options"></div>
            </div>
          </div>
        </div>

        <div class="filter-group">
          <label class="filter-label" for="filter-oa">Tipo de Acesso</label>
          <select class="filter-input" id="filter-oa" name="oa">
            <option value="">Todos</option>
            <option value="Full Open Access">Full Open Access</option>
            <option value="Hybrid">Híbrido</option>
            <option value="Diamond Open Access">Diamond Open Access</option>
          </select>
        </div>

        <div class="filter-group">
          <span class="filter-label">Qualis</span>
          <div class="qualis-chips" id="qualis-chips" role="group" aria-label="Filtro por estrato Qualis">
            ${QUALIS_STRATA.map(s => `
              <button
                class="qualis-chip"
                type="button"
                data-stratum="${s}"
                aria-pressed="false"
              >${s}</button>
            `).join('')}
          </div>
        </div>

      </div>
    </search>

    <div class="faq-card">
      <h3>Dúvidas sobre APC?</h3>
      <p>Saiba como publicar em acesso aberto sem custos através dos acordos CAPES.</p>
      <a href="https://www.periodicos.capes.gov.br/index.php/acessoaberto/acordos-transformativos.html"
         target="_blank" rel="noopener noreferrer">Ver FAQ</a>
    </div>
  `

  // ── Wire up events ─────────────────────────────────────────────────────────

  let debounceTimer: ReturnType<typeof setTimeout>

  // Text search (debounced)
  const qInput = sidebar.querySelector<HTMLInputElement>('#filter-q')!
  qInput.addEventListener('input', () => {
    clearTimeout(debounceTimer)
    debounceTimer = setTimeout(() => {
      setFilters({ q: qInput.value.trim() })
    }, 200)
  })

  // ISSN search (debounced) — separate from title search
  const issnInput = sidebar.querySelector<HTMLInputElement>('#filter-issn')!
  issnInput.addEventListener('input', () => {
    clearTimeout(debounceTimer)
    debounceTimer = setTimeout(() => {
      setFilters({ issn: issnInput.value.trim() })
    }, 200)
  })

  // Publisher checkboxes
  const pubCheckboxes = sidebar.querySelectorAll<HTMLInputElement>('input[name="publisher"]')
  pubCheckboxes.forEach(cb => {
    cb.addEventListener('change', () => {
      const selected = Array.from(pubCheckboxes)
        .filter(c => c.checked)
        .map(c => c.value)
      setFilters({ publishers: selected })
    })
  })

  // Area multi-select — populated once data loads
  const areaToggle = sidebar.querySelector<HTMLButtonElement>('#area-toggle')!
  const areaToggleText = sidebar.querySelector<HTMLSpanElement>('#area-toggle-text')!
  const areaPanel = sidebar.querySelector<HTMLDivElement>('#area-panel')!
  const areaSearch = sidebar.querySelector<HTMLInputElement>('#area-search')!
  const areaOptions = sidebar.querySelector<HTMLDivElement>('#area-options')!

  function openAreaPanel(): void {
    areaPanel.hidden = false
    areaToggle.setAttribute('aria-expanded', 'true')
    areaSearch.value = ''
    filterAreaOptions('')
    areaSearch.focus()
  }

  function closeAreaPanel(): void {
    areaPanel.hidden = true
    areaToggle.setAttribute('aria-expanded', 'false')
  }

  areaToggle.addEventListener('click', () => {
    if (areaPanel.hidden) openAreaPanel()
    else closeAreaPanel()
  })

  // Close on outside click / Escape
  document.addEventListener('click', e => {
    if (!areaPanel.hidden && !sidebar.querySelector('#area-multiselect')!.contains(e.target as Node)) {
      closeAreaPanel()
    }
  })
  areaPanel.addEventListener('keydown', e => {
    if (e.key === 'Escape') { closeAreaPanel(); areaToggle.focus() }
  })

  function filterAreaOptions(query: string): void {
    const n = query.trim().toLowerCase()
    areaOptions.querySelectorAll<HTMLLabelElement>('.multiselect-option').forEach(opt => {
      const match = !n || opt.dataset.area!.toLowerCase().includes(n)
      opt.hidden = !match
    })
  }

  areaSearch.addEventListener('input', () => filterAreaOptions(areaSearch.value))

  // Checkbox changes inside the options panel
  areaOptions.addEventListener('change', () => {
    const selected = Array.from(
      areaOptions.querySelectorAll<HTMLInputElement>('input[type="checkbox"]:checked')
    ).map(c => c.value)
    setFilters({ areas: selected })
  })

  // OA type select
  const oaSelect = sidebar.querySelector<HTMLSelectElement>('#filter-oa')!
  oaSelect.addEventListener('change', () => {
    setFilters({ oa: oaSelect.value })
  })

  // Qualis chips
  const chips = sidebar.querySelectorAll<HTMLButtonElement>('.qualis-chip')
  chips.forEach(chip => {
    chip.addEventListener('click', () => {
      const stratum = chip.dataset.stratum!
      const state = getState()
      const current = state.filters.qualis
      const next = current.includes(stratum)
        ? current.filter(s => s !== stratum)
        : [...current, stratum]
      setFilters({ qualis: next })
    })
  })

  // Clear button
  sidebar.querySelector('#btn-clear-filters')!.addEventListener('click', () => {
    clearFilters()
  })

  // ── Sync UI from store ─────────────────────────────────────────────────────

  function syncUI(filters: Filters): void {
    qInput.value = filters.q
    issnInput.value = filters.issn

    pubCheckboxes.forEach(cb => {
      cb.checked = filters.publishers.includes(cb.value)
    })

    // Area multi-select
    areaOptions.querySelectorAll<HTMLInputElement>('input[type="checkbox"]').forEach(cb => {
      cb.checked = filters.areas.includes(cb.value)
    })
    const count = filters.areas.length
    areaToggleText.textContent =
      count === 0 ? 'Todas as Áreas'
      : count === 1 ? filters.areas[0]
      : `${count} áreas selecionadas`
    areaToggle.classList.toggle('has-selection', count > 0)

    oaSelect.value = filters.oa

    chips.forEach(chip => {
      const active = filters.qualis.includes(chip.dataset.stratum!)
      chip.classList.toggle('active', active)
      chip.setAttribute('aria-pressed', String(active))
    })
  }

  // Populate areas when data loads
  subscribe(() => {
    const { areas, filters } = getState()
    if (areas.length > 0 && areaOptions.children.length === 0) {
      const frag = document.createDocumentFragment()
      areas.forEach(a => {
        const label = document.createElement('label')
        label.className = 'multiselect-option'
        label.dataset.area = a
        label.setAttribute('role', 'option')
        label.innerHTML = `<input type="checkbox" value="${escAttr(a)}" />${escHtml(a)}`
        frag.appendChild(label)
      })
      areaOptions.appendChild(frag)
    }
    syncUI(filters)
  })

  return sidebar
}

function escHtml(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

function escAttr(str: string): string {
  return escHtml(str).replace(/"/g, '&quot;')
}
