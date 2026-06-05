"""
Download Qualis 2021-2024 XLS per area from Sucupira CAPES.
Flow per area:
  1. GET page → capture session cookie + ViewState
  2. POST Consultar (evento=237, area=<id>) → capture results page + new ViewState + XLS button ID
  3. POST XLS button → download .xlsx file
"""

import re
import time
from pathlib import Path
import urllib.request
import urllib.parse
import http.cookiejar

OUT_DIR = Path(__file__).parent.parent / "data" / "00_raw" / "qualis_areas"
OUT_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = ("https://sucupira-legado.capes.gov.br/sucupira/public/consultas"
            "/coleta/veiculoPublicacaoQualis/listaConsultaGeralPeriodicos.jsf")

EVENTO_2021_2024 = "237"

AREAS = {
    27: "ADMINISTRAÇÃO PÚBLICA E DE EMPRESAS, CIÊNCIAS CONTÁBEIS E TURISMO",
    35: "ANTROPOLOGIA / ARQUEOLOGIA",
    29: "ARQUITETURA, URBANISMO E DESIGN",
    11: "ARTES",
    3:  "ASTRONOMIA / FÍSICA",
    7:  "BIODIVERSIDADE",
    48: "BIOTECNOLOGIA",
    25: "CIÊNCIA DE ALIMENTOS",
    39: "CIÊNCIA POLÍTICA E RELAÇÕES INTERNACIONAIS",
    42: "CIÊNCIAS AGRÁRIAS I",
    49: "CIÊNCIAS AMBIENTAIS",
    6:  "CIÊNCIAS BIOLÓGICAS I",
    8:  "CIÊNCIAS BIOLÓGICAS II",
    9:  "CIÊNCIAS BIOLÓGICAS III",
    44: "CIÊNCIAS DA RELIGIÃO E TEOLOGIA",
    51: "CIÊNCIAS E HUMANIDADES PARA A EDUCAÇÃO BÁSICA",
    2:  "COMPUTAÇÃO",
    31: "COMUNICAÇÃO E INFORMAÇÃO E MUSEOLOGIA",
    26: "DIREITO",
    28: "ECONOMIA",
    38: "EDUCAÇÃO",
    21: "EDUCAÇÃO FÍSICA, FISIOTERAPIA, FONOAUDIOLOGIA E TERAPIA OCUPACIONAL",
    20: "ENFERMAGEM",
    10: "ENGENHARIAS I",
    12: "ENGENHARIAS II",
    13: "ENGENHARIAS III",
    14: "ENGENHARIAS IV",
    46: "ENSINO",
    19: "FARMÁCIA",
    33: "FILOSOFIA",
    5:  "GEOCIÊNCIAS",
    36: "GEOGRAFIA",
    40: "HISTÓRIA",
    45: "INTERDISCIPLINAR",
    41: "LINGUÍSTICA E LITERATURA",
    1:  "MATEMÁTICA / PROBABILIDADE E ESTATÍSTICA",
    47: "MATERIAIS",
    15: "MEDICINA I",
    16: "MEDICINA II",
    17: "MEDICINA III",
    24: "MEDICINA VETERINÁRIA",
    50: "NUTRIÇÃO",
    18: "ODONTOLOGIA",
    30: "PLANEJAMENTO URBANO E REGIONAL / DEMOGRAFIA",
    37: "PSICOLOGIA",
    4:  "QUÍMICA",
    22: "SAÚDE COLETIVA",
    32: "SERVIÇO SOCIAL",
    34: "SOCIOLOGIA",
    23: "ZOOTECNIA / RECURSOS PESQUEIROS",
}

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/120.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}


def extract_viewstate(html: str) -> str | None:
    m = re.search(r'javax\.faces\.ViewState[^>]+value="([^"]+)"', html)
    return m.group(1) if m else None


def extract_xls_button_id(html: str) -> str | None:
    """Find the XLS button component ID in the results table."""
    # The XLS button is near xls.gif with an onclick containing jsfcljs
    # Find from last occurrence (results table, not the legend)
    idx = html.rfind("xls.gif")
    if idx < 0:
        return None
    ctx = html[max(0, idx - 500):idx + 100]
    m = re.search(r"'(form:j_idt\d+)':'form:j_idt\d+'", ctx)
    return m.group(1) if m else None


def make_request(url: str, cookie_jar, data: dict | None = None) -> bytes:
    headers = dict(HEADERS)
    headers["Referer"] = BASE_URL
    if data:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        body = urllib.parse.urlencode(data).encode()
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    else:
        req = urllib.request.Request(url, headers=headers)

    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
    with opener.open(req, timeout=30) as resp:
        return resp.read()


def download_area(area_id: int, area_name: str) -> Path | None:
    slug = re.sub(r"[^a-z0-9]+", "_", area_name.lower()).strip("_")
    # Check if already downloaded
    existing = list(OUT_DIR.glob(f"*{slug}*.xlsx"))
    if existing:
        print(f"  [SKIP] {area_name} — already exists: {existing[0].name}")
        return existing[0]

    jar = http.cookiejar.CookieJar()

    # Step 1: GET fresh session + ViewState
    html1 = make_request(BASE_URL, jar).decode("utf-8", errors="replace")
    vs1 = extract_viewstate(html1)
    if not vs1:
        print(f"  [ERROR] {area_name} — could not get ViewState")
        return None

    # Step 2: POST Consultar
    data2 = {
        "form": "form",
        "form:evento": EVENTO_2021_2024,
        "form:checkArea": "on",
        "form:area": str(area_id),
        "form:checkIssn": "",
        "form:issn:issn": "",
        "form:checkTitulo": "",
        "form:j_idt62": "",
        "form:checkEstrato": "",
        "form:estrato": "0",
        "form:consultar": "Consultar",
        "javax.faces.ViewState": vs1,
    }
    html2 = make_request(BASE_URL, jar, data2).decode("utf-8", errors="replace")

    xls_id = extract_xls_button_id(html2)
    vs2 = extract_viewstate(html2)

    if not xls_id or not vs2:
        print(f"  [ERROR] {area_name} — XLS button or ViewState not found in results page")
        return None

    # Step 3: POST XLS button click
    data3 = {
        "form": "form",
        "form:evento": EVENTO_2021_2024,
        "form:checkArea": "on",
        "form:area": str(area_id),
        "form:checkIssn": "",
        "form:issn:issn": "",
        "form:checkTitulo": "",
        "form:j_idt62": "",
        "form:checkEstrato": "",
        "form:estrato": "0",
        xls_id: xls_id,
        "javax.faces.ViewState": vs2,
    }

    jar2 = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar2))
    headers = dict(HEADERS)
    headers["Content-Type"] = "application/x-www-form-urlencoded"
    headers["Referer"] = BASE_URL
    body = urllib.parse.urlencode(data3).encode()
    req = urllib.request.Request(BASE_URL, data=body, headers=headers, method="POST")

    # Reuse the same session cookie
    opener2 = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    with opener2.open(req, timeout=60) as resp:
        content_disp = resp.headers.get("Content-Disposition", "")
        content_type = resp.headers.get("Content-Type", "")

        if "spreadsheet" not in content_type and "xlsx" not in content_disp:
            print(f"  [ERROR] {area_name} — unexpected content type: {content_type}")
            return None

        # Extract filename from Content-Disposition
        m = re.search(r'filename="([^"]+)"', content_disp)
        filename = m.group(1) if m else f"qualis_{slug}.xlsx"
        out_path = OUT_DIR / filename

        data_bytes = resp.read()
        with open(out_path, "wb") as f:
            f.write(data_bytes)

        return out_path


def main():
    # Find already downloaded areas
    existing = {f.stem for f in OUT_DIR.glob("*.xlsx")}
    print(f"Output dir: {OUT_DIR}")
    print(f"Already downloaded: {len(existing)} files")
    print(f"Areas to download: {len(AREAS)}\n")

    success = 0
    failed = []

    for i, (area_id, area_name) in enumerate(AREAS.items(), 1):
        print(f"[{i:02d}/{len(AREAS)}] {area_name}...")
        try:
            path = download_area(area_id, area_name)
            if path:
                size = path.stat().st_size
                print(f"  OK — {path.name} ({size:,} bytes)")
                success += 1
            else:
                failed.append(area_name)
        except Exception as e:
            print(f"  [EXCEPTION] {e}")
            failed.append(area_name)

        # Polite delay between requests
        if i < len(AREAS):
            time.sleep(1.5)

    print(f"\nDone: {success}/{len(AREAS)} downloaded")
    if failed:
        print(f"Failed: {failed}")


if __name__ == "__main__":
    main()
