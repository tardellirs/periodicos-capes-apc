<div align="center">

# 📚 Portal de Periódicos APC — Acordos CAPES

**Catálogo pesquisável de periódicos científicos elegíveis para publicação em acesso aberto sem custo de APC, sob os acordos transformativos da CAPES.**

### 🌐 [periodicos.ifsp.dev](https://periodicos.ifsp.dev)

[![Site](https://img.shields.io/badge/Acessar-periodicos.ifsp.dev-001e40?logo=googlechrome&logoColor=white)](https://periodicos.ifsp.dev)
[![Frontend](https://img.shields.io/badge/Frontend-TypeScript%20%2B%20Vite-3178C6?logo=typescript&logoColor=white)](#frontend)
[![Pipeline](https://img.shields.io/badge/Pipeline-Python%203-3776AB?logo=python&logoColor=white)](#pipeline-de-dados)
[![Banco](https://img.shields.io/badge/Banco-SQLite-003B57?logo=sqlite&logoColor=white)](#pipeline-de-dados)
[![Testes](https://img.shields.io/badge/Testes-Vitest%20%2B%20Playwright-6E9F18?logo=vitest&logoColor=white)](#testes)
[![Status](https://img.shields.io/badge/Projeto-Voluntário%20e%20não%20oficial-orange)](#-isenção-de-responsabilidade)

</div>

---

## Sobre o projeto

A CAPES firmou **acordos transformativos** com grandes editoras científicas que permitem a pesquisadores vinculados a instituições brasileiras participantes publicarem em **acesso aberto sem pagar a taxa de processamento de artigo (APC — _Article Processing Charge_)**.

Essas listas, porém, estão espalhadas em PDFs e planilhas de difícil consulta. Este projeto **consolida e cruza** esses dados em um catálogo único, rápido e pesquisável, enriquecido com a **classificação Qualis** de cada periódico por área de avaliação.

> **4.983 periódicos** de **7 editoras**, com **23.785 classificações Qualis** por área.

| Editora | Periódicos |
| --- | ---: |
| Springer Nature | 1.715 |
| Elsevier | 1.616 |
| Wiley | 1.296 |
| IEEE | 222 |
| ACM | 73 |
| ACS | 51 |
| Royal Society | 10 |

## ✨ Funcionalidades

- 🔎 **Busca instantânea** por nome do periódico e por ISSN / e-ISSN (insensível a acentuação).
- 🎚️ **Filtros combináveis** por editora, área do conhecimento (multi-seleção), estrato Qualis e tipo de acesso aberto.
- 🏷️ **Detalhes por periódico** em modal: ISSNs, licença, fator de impacto, melhor Qualis e classificação completa por área.
- 🔗 **Estado na URL** — qualquer combinação de filtros gera um link compartilhável.
- ⚡ **100% client-side** — os dados são carregados uma vez e toda a filtragem acontece no navegador, sem backend.

## 🏗️ Arquitetura

O repositório tem duas metades independentes:

```
acordos-capes/
├── scripts/        # Pipeline de dados em Python (extração → enriquecimento → carga)
├── data/
│   ├── 00_raw/     # Fontes originais: PDFs e planilhas das editoras + Qualis
│   └── 01_processed/  # JSONs intermediários por editora + all_journals.json
├── acordos.db      # Banco SQLite gerado pela pipeline
└── site/           # Aplicação web (TypeScript + Vite)
    ├── src/
    └── public/data.json   # Snapshot exportado do banco, consumido pelo site
```

O banco de dados existe apenas para **produzir o `site/public/data.json`**. A aplicação web não consulta o banco em tempo de execução.

```
PDFs / XLSX / Web  →  scripts de extração  →  all_journals.json
                                                    │
                              enriquecimento (área + Qualis)
                                                    │
                                              acordos.db (SQLite)
                                                    │
                                          site/public/data.json
                                                    │
                                            Aplicação web (Vite)
```

---

## 🚀 Começando

### Pré-requisitos

- **Node.js** 18+ (para o frontend)
- **Python** 3.10+ (apenas se for reprocessar os dados)

### Frontend

```bash
cd site
npm install
npm run dev        # servidor de desenvolvimento (http://localhost:5173)
npm run build      # build de produção em site/dist/
npm run preview    # serve o build de produção localmente
```

O site já vem com o `public/data.json` versionado, então **não é necessário rodar a pipeline** para desenvolver a interface.

### Pipeline de dados

Necessária apenas para regenerar o catálogo a partir das fontes.

> **Nota:** os arquivos-fonte originais (PDFs das editoras e planilhas Qualis) **não são redistribuídos** neste repositório por serem material de terceiros. Para reprocessar, obtenha-os nas [fontes oficiais](#-fontes-de-dados) e coloque-os em `data/00_raw/`. Defina também `CONTACT_EMAIL` no ambiente para entrar no _polite pool_ da CrossRef ao rodar o extrator da ACS.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r scripts/requirements.txt
export CONTACT_EMAIL="seu-email@exemplo.org"   # opcional (etiqueta CrossRef)
```

Execute os passos a partir da raiz do repositório, na ordem:

| # | Comando | O que faz |
| --- | --- | --- |
| 1 | `python scripts/extract_journals.py` | Extrai ACM, IEEE, Springer Nature e Royal Society dos PDFs |
| 2 | `python scripts/extract_acs.py` | Extrai ACS (PDF + enriquecimento via CrossRef) |
| 3 | `python scripts/extract_elsevier.py` | Extrai Elsevier (coleta web) |
| 4 | `python scripts/extract_wiley.py` | Extrai Wiley (planilha `Wiley.xlsx`) |
| 5 | `python scripts/add_primary_area.py` | Mapeia cada periódico para uma área CAPES |
| 6 | `python scripts/download_qualis_areas.py` | Baixa as planilhas Qualis por área |
| 7 | `python scripts/link_qualis.py` | Cruza periódicos com seus estratos Qualis |
| 8 | `python scripts/load_to_db.py` | Carrega `all_journals.json` no `acordos.db` |
| 9 | `python scripts/export_site_data.py` | Exporta o banco para `site/public/data.json` |

> Para adicionar uma nova editora, escreva uma função `extract_*()` e registre-a em `main()` de `extract_journals.py` (ou crie um script dedicado seguindo a mesma estrutura de JSON), depois rode os passos de enriquecimento em diante.

---

## 🧪 Testes

A partir de `site/`:

```bash
npm test                         # testes unitários (Vitest)
npm run test:watch               # modo watch
npm run test:coverage            # cobertura
npm run test:e2e                 # testes end-to-end (Playwright)

npx vitest run src/filters.test.ts            # um arquivo
npx vitest run -t "multiple areas work"       # um teste por nome
npx playwright test -g "filters by area"      # um e2e por nome
```

A lógica de negócio (filtragem, estado) concentra-se em `src/filters.ts` e `src/store.ts` e é coberta por testes unitários; os componentes de UI são validados pelos testes e2e.

## 🛠️ Stack

| Camada | Tecnologias |
| --- | --- |
| Frontend | TypeScript, Vite, CSS puro (design tokens), Web Components nativos (`<dialog>`) |
| Estado | Store observável próprio (sem framework) |
| Testes | Vitest (unitário), Playwright (e2e) |
| Pipeline | Python, pdfplumber, openpyxl, pandas |
| Dados | SQLite (FTS5) → JSON estático |

## 📊 Fontes de dados

- **Acordos APC:** páginas e documentos públicos da [CAPES Periódicos](https://www.periodicos.capes.gov.br) e das editoras participantes.
- **Qualis:** classificações da plataforma [Sucupira](https://sucupira-legado.capes.gov.br).

---

## ⚠️ Isenção de Responsabilidade

Esta página é um **projeto voluntário e não oficial**. Não tem ligação, suporte ou relação com a CAPES. Os dados são informativos e baseados em fontes públicas. **Valide as informações diretamente na plataforma oficial da CAPES antes de submeter seus artigos.**

## 📄 Licença

Distribuído sem fins lucrativos para fins informativos e educacionais. Os dados pertencem às suas respectivas fontes (CAPES e editoras).
