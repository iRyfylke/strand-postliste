from playwright.sync_api import sync_playwright
import json
import os
from datetime import datetime

CONFIG_FILE = "config.json"
OUTPUT_DIR = "."
BASE_URL = (
    "https://www.strand.kommune.no/tjenester/politikk-innsyn-og-medvirkning/"
    "postliste-dokumenter-og-vedtak/sok-i-post-dokumenter-og-saker/#/?page={page}&pageSize=100"
)

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"max_pages": 2, "per_page": 50}

def safe_text(element, selector: str) -> str:
    node = element.query_selector(selector)
    return node.inner_text().strip() if node else ""

def hent_side(page_num: int, browser):
    url = BASE_URL.format(page=page_num)
    print(f"[INFO] Åpner side {page_num}: {url}")
    page = browser.new_page()
    try:
        page.goto(url, timeout=15000)
        page.wait_for_selector("article.bc-content-teaser--item", timeout=5000)
    except Exception as e:
        print(f"[WARN] Ingen oppføringer på side {page_num} ({e})")
        page.close()
        return []

    articles = page.query_selector_all("article.bc-content-teaser--item")
    dokumenter = []
    for art in articles:
        tittel = safe_text(art, ".bc-content-teaser-title-text")
        dato = safe_text(art, ".bc-content-teaser-meta-property--dato dd")
        dokid = safe_text(art, ".bc-content-teaser-meta-property--dokumentID dd")
        mottaker = safe_text(art, ".bc-content-teaser-meta-property--mottaker dd")

        # Hent detaljlenke
        link_elem = art.evaluate_handle("node => node.closest('a')")
        detalj_link = link_elem.get_attribute("href") if link_elem else ""

        filer = []
        if detalj_link:
            detail_page = browser.new_page()
            try:
                detail_page.goto(detalj_link, timeout=15000)
                detail_page.wait_for_selector("a.bc-content-link", timeout=3000)
                file_links = detail_page.query_selector_all("a.bc-content-link")
                for fl in file_links:
                    href = fl.get_attribute("href")
                    tekst = fl.inner_text()
                    if href and href.startswith("/api/presentation/v2/nye-innsyn/filer"):
                        filer.append({
                            "tekst": tekst,
                            "url": "https://www.strand.kommune.no" + href
                        })
            except Exception as e:
                print(f"[WARN] Klarte ikke hente filer for '{tittel}': {e}")
            finally:
                detail_page.close()

        dokumenter.append({
            "tittel": tittel,
            "dato": dato,
            "dokumentID": dokid,
            "mottaker": mottaker,
            "side": page_num,
            "detalj_link": detalj_link,
            "filer": filer
        })
    page.close()
    print(f"[INFO] Side {page_num}: {len(dokumenter)} dokumenter funnet.")
    return dokumenter

def main():
    print("[INFO] Starter scraper…")
    config = load_config()
    max_pages = config.get("max_pages", 2)
    per_page = config.get("per_page", 50)

    alle_dokumenter = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        for page_num in range(1, max_pages + 1):
            docs = hent_side(page_num, browser)
            if not docs:
                print(f"[INFO] Stopper på side {page_num} – ingen flere dokumenter.")
                break
            alle_dokumenter.extend(docs)
            print(f"[INFO] Totalt hittil: {len(alle_dokumenter)} dokumenter.")
        browser.close()

    # lagre JSON
    with open("postliste.json", "w", encoding="utf-8") as f:
        json.dump(alle_dokumenter, f, ensure_ascii=False, indent=2)
    print(f"[INFO] Lagret JSON med {len(alle_dokumenter)} dokumenter")

    # lag HTML med paginering og fil-lenker
    html = f"""<!doctype html>
<html lang="no">
<head>
<meta charset="utf-8">
<title>Postliste</title>
<style>
body {{ font-family: sans-serif; margin: 2rem; }}
.card {{ border: 1px solid #ddd; padding: 1rem; margin-bottom: 1rem; }}
</style>
</head>
<body>
<h1>Postliste – Strand kommune</h1>
<p>Oppdatert: {datetime.now().strftime("%Y-%m-%d %H:%M")}</p>
<div id="container"></div>
<div id="pagination"></div>
<script>
const data = {json.dumps(alle_dokumenter, ensure_ascii=False)};
let perPage = {per_page};
let currentPage = 1;

function renderPage(page) {{
  const start = (page-1)*perPage;
  const end = start+perPage;
  const items = data.slice(start,end);
  document.getElementById("container").innerHTML = items.map(d =>
    `<div class='card'>
      <h3>${{d.tittel}}</h3>
      <p>${{d.dato}} – ${{d.dokumentID}} – ${{d.mottaker}} (side ${{d.side}})</p>
      <p><a href='${{d.detalj_link}}' target='_blank'>Detaljer</a> | 
         <a href='${{d.detalj_link}}' target='_blank'>Be om innsyn</a></p>
      ${{d.filer.length ? "<ul>" + d.filer.map(f => `<li><a href='${{f.url}}' target='_blank'>${{f.tekst}}</a></li>`).join("") + "</ul>" : ""}}
    </div>`
  ).join("");
  document.getElementById("pagination").innerHTML =
    `<button onclick='prevPage()' ${{page===1?"disabled":""}}>Forrige</button>
     Side ${{page}} av ${{Math.ceil(data.length/perPage)}}
     <button onclick='nextPage()' ${{end>=data.length?"disabled":""}}>Neste</button>`;
}}

function prevPage() {{ if(currentPage>1) {{ currentPage--; renderPage(currentPage); }} }}
function nextPage() {{ if(currentPage<Math.ceil(data.length/perPage)) {{ currentPage++; renderPage(currentPage); }} }}

renderPage(currentPage);
</script>
</body>
</html>"""
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[INFO] Lagret HTML med paginering og fil-lenker")

if __name__ == "__main__":
    main()
