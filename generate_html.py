import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

DATA_FILE = "postliste.json"
CONFIG_FILE = "config.json"
OUTPUT_FILE = "index.html"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                pass
    return {"per_page": 50}

def load_data():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return []

def generate_html():
    data = load_data()
    config = load_config()
    per_page = int(config.get("per_page", 50))
    updated = datetime.now(ZoneInfo("Europe/Oslo")).strftime("%d.%m.%Y %H:%M")

    html = f"""<!doctype html>
<html lang="no">
<head>
<meta charset="utf-8">
<title>Postliste – Strand kommune</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root {{
  --border: #ddd;
  --text: #333;
  --muted: #555;
  --bg: #fff;
  --link: #1f6feb;
  --green: #1a7f37;
  --red: #b42318;
}}
* {{ box-sizing: border-box; }}
body {{
  font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
  margin: 1rem;
  color: var(--text);
  background: var(--bg);
  transition: background 0.3s, color 0.3s;
}}
header.sticky-header {{
  position: sticky;
  top: 0;
  background: var(--bg);
  z-index: 1000;
  padding: 1rem 0;
  border-bottom: 2px solid var(--border);
}}
header h1 {{ margin: 0 0 .25rem 0; font-size: 1.4rem; }}
header .updated {{ color: var(--muted); margin-bottom: 0.5rem; font-size: 0.9rem; }}

.controls {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: .75rem;
  align-items: end;
  margin: 1rem 0;
}}
.controls .field {{ display: flex; flex-direction: column; gap: .25rem; }}
.controls label {{ font-weight: 600; color: var(--text); font-size: 0.85rem; }}
.controls input[type="text"], .controls select, .controls button {{
  padding: .5rem .6rem;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: #fff;
  font-size: 0.95rem;
}}
.controls .actions {{ display: flex; gap: .5rem; align-items: center; flex-wrap: wrap; }}

.container {{
  display: grid;
  grid-template-columns: 1fr;
  gap: 1rem;
}}
@media (min-width: 700px) {{
  .container {{ grid-template-columns: 1fr 1fr; }}
}}
@media (min-width: 1100px) {{
  .container {{ grid-template-columns: 1fr 1fr 1fr; }}
}}

.card {{
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 0.9rem;
  display: flex;
  flex-direction: column;
  gap: .5rem;
  background: var(--bg);
  transition: background 0.3s, color 0.3s, border-color 0.3s;
}}
.card h3 {{
  margin: 0;
  font-size: 1rem;
  line-height: 1.3;
}}
.meta {{
  color: var(--muted);
  font-size: 0.9rem;
}}
.status-publisert {{ color: var(--green); font-weight: 600; }}
.status-innsyn {{ color: var(--red); font-weight: 600; }}

ul.files {{
  margin: .25rem 0 0 0;
  padding-left: 1rem;
  font-size: 0.9rem;
}}
ul.files li {{ margin: .25rem 0; }}
.card .footer-link a {{
  color: var(--link);
  text-decoration: none;
  font-size: 0.9rem;
}}
.card .footer-link a:hover {{ text-decoration: underline; }}

.pagination {{
  margin: 1rem 0;
  display: flex;
  gap: .75rem;
  align-items: center;
  flex-wrap: wrap;
  font-size: 0.95rem;
}}
.pagination button {{
  padding: .45rem .8rem;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: #fff;
}}
.summary {{ color: var(--muted); font-size: .95rem; }}

/* Type farger (klasser brukes for tydelig markering) */
.type-inngående {{ color: #1f6feb; font-weight: 600; }}
.type-utgående {{ color: #b78103; font-weight: 600; }}
.type-sakskart {{ color: #7d3fc2; font-weight: 600; }}
.type-møtebok {{ color: #0ea5a5; font-weight: 600; }}
.type-møteprotokoll {{ color: #8b5e34; font-weight: 600; }}
.type-saksfremlegg {{ color: #14532d; font-weight: 600; }}
.type-internt {{ color: #667085; font-weight: 600; }}

/* Dark mode */
body.dark {{
  --bg: #0f1115;
  --text: #e6edf3;
  --muted: #9aa7b5;
  --border: #263041;
  --link: #58a6ff;
  --green: #3fb950;
  --red: #ff6b6b;
}}
.toggle-dark {{
  position: fixed;
  bottom: 1rem;
  right: 1rem;
  background: var(--link);
  color: #fff;
  border: none;
  padding: .6rem .9rem;
  border-radius: 10px;
  cursor: pointer;
  font-size: 0.95rem;
}}
.toggle-dark:focus {{ outline: 2px solid var(--border); }}
</style>
</head>
<body>
<header class="sticky-header">
  <h1>Postliste – Strand kommune</h1>
  <p class="updated">Oppdatert: {updated}</p>

  <section class="controls" aria-label="Kontroller for filtrering, søk og sortering">
    <div class="field">
      <label for="searchInput">Søk:</label>
      <input id="searchInput" type="text" placeholder="Skriv for å søke …" oninput="applySearch()" />
    </div>
    <div class="field">
      <label for="filterType">Dokumenttype:</label>
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
    <div class="field">
      <label for="statusFilter">Status:</label>
      <select id="statusFilter" onchange="applyStatusFilter()">
        <option value="">Alle</option>
        <option value="Publisert">Publisert</option>
        <option value="Må bes om innsyn">Må bes om innsyn</option>
      </select>
    </div>
    <div class="field">
      <label for="sortSelect">Sorter:</label>
      <select id="sortSelect" onchange="applySort()">
        <option value="dato-desc">Dato (nyeste først)</option>
        <option value="dato-asc">Dato (eldste først)</option>
        <option value="type-asc">Dokumenttype (A–Å)</option>
        <option value="type-desc">Dokumenttype (Å–A)</option>
        <option value="status-publisert">Status (Publisert først)</option>
        <option value="status-innsyn">Status (Må bes om innsyn først)</option>
      </select>
    </div>
    <div class="field">
      <label for="perPage">Per side:</label>
      <select id="perPage" onchange="changePerPage()">
        <option value="5">5</option>
        <option value="10">10</option>
        <option value="20">20</option>
        <option value="50" selected>50</option>
      </select>
    </div>
    <div class="actions">
      <button onclick="exportCSV()">Eksporter CSV</button>
      <span class="summary" id="summary"></span>
    </div>
  </section>
</header>

<nav id="pagination-top" class="pagination" aria-label="Paginering topp"></nav>
<main id="container" class="container"></main>
<nav id="pagination-bottom" class="pagination" aria-label="Paginering bunn"></nav>

<button class="toggle-dark" onclick="toggleDarkMode()" aria-label="Veksle mørk modus">🌙 Mørk modus</button>

<script>
const data = {json.dumps(data, ensure_ascii=False)};
let perPage = {per_page};
let currentPage = 1;
let currentFilter = "";
let currentSearch = "";
let currentStatus = "";
let currentSort = "dato-desc";

// Persist mørk modus med localStorage
(function initTheme() {{
  const saved = localStorage.getItem("dark-mode");
  if (saved === "on") document.body.classList.add("dark");
}})();

function toggleDarkMode() {{
  document.body.classList.toggle("dark");
  localStorage.setItem("dark-mode", document.body.classList.contains("dark") ? "on" : "off");
}}

function escapeHtml(s) {{
  if (!s) return "";
  return s.replace(/[&<>"]/g, c => ({{"&":"&amp;","<":"&lt;","\\": "&quot;"}})[c]);
}}

function cssClassForType(doktype) {{
  if (!doktype) return "";
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
  if (!doktype) return "📄";
  if (doktype.includes("Inngående")) return "📬";
  if (doktype.includes("Utgående")) return "📤";
  if (doktype.includes("Sakskart")) return "📑";
  if (doktype.includes("Møtebok")) return "📘";
  if (doktype.includes("Møteprotokoll")) return "📜";
  if (doktype.includes("Saksfremlegg")) return "📝";
  if (doktype.includes("Internt")) return "📂";
  return "📄";
}}

// Dato for sortering: preferer parsed_date (ISO), fallback til DD.MM.YYYY
function getDateForSort(d) {{
  const iso = d.parsed_date || "";
  if (iso) {{
    const t = Date.parse(iso);
    if (!isNaN(t)) return t;
  }}
  const dd = d.dato || "";
  if (!dd) return 0;
  const parts = dd.split(".");
  if (parts.length === 3) {{
    const [DD, MM, YYYY] = parts;
    const t = Date.parse(`${{YYYY}}-${{MM}}-${{DD}}`);
    return isNaN(t) ? 0 : t;
  }}
  return 0;
}}

function getFilteredData() {{
  let arr = data.slice();

  // Søk
  if (currentSearch) {{
    const q = currentSearch.toLowerCase();
    arr = arr.filter(d =>
      (d.tittel && d.tittel.toLowerCase().includes(q)) ||
      (d.dokumentID && String(d.dokumentID).toLowerCase().includes(q)) ||
      (d.avsender_mottaker && d.avsender_mottaker.toLowerCase().includes(q))
    );
  }}

  // Type
  if (currentFilter) {{
    arr = arr.filter(d => d.dokumenttype && d.dokumenttype.includes(currentFilter));
  }}

  // Status
  if (currentStatus) {{
    arr = arr.filter(d => d.status === currentStatus);
  }}

  // Sortering
  arr.sort((a,b) => {{
    if (currentSort === "dato-desc") return getDateForSort(b) - getDateForSort(a);
    if (currentSort === "dato-asc") return getDateForSort(a) - getDateForSort(b);
    if (currentSort === "type-asc") return (a.dokumenttype||"").localeCompare(b.dokumenttype||"");
    if (currentSort === "type-desc") return (b.dokumenttype||"").localeCompare(a.dokumenttype||"");
    if (currentSort === "status-publisert") return (b.status === "Publisert") - (a.status === "Publisert");
    if (currentSort === "status-innsyn") return (a.status === "Publisert") - (b.status === "Publisert");
    return 0;
  }});

  return arr;
}}

function renderSummary(totalFiltered) {{
  const totalAll = data.length;
  const parts = [];
  if (currentSearch) parts.push(`søk: "${{currentSearch}}"`);
  if (currentFilter) parts.push(`type: ${{currentFilter}}`);
  if (currentStatus) parts.push(`status: ${{currentStatus}}`);
  const ctx = parts.length ? ` (${{parts.join(", ")}})` : "";
  document.getElementById("summary").textContent =
    `Viser ${{totalFiltered}} av ${{totalAll}}${{ctx}}`;
}}

function renderPage(page) {{
  const filtered = getFilteredData();
  const start = (page-1) * perPage;
  const end = start + perPage;
  const items = filtered.slice(start, end);

  const cards = items.map(d => {{
    const typeClass = cssClassForType(d.dokumenttype || "");
    const typeIcon = iconForType(d.dokumenttype || "");
    const statusClass = d.status === "Publisert" ? "status-publisert" : "status-innsyn";
    const link = d.journal_link || d.detalj_link || "";

    // Betinget visning av dokumenter/innsyn
    let filesHtml = "";
    if (d.status === "Publisert" && d.filer && d.filer.length) {{
      filesHtml = "<ul class='files'>" + d.filer.map(f => `
        <li><a href='${{f.url}}' target='_blank'>${{escapeHtml(f.tekst) || "Fil"}}</a></li>
      `).join("") + "</ul>";
    }} else if (link) {{
      filesHtml = `<p><a href='${{link}}' target='_blank'>Be om innsyn</a></p>`;
    }}

    const am = d.avsender_mottaker ? escapeHtml(d.avsender_mottaker) + " – " : "";
    const datoVis = escapeHtml(d.dato || (d.parsed_date ? new Date(d.parsed_date).toLocaleDateString("no-NO") : ""));

    return `
      <article class='card'>
        <h3>${{escapeHtml(d.tittel)}}</h3>
        <p class='meta'>
          ${{datoVis}} – ${{escapeHtml(String(d.dokumentID||""))}} – ${{am}}
          <span class='${{typeClass}}'>${{typeIcon}} ${{escapeHtml(d.dokumenttype || "")}}</span>
        </p>
        <p>Status: <span class='${{statusClass}}'>${{d.status}}</span></p>
        ${{filesHtml}}
        ${{link ? `<p class='footer-link'><a href='${{link}}' target='_blank' aria-label='Åpne journalposten'>Se journalposten</a></p>` : ""}}
      </article>`;
  }}).join("");

  document.getElementById("container").innerHTML = cards;
  renderPagination("pagination-top", page, filtered.length);
  renderPagination("pagination-bottom", page, filtered.length);
  renderSummary(filtered.length);
}}

function renderPagination(elementId, page, totalItems) {{
  const maxPage = Math.ceil(totalItems / perPage) || 1;
  document.getElementById(elementId).innerHTML =
    `<button onclick='prevPage()' ${{page===1?"disabled":""}}>Forrige</button>
     <span>Side ${{page}} av ${{maxPage}}</span>
     <button onclick='nextPage()' ${{page>=maxPage?"disabled":""}}>Neste</button>`;
}}

function prevPage() {{
  if (currentPage > 1) {{
    currentPage--;
    renderPage(currentPage);
  }}
}}

function nextPage() {{
  const maxPage = Math.ceil(getFilteredData().length / perPage) || 1;
  if (currentPage < maxPage) {{
    currentPage++;
    renderPage(currentPage);
  }}
}}

function applyFilter() {{
  currentFilter = document.getElementById("filterType").value;
  currentPage = 1;
  renderPage(currentPage);
}}

function applyStatusFilter() {{
  currentStatus = document.getElementById("statusFilter").value;
  currentPage = 1;
  renderPage(currentPage);
}}

function applySearch() {{
  currentSearch = document.getElementById("searchInput").value.trim();
  currentPage = 1;
  renderPage(currentPage);
}}

function applySort() {{
  currentSort = document.getElementById("sortSelect").value;
  currentPage = 1;
  renderPage(currentPage);
}}

function changePerPage() {{
  perPage = parseInt(document.getElementById("perPage").value, 10);
  currentPage = 1;
  renderPage(currentPage);
}}

function exportCSV() {{
  const filtered = getFilteredData();
  const rows = [["Dato","DokumentID","Tittel","Dokumenttype","Avsender/Mottaker","Status","Journalpostlenke"]];
  filtered.forEach(d => {{
    const link = d.journal_link || d.detalj_link || "";
    rows.push([
      d.dato || (d.parsed_date || ""),
      String(d.dokumentID || ""),
      (d.tittel || "").replace(/\\s+/g, " ").trim(),
      d.dokumenttype || "",
      d.avsender_mottaker || "",
      d.status || "",
      link
    ]);
  }});
  const csv = rows.map(r => r.map(v => `"${{String(v).replace(/"/g, '""')}}"`).join(",")).join("\\n");
  const blob = new Blob([csv], {{type: "text/csv;charset=utf-8;"}});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "postliste.csv";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}}

document.addEventListener("DOMContentLoaded", () => {{
  const perPageSelect = document.getElementById("perPage");
  if (perPageSelect) {{
    const opt = Array.from(perPageSelect.options).find(o => parseInt(o.value,10) === perPage);
    if (opt) perPageSelect.value = String(perPage);
  }}
  renderPage(currentPage);
}});
</script>
</body>
</html>"""

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[INFO] Lagret HTML til {OUTPUT_FILE}")

if __name__ == "__main__":
    generate_html()
