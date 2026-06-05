import type { Journal } from '../types'
import { STRATA_COLORS } from '../types'

let dialog: HTMLDialogElement | null = null

function getDialog(): HTMLDialogElement {
  if (dialog) return dialog

  dialog = document.createElement('dialog')
  dialog.setAttribute('aria-modal', 'true')
  dialog.setAttribute('aria-labelledby', 'dialog-title')
  document.body.appendChild(dialog)

  // Close on backdrop click
  dialog.addEventListener('click', (e) => {
    if (e.target === dialog) dialog!.close()
  })

  // Close on Escape (native dialog handles this)
  return dialog
}

function oaLabel(oa: string | null): string {
  if (!oa) return '—'
  if (oa.toLowerCase().includes('full') || oa.toLowerCase().includes('diamond')) return oa
  return oa
}

function impactText(v: number | null): string {
  if (v == null) return '—'
  return v.toFixed(3)
}

function qualisColor(stratum: string): string {
  return STRATA_COLORS[stratum] ?? '#616161'
}

// Small provenance hint next to the citation metric (Scimago vs OpenAlex).
function sourceTag(src: string | null): string {
  if (!src) return ''
  const label = src === 'scimago' ? 'Scimago' : src === 'openalex' ? 'OpenAlex' : src
  return ` <span class="metric-source" title="Fonte da métrica">· ${label}</span>`
}

export function showJournalDetail(journal: Journal): void {
  const dlg = getDialog()

  const qualisRows = journal.qualis.length > 0
    ? journal.qualis
        .sort((a, b) => a.area.localeCompare(b.area, 'pt'))
        .map(q => `
          <tr>
            <td>${q.area}</td>
            <td>
              <span class="qualis-badge" data-stratum="${q.estrato}"
                    style="background:${qualisColor(q.estrato)}">
                ${q.estrato}
              </span>
            </td>
          </tr>
        `).join('')
    : '<tr><td colspan="2" style="color:var(--on-surface-variant);padding:0.5rem 0;">Sem classificação Qualis disponível</td></tr>'

  const urlBtn = journal.url
    ? `<a href="${journal.url}" target="_blank" rel="noopener noreferrer"
           class="btn-primary" style="display:inline-flex;align-items:center;gap:0.375rem;text-decoration:none;">
         <span>Acessar periódico</span>
         <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15,3 21,3 21,9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
       </a>`
    : ''

  dlg.innerHTML = `
    <div class="dialog-header">
      <div class="dialog-header-content">
        <h2 id="dialog-title">${escHtml(journal.title)}</h2>
        <span class="dialog-publisher">${escHtml(journal.imprint ?? journal.publisher ?? '')}</span>
      </div>
      <button class="dialog-close" type="button" aria-label="Fechar">×</button>
    </div>

    <div class="dialog-body">

      <div class="dialog-meta-grid">
        <div class="meta-item">
          <label>ISSN (print)</label>
          <span>${journal.issn ?? '—'}</span>
        </div>
        <div class="meta-item">
          <label>e-ISSN</label>
          <span>${journal.eissn ?? '—'}</span>
        </div>
        <div class="meta-item">
          <label>Área Principal</label>
          <span style="font-family:var(--font-body);font-size:0.875rem">${escHtml(journal.area ?? '—')}</span>
        </div>
        <div class="meta-item">
          <label>Melhor Qualis</label>
          <span>
            ${journal.qualis_best
              ? `<span class="qualis-badge" data-stratum="${journal.qualis_best}"
                       style="background:${qualisColor(journal.qualis_best)}">${journal.qualis_best}</span>`
              : '—'}
          </span>
        </div>
        <div class="meta-item">
          <label>Tipo de Acesso</label>
          <span style="font-family:var(--font-body);font-size:0.875rem">${escHtml(oaLabel(journal.oa))}</span>
        </div>
        <div class="meta-item">
          <label>Licença</label>
          <span style="font-family:var(--font-body);font-size:0.875rem">${escHtml(journal.license ?? '—')}</span>
        </div>
        <div class="meta-item">
          <label>Cites/doc (2 anos)${sourceTag(journal.metric_source)}</label>
          <span style="font-family:var(--font-body)">${journal.cites_per_doc != null ? journal.cites_per_doc.toFixed(2) : '—'}</span>
        </div>
        <div class="meta-item">
          <label>Quartil (SJR)</label>
          <span>${journal.quartile ? `<span class="quartile-badge" data-quartile="${journal.quartile}">${journal.quartile}</span>` : '—'}</span>
        </div>
        <div class="meta-item">
          <label>SJR</label>
          <span style="font-family:var(--font-body)">${journal.sjr != null ? journal.sjr.toFixed(3) : '—'}</span>
        </div>
        <div class="meta-item">
          <label>h-index</label>
          <span style="font-family:var(--font-body)">${journal.h_index ?? '—'}</span>
        </div>
        ${journal.impact_factor != null ? `
        <div class="meta-item">
          <label>Impact Factor (oficial)</label>
          <span style="font-family:var(--font-body)">${impactText(journal.impact_factor)}</span>
        </div>` : ''}
        <div class="meta-item">
          <label>Editora</label>
          <span style="font-family:var(--font-body);font-size:0.875rem">${escHtml(journal.publisher ?? '—')}</span>
        </div>
      </div>

      ${journal.qualis.length > 0 ? `
      <div>
        <p class="dialog-section-title">Classificações Qualis por Área</p>
        <table class="qualis-area-table">
          <tbody>${qualisRows}</tbody>
        </table>
      </div>` : ''}

    </div>

    <div class="dialog-footer">
      <button class="btn-detail" type="button" id="dialog-close-btn">Fechar</button>
      ${urlBtn}
    </div>
  `

  dlg.querySelector('.dialog-close')!.addEventListener('click', () => dlg.close())
  dlg.querySelector('#dialog-close-btn')!.addEventListener('click', () => dlg.close())

  dlg.showModal()
}

function escHtml(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}
