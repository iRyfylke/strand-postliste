from playwright.sync_api import sync_playwright
import json
import os
from datetime import datetime

CONFIG_FILE = "config.json"
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
        doktype = safe_text(art, ".bc-content-teaser-meta-property--dokumenttype dd")

        # Avsender/mottaker logikk
        mottaker = ""
        if "Inngående" in doktype:
            mottaker = safe_text(art, ".bc-content-teaser-meta-property--avsender dd")
        elif "Utgående" in doktype:
            mottaker = safe_text(art, ".bc-content-teaser-meta-property--mottaker dd")

        # Hent detaljlenke
        link_elem = art.evaluate_handle("node => node.closest('a')")
        detalj_link = link_elem.get_attribute("href") if link_elem else ""

        filer = []
        if detalj_link:
            detail_page = browser.new_page()
            try:
                detail_page.goto(detalj_link, timeout=15000)
                file_links = detail_page.query_selector_all("a")
                for fl in file_links:
                    href = fl.get_attribute("href")
                    tekst = fl.inner_text()
                    if href and "/api/presentation/v2/nye-innsyn/filer" in href:
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
            "dokumenttype": doktype,
            "avsender_mottaker": mottaker,
            "side": page_num,
            "detalj_link": detalj_link,
            "filer": filer,
            "status": "Publisert" if filer else "Må bes om innsyn"
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

    # lag HTML med paginering, status og ikoner
    html = f"""<!doctype html>
<html lang="no">
<head>
<meta charset="utf-8">
<title>Postliste</title>
<style>
body {{ font-family: sans-serif; margin: 2rem; }}
.card {{ border: 1px solid #ddd; padding: 1rem; margin-bottom: 1rem; }}
.status-publisert {{ color: green; font-weight: bold; }}
.status-innsyn {{ color: red; font-weight: bold; }}
.type-inngående {{ color: blue; font-weight: bold; }}
.type-utgående {{ color: darkorange; font-weight: bold; }}
.type-sakskart {{ color: purple; font-weight: bold; }}
.type-møtebok {{ color: teal; font-weight: bold; }}
.type-møteprotokoll {{ color: brown; font-weight: bold; }}
.type-saksfremlegg {{ color: darkgreen; font-weight: bold; }}
.type-internt {{ color: gray; font-weight: bold; }}
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

function cssClassForType(doktype) {{
  if (doktype.includes("Inngående")) return "type-inngående";
  if (doktype.includes("Utgående")) return "type-utgående";
  if (doktype.includes("Sakskart")) return "type-sakskart";
  if (doktype.includes("Møtebok")) return "type-møtebok";
  if (doktype.includes("Møteprotokoll")) return "type-møteprotokoll";
  if (doktype.includes("Saksfremlegg")) return "type-saksfremlegg";
  if (doktype.includes("Internt")) return "type-internt";
  return "";
}}

function iconForType(doktype) {{
  if (doktype.includes("Inngående")) return "📬";
  if (doktype.includes("Utgående")) return "📤";
  if (doktype.includes("Sakskart")) return "📑";
  if (doktype.includes("Møtebok")) return "📘";
  if (doktype.includes("Møteprotokoll")) return "📜";
  if (doktype.includes("Saksfremlegg")) return "📝";
  if (doktype.includes("Internt")) return "📂";
  return "📄";
}}

function renderPage(page) {{
  const start = (page-1)*perPage;
  const end = start+perPage;
  const items = data.slice(start,end);
  document.getElementById("container").innerHTML = items.map(d =>
    `<div class='card'>
      <h3>${{d.tittel}}</h3>
      <p>${{d.dato}} – ${{d.dokumentID}} – <span class='${{cssClassForType(d.dokumenttype)}}'>${{iconForType(d.dokumenttype)}} ${{d.dokumenttype}}</span></p>
      ${{d.avsender_mottaker ? `<p>Avsender/Mottaker: ${{d.avsender_mottaker}}</p>` : ""}}
      <p>Status: <span class='${{d.status==="Publisert"?"status-publisert":"status-innsyn"}}'>${{d.status}}</span></p>
      <p><a href='${{d.detalj_link}}' target='_blank'>Detaljer</a></p>
      ${{d.filer.length ? "<ul>" + d.filer.map(f => `<li><a href='${{f.url}}' target='_blank'>${{f.tekst}}</a></li>`).join("") + "</ul>" : "<p><a href='${{d.detalj_link}}' target='_blank'>Be om innsyn</a></p>"}}
    </div>`
