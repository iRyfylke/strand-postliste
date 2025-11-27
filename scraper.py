from playwright.sync_api import sync_playwright
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

CONFIG_FILE = "config.json"
DATA_FILE = "postliste.json"

BASE_URL = (
    "https://www.strand.kommune.no/tjenester/politikk-innsyn-og-medvirkning/"
    "postliste-dokumenter-og-vedtak/sok-i-post-dokumenter-og-saker/#/?page={page}&pageSize=100"
)

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "mode": "incremental",
        "max_pages_incremental": 5,
        "max_pages_update": 200,
        "per_page": 50
    }

def load_existing():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                # Sikre at vi har liste -> dict keyed by dokumentID
                return {d["dokumentID"]: d for d in data if "dokumentID" in d}
            except Exception:
                return {}
    return {}

def safe_text(element, selector: str) -> str:
    try:
        node = element.query_selector(selector)
        return node.inner_text().strip() if node else ""
    except Exception:
        return ""

# Ny hjelpefunksjon for å formatere datoer til DD.MM.YYYY
def format_dato(dato_str: str) -> str:
    from datetime import datetime
    try:
        dt = datetime.strptime(dato_str, "%Y-%m-%d")
        return dt.strftime("%d.%m.%Y")
    except Exception:
        return dato_str

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
        dato_raw = safe_text(art, ".bc-content-teaser-meta-property--dato dd")
        dato = format_dato(dato_raw)
        dokid = safe_text(art, ".bc-content-teaser-meta-property--dokumentID dd")
        doktype = safe_text(art, ".SakListItem_sakListItemTypeText__16759c")

        # Avsender/mottaker med label
        avsender = safe_text(art, ".bc-content-teaser-meta-property--avsender dd")
        mottaker = safe_text(art, ".bc-content-teaser-meta-property--mottaker dd")
        if avsender:
            am = f"Avsender: {avsender}"
        elif mottaker:
            am = f"Mottaker: {mottaker}"
        else:
            am = ""

        if not dokid:
            continue

        detalj_link = ""
        try:
            link_elem = art.evaluate_handle("node => node.closest('a')")
            detalj_link = link_elem.get_attribute("href") if link_elem else ""
        except Exception:
            detalj_link = ""

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
                        abs_url = href if href.startswith("http") else "https://www.strand.kommune.no" + href
                        filer.append({"tekst": tekst, "url": abs_url})
            except Exception as e:
                print(f"[WARN] Klarte ikke hente filer for '{tittel}': {e}")
            finally:
                detail_page.close()

        dokumenter.append({
            "tittel": tittel,
            "dato": dato,
            "dokumentID": dokid,
            "dokumenttype": doktype,
            "avsender_mottaker": am,
            "side": page_num,
            "detalj_link": detalj_link,
            "filer": filer,
            "status": "Publisert" if filer else "Må bes om innsyn"
        })
    page.close()
    return dokumenter

def main():
    print("[INFO] Starter scraper…")
    config = load_config()
    mode = config.get("mode", "incremental")
    max_pages = config["max_pages_incremental"] if mode == "incremental" else config["max_pages_update"]
    per_page = config.get("per_page", 50)

    existing = load_existing()
    updated = dict(existing)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        for page_num in range(1, max_pages + 1):
            docs = hent_side(page_num, browser)
            if not docs:
                continue

            # Oppdater/legg til
            for d in docs:
                doc_id = d["dokumentID"]
                if doc_id not in updated:
                    print(f"[NEW] {doc_id} – {d['tittel']}")
                    updated[doc_id] = d
                else:
                    old = updated[doc_id]
                    changed = (
                        old.get("status") != d.get("status") or
                        len(old.get("filer", [])) != len(d.get("filer", [])) or
                        old.get("tittel") != d.get("tittel") or
                        old.get("dokumenttype") != d.get("dokumenttype") or
                        old.get("avsender_mottaker") != d.get("avsender_mottaker")
                    )
                    if changed:
                        print(f"[UPDATE] {doc_id} – {d['tittel']}")
                        updated[doc_id] = d

            # I incremental-modus: stopp når vi treffer kjent ID (resten antas å være gamle)
            if mode == "incremental":
                if any(d["dokumentID"] in existing for d in docs):
                    print("[INFO] Incremental: Stoppet – fant eksisterende oppføring på denne siden.")
                    break
        browser.close()

    # Lagre JSON (liste av verdier sortert etter dato, hvis mulig)
    data_list = list(updated.values())
    try:
        data_list.sort(key=lambda x: x.get("dato", ""), reverse=True)
    except Exception:
        pass

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data_list, f, ensure_ascii=False, indent=2)
    print(f"[INFO] Lagret JSON med {len(data_list)} dokumenter")

    # Generer komplett HTML med ikoner, fargekoder, filtrering, paginering (topp/bunn) og norsk tid/datoformat
    html = f"""<!doctype html>
<html lang="no">
<head>
<meta charset="utf-8">
<title>Postliste</title>
<style>
body { font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 2rem; }
.controls { display: flex; gap: 1rem; align-items: center; margin: 1rem 0; flex-wrap: wrap; }
.controls label { font-weight: 600; color: #333; }
select { padding: .25rem .5rem; }
.card { border: 1px solid #ddd; border-radius: 8px; padding: 1rem; margin-bottom: 1rem; }
.card h3 { margin: 0 0 .5rem 0; font-size: 1.1rem; }
.meta { color: #555; margin-bottom: .5rem; }
.status-publisert { color: #1a7f37; font-weight: 600; }
.status-innsyn { color: #b42318; font-weight: 600; }
.type-inngående { color: #1f6feb; font-weight: 600; }
.type-utgående { color: #b78103; font-weight: 600; }
.type-sakskart { color: #7d3fc2; font-weight: 600; }
.type-møtebok { color: #0ea5a5; font-weight: 600; }
.type-møteprotokoll { color: #8b5e34; font-weight: 600; }
.type-saksfremlegg { color: #14532d; font-weight: 600; }
.type-internt { color: #667085; font-weight: 600; }
ul.files { margin: .5rem 0 0 0; padding-left: 1rem; }
ul.files li { margin: .25rem 0; }
.pagination { margin: 1rem 0; display: flex; gap: .75rem; align-items: center; }
.pagination button { padding: .25rem .6rem; }
.summary { color: #444; font-size: .95rem; }
</style>
</head>
<body>
<h1>Postliste – Strand kommune</h1>
<p>Oppdatert: {datetime.now(ZoneInfo("Europe/Oslo")).strftime("%d.%m.%Y %H:%M")}</p>

<div class="controls">
  <div>
    <label for="filterType">Filtrer på dokumenttype:</label>
    <select id="filterType" onchange="applyFilter()">
      <option value="">Alle</option>
      <option value="Inngående">Inngående</option>
      <option value="Utgående">Utgående</option>
      <option value="Sakskart">Sakskart</option>
      <option value="Møtebok">Møtebok</option>
      <option value="Møteprotokoll">Møteprotokoll</option>
      <option value="Saksfremlegg">Saksfremlegg</option>
      <option value="Internt">Internt</option>
    </select>
  </div>
  <div>
    <label for="perPage">Oppføringer per side:</label>
    <select id="perPage" onchange="changePerPage()">
      <option value="5">5</option>
      <option value="10" selected>10</option>
      <option value="20">20</option>
      <option value="50">50</option>
    </select>
  </div>
  <div class="summary" id="summary"></div>
</div>

<div id="pagination-top" class="pagination"></div>
<div id="container"></div>
<div id="pagination-bottom" class="pagination"></div>

<script>
const data = {json.dumps(data_list, ensure_ascii=False)};
let perPage = {per_page};
let currentPage = 1;
let currentFilter = "";

function cssClassForType(doktype) {
  if (!doktype) return "";
  if (doktype.includes("Inngående")) return "type-inngående";
  if (doktype.includes("Utgående")) return "type-utgående";
  if (doktype.includes("Sakskart")) return "type-sakskart";
  if (doktype.includes("Møtebok")) return "type-møtebok";
  if (doktype.includes("Møteprotokoll")) return "type-møteprotokoll";
  if (doktype.includes("Saksfremlegg")) return "type-saksfremlegg";
  if (doktype.includes("Internt")) return "type-internt";
  return "";
}

function iconForType(doktype) {
  if (!doktype) return "📄";
  if (doktype.includes("Inngående")) return "📬";
  if (doktype.includes("Utgående")) return "📤";
  if (doktype.includes("Sakskart")) return "📑";
  if (doktype.includes("Møtebok")) return "📘";
  if (doktype.includes("Møteprotokoll")) return "📜";
  if (doktype.includes("Saksfremlegg")) return "📝";
  if (doktype.includes("Internt")) return "📂";
  return "📄";
}

function escapeHtml(s) {
  if (!s) return "";
  return s.replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;"})[c]);
}

function getFilteredData() {
  if (!currentFilter) return data;
  return data.filter(d => d.dokumenttype && d.dokumenttype.includes(currentFilter));
}

function renderSummary(totalFiltered) {
  const totalAll = data.length;
  const txt = currentFilter
    ? `Viser ${totalFiltered} av ${totalAll} (filter: ${currentFilter})`
    : `Viser ${totalFiltered} av ${totalAll}`;
  document.getElementById("summary").textContent = txt;
}

function renderPage(page) {
  const filtered = getFilteredData();
  const start = (page-1) * perPage;
  const end = start + perPage;
  const items = filtered.slice(start, end);

  const html = items.map(d => {
    const typeClass = cssClassForType(d.dokumenttype || "");
    const typeIcon = iconForType(d.dokumenttype || "");
    const statusClass = d.status === "Publisert" ? "status-publisert" : "status-innsyn";

    const filesHtml = (d.filer && d.filer.length)
      ? "<ul class='files'>" + d.filer.map(f => `<li><a href='${f.url}' target='_blank'>${escapeHtml(f.tekst) || "Fil"}</a></li>`).join("") + "</ul>"
      : (d.detalj_link ? `<p><a href='${d.detalj_link}' target='_blank'>Be om innsyn</a></p>` : "");

    const am = d.avsender_mottaker ? escapeHtml(d.avsender_mottaker) + " – " : "";

    return `
      <div class='card'>
        <h3>${escapeHtml(d.tittel)}</h3>
        <p class='meta'>
          ${escapeHtml(d.dato)} – ${escapeHtml(d.dokumentID)} – ${am}
          <span class='${typeClass}'>${typeIcon} ${escapeHtml(d.dokumenttype || "")}</span>
        </p>
        <p>Status: <span class='${statusClass}'>${d.status}</span></p>
        ${filesHtml}
        ${d.detalj_link ? `<p><a href='${d.detalj_link}' target='_blank'>Se journalposten</a></p>` : ""}
      </div>`;
  }).join("");

  document.getElementById("container").innerHTML = html;
  renderPagination("pagination-top", page, filtered.length);
  renderPagination("pagination-bottom", page, filtered.length);
  renderSummary(filtered.length);
}

function renderPagination(elementId, page, totalItems) {
  const maxPage = Math.ceil(totalItems / perPage) || 1;
  document.getElementById(elementId).innerHTML =
    `<button onclick='prevPage()' ${page===1?"disabled":""}>Forrige</button>
     Side ${page} av ${maxPage}
     <button onclick='nextPage()' ${page>=maxPage?"disabled":""}>Neste</button>`;
}

function prevPage() {
  if (currentPage > 1) {
    currentPage--;
    renderPage(currentPage);
  }
}

function nextPage() {
  const maxPage = Math.ceil(getFilteredData().length / perPage) || 1;
  if (currentPage < maxPage) {
    currentPage++;
    renderPage(currentPage);
  }
}

function applyFilter() {
  currentFilter = document.getElementById("filterType").value;
  currentPage = 1;
  renderPage(currentPage);
}

function changePerPage() {
  perPage = parseInt(document.getElementById("perPage").value, 10);
  currentPage = 1;
  renderPage(currentPage);
}

renderPage(currentPage);
</script>
</body>
</html>"""
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("[INFO] Lagret HTML til index.html")

if __name__ == "__main__":
    main()
