import './styles/main.css'
import { loadData, restoreFromURL } from './store'
import { createFilterSidebar } from './components/FilterSidebar'
import { createJournalTable } from './components/JournalTable'

function buildApp(): void {
  const app = document.querySelector<HTMLDivElement>('#app')!

  app.innerHTML = `
    <!-- Header -->
    <header class="site-header">
      <div class="header-inner">
        <span class="header-logo">Periódicos <span>CAPES</span></span>
        <nav class="header-nav" aria-label="Navegação principal">
          <a href="#">Início</a>
          <a href="https://www.periodicos.capes.gov.br" target="_blank" rel="noopener noreferrer">Acervos</a>
          <a href="https://www.periodicos.capes.gov.br/index.php/acessoaberto/acordos-transformativos.html"
             target="_blank" rel="noopener noreferrer">Sobre APC</a>
        </nav>
        <a class="header-cta"
           href="https://www.periodicos.capes.gov.br"
           target="_blank"
           rel="noopener noreferrer">
          Acessar CAPES
        </a>
      </div>
    </header>

    <!-- Hero -->
    <section class="hero" aria-labelledby="hero-title">
      <div class="hero-inner">
        <h1 id="hero-title">Acordos de <em>Publicação (APC)</em></h1>
        <p>Encontre periódicos científicos com acordos de isenção de taxas de processamento de artigos para pesquisadores brasileiros vinculados às instituições participantes.</p>
        <span class="hero-stat">
          <strong id="hero-count">4.983</strong> periódicos com acordos disponíveis
        </span>
      </div>
    </section>

    <!-- Main content -->
    <div class="main-layout" id="main-layout"></div>

    <!-- Footer -->
    <footer class="site-footer">
      <p>Dados: <a href="https://www.periodicos.capes.gov.br" target="_blank" rel="noopener noreferrer">CAPES Periódicos</a>
         &middot; Qualis: <a href="https://sucupira-legado.capes.gov.br" target="_blank" rel="noopener noreferrer">Sucupira</a>
      </p>
      <p class="footer-disclaimer">
        <strong>Isenção de Responsabilidade:</strong> Esta página é um projeto voluntário e não oficial.
        Não tem ligação, suporte ou relação com a CAPES. Os dados são informativos e baseados em fontes
        públicas. Validar as informações diretamente na plataforma oficial da CAPES antes de submeterem
        seus artigos.
      </p>
    </footer>
  `

  // Mount components into layout
  const layout = app.querySelector<HTMLDivElement>('#main-layout')!
  layout.appendChild(createFilterSidebar())
  layout.appendChild(createJournalTable())
}

// Bootstrap
restoreFromURL()
buildApp()
loadData()
