import { getState, getPage, getTotalPages, setPage, subscribe } from '../store'
import type { Journal } from '../types'
import { showJournalDetail } from './Modal'

function oaBadge(oa: string | null): string {
  if (!oa) return ''
  const lower = oa.toLowerCase()
  if (lower.includes('diamond')) return `<span class="oa-badge diamond">Diamond OA</span>`
  if (lower.includes('full')) return `<span class="oa-badge full">Full OA</span>`
  return `<span class="oa-badge hybrid">Híbrido</span>`
}

function qualisBadge(stratum: string | null): string {
  if (!stratum) return '—'
  return `<span class="qualis-badge" data-stratum="${stratum}">${stratum}</span>`
}

function renderRow(j: Journal): HTMLTableRowElement {
  const tr = document.createElement('tr')
  tr.innerHTML = `
    <td class="journal-title-cell">
      <div class="journal-title" title="${escHtml(j.title)}">${escHtml(j.title)}</div>
      <div class="journal-issn">${j.issn ?? j.eissn ?? ''}</div>
    </td>
    <td><span class="publisher-chip">${escHtml(j.imprint ?? j.publisher ?? '—')}</span></td>
    <td><span class="area-text" title="${escHtml(j.area ?? '')}">${escHtml(j.area ?? '—')}</span></td>
    <td>${oaBadge(j.oa)}</td>
    <td>${qualisBadge(j.qualis_best)}</td>
    <td class="td-actions">
      <button class="btn-detail" type="button" data-journal-id="${j.id}">Ver detalhes</button>
    </td>
  `
  tr.querySelector('.btn-detail')!.addEventListener('click', () => showJournalDetail(j))
  return tr
}

function renderPagination(container: HTMLElement, page: number, total: number): void {
  container.innerHTML = ''
  if (total <= 1) return

  const MAX_VISIBLE = 7

  function btn(label: string, p: number, active = false, disabled = false): HTMLButtonElement {
    const b = document.createElement('button')
    b.className = `page-btn${active ? ' active' : ''}`
    b.textContent = label
    b.disabled = disabled
    b.setAttribute('aria-label', `Página ${p}`)
    if (active) b.setAttribute('aria-current', 'page')
    if (!disabled && !active) b.addEventListener('click', () => setPage(p))
    return b
  }

  // Prev — separate aria-label so it doesn't clash with numbered buttons
  const prevBtn = btn('‹', page - 1, false, page === 1)
  prevBtn.setAttribute('aria-label', 'Página anterior')
  container.appendChild(prevBtn)

  if (total <= MAX_VISIBLE) {
    for (let i = 1; i <= total; i++) container.appendChild(btn(String(i), i, i === page))
  } else {
    const pages: (number | null)[] = []
    pages.push(1)
    if (page > 3) pages.push(null)
    for (let i = Math.max(2, page - 1); i <= Math.min(total - 1, page + 1); i++) pages.push(i)
    if (page < total - 2) pages.push(null)
    pages.push(total)

    pages.forEach(p => {
      if (p === null) {
        const ellipsis = document.createElement('span')
        ellipsis.className = 'page-ellipsis'
        ellipsis.textContent = '…'
        container.appendChild(ellipsis)
      } else {
        container.appendChild(btn(String(p), p, p === page))
      }
    })
  }

  // Next — separate aria-label
  const nextBtn = btn('›', page + 1, false, page === total)
  nextBtn.setAttribute('aria-label', 'Próxima página')
  container.appendChild(nextBtn)
}

export function createJournalTable(): HTMLElement {
  const wrapper = document.createElement('section')
  wrapper.className = 'catalog-section'
  wrapper.setAttribute('aria-label', 'Lista de periódicos')

  wrapper.innerHTML = `
    <div class="catalog-header">
      <h2 id="catalog-title">Explorar Periódicos</h2>
      <div style="display:flex;align-items:center;gap:1rem;">
        <p class="catalog-meta" aria-live="polite" id="catalog-count"></p>
      </div>
    </div>

    <div class="table-wrapper">
      <table class="journal-table" aria-labelledby="catalog-title">
        <thead>
          <tr>
            <th scope="col">Periódico</th>
            <th scope="col">Editora</th>
            <th scope="col">Área</th>
            <th scope="col">Acesso</th>
            <th scope="col">Qualis</th>
            <th scope="col">Ações</th>
          </tr>
        </thead>
        <tbody id="journal-tbody"></tbody>
      </table>
      <div id="table-state-msg" class="table-state" hidden></div>
    </div>

    <nav class="pagination" id="pagination" aria-label="Paginação"></nav>
  `

  const tbody = wrapper.querySelector<HTMLTableSectionElement>('#journal-tbody')!
  const stateMsg = wrapper.querySelector<HTMLDivElement>('#table-state-msg')!
  const countEl = wrapper.querySelector<HTMLParagraphElement>('#catalog-count')!
  const paginationEl = wrapper.querySelector<HTMLElement>('#pagination')!

  function render(): void {
    const state = getState()

    // Loading state
    if (state.loading) {
      tbody.innerHTML = ''
      stateMsg.hidden = false
      stateMsg.innerHTML = `<div class="spinner" aria-hidden="true"></div><p>Carregando periódicos…</p>`
      return
    }

    // Error state
    if (state.error) {
      stateMsg.hidden = false
      stateMsg.innerHTML = `<p>Erro ao carregar dados. <a href=".">Recarregar</a></p>`
      return
    }

    stateMsg.hidden = true

    // Update count
    const total = state.filtered.length
    const all = state.all.length
    if (total === all) {
      countEl.innerHTML = `<strong>${all.toLocaleString('pt-BR')}</strong> periódicos disponíveis`
    } else {
      countEl.innerHTML = `<strong>${total.toLocaleString('pt-BR')}</strong> de ${all.toLocaleString('pt-BR')} periódicos`
    }

    // Render page rows
    const page = getPage()
    const fragment = document.createDocumentFragment()

    if (page.length === 0) {
      tbody.innerHTML = ''
      stateMsg.hidden = false
      stateMsg.innerHTML = `<p>Nenhum periódico encontrado com os filtros selecionados.</p>`
      paginationEl.innerHTML = ''
      return
    }

    page.forEach(j => fragment.appendChild(renderRow(j)))
    tbody.replaceChildren(fragment)

    // Pagination
    renderPagination(paginationEl, state.page, getTotalPages())
  }

  subscribe(render)
  return wrapper
}

function escHtml(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}
