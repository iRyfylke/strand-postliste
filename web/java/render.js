// === Imports ===
import { renderPagination } from './pagination.js';
import { buildStats } from './stats.js';

// === Global state (privat) ===
let currentSearch = "";
let currentFilter = "";
let currentStatus = "";
let dateFrom = null;
let dateTo = null;
let currentSort = "dato-desc";
let currentPage = 1;

// === Settere og gettere ===
export function setSearch(val) { currentSearch = val; }
export function setFilter(val) { currentFilter = val; }
export function setStatus(val) { currentStatus = val; }
export function setDateRange(from, to) { dateFrom = from; dateTo = to; }
export function setSort(val) { currentSort = val; }
export function setPage(val) { currentPage = val; }

export function getState() {
  return { currentSearch, currentFilter, currentStatus, dateFrom, dateTo, currentSort, currentPage };
}

// === Hjelpefunksjoner ===
function escapeHtml(s) {
  if (!s) return "";
  return s.replace(/[&<>"]/g, c => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;" }[c]
  ));
}

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

function parseDDMMYYYY(d) {
  if (!d) return null;
  const parts = d.split(".");
  if (parts.length !== 3) return null;
  const [DD, MM, YYYY] = parts.map(x => parseInt(x, 10));
  return new Date(YYYY, MM - 1, DD);
}

function getDateForSort(d) {
  const dt = parseDDMMYYYY(d.dato);
  return dt ? dt.getTime() : 0;
}

// === Filtrering og sortering ===
export function getFilteredData() {
  let arr = data.slice();

  if (currentSearch) {
    const q = currentSearch.toLowerCase();
    arr = arr.filter(d =>
      (d.tittel && d.tittel.toLowerCase().includes(q)) ||
      (d.dokumentID && String(d.dokumentID).toLowerCase().includes(q))
    );
  }

  if (currentFilter) {
    arr = arr.filter(d => d.dokumenttype && d.dokumenttype.includes(currentFilter));
  }

  if (currentStatus) {
    arr = arr.filter(d => d.status === currentStatus);
  }

  if (dateFrom || dateTo) {
    const from = dateFrom ? new Date(dateFrom) : null;
    const to = dateTo ? new Date(dateTo) : null;
    arr = arr.filter(d => {
      const pd = parseDDMMYYYY(d.dato);
      if (!pd) return false;
      if (from && pd < from) return false;
      if (to && pd > to) return false;
      return true;
    });
  }

  arr.sort((a,b) => {
    if (currentSort === "dato-desc") return getDateForSort(b) - getDateForSort(a);
    if (currentSort === "dato-asc") return getDateForSort(a) - getDateForSort(b);
    if (currentSort === "type-asc") return (a.dokumenttype||"").localeCompare(b.dokumenttype||"");
    if (currentSort === "type-desc") return (b.dokumenttype||"").localeCompare(a.dokumenttype||"");
    if (currentSort === "status-publisert") return (b.status === "Publisert") - (a.status === "Publisert");
    if (currentSort === "status-innsyn") return (a.status === "Publisert") - (b.status === "Publisert");
    return 0;
  });

  return arr;
}

// === Sammendrag ===
function renderSummary(totalFiltered) {
  const totalAll = data.length;
  const parts = [];
  if (currentSearch) parts.push(`søk: "${currentSearch}"`);
  if (currentFilter) parts.push(`type: ${currentFilter}`);
  if (currentStatus) parts.push(`status: ${currentStatus}`);
  if (dateFrom || dateTo) parts.push(`dato: ${dateFrom || "–"} til ${dateTo || "–"}`);
  const ctx = parts.length ? ` (${parts.join(", ")})` : "";

  const el = document.getElementById("summary");
  if (el) el.textContent = `Viser ${totalFiltered} av ${totalAll}${ctx}`;
}

// === Rendering av kort og paginering ===
export function renderPage(page) {
  const filtered = getFilteredData();
  const maxPage = Math.ceil(filtered.length / perPage) || 1;

  if (page < 1) page = 1;
  if (page > maxPage) page = maxPage;
  currentPage = page;

  const start = (page - 1) * perPage;
  const end = start + perPage;
  const items = filtered.slice(start, end);

  const cards = items.map(d => {
    const typeClass = cssClassForType(d.dokumenttype || "");
    const typeIcon = iconForType(d.dokumenttype || "");
    const statusClass = d.status === "Publisert" ? "status-publisert" : "status-innsyn";
    const link = d.journal_link || d.detalj_link || "";

    let filesHtml = "";
    if (d.status === "Publisert" && d.filer && d.filer.length) {
      filesHtml = "<ul class='files'>" + d.filer.map(f => `
        <li><a href='${f.url}' target='_blank'>${escapeHtml(f.tekst) || "Fil"}</a></li>
      `).join("") + "</ul>";
    } else if (link) {
      filesHtml = `<p><a href='${link}' target='_blank'>Be om innsyn</a></p>`;
    }

    const am = d.avsender_mottaker ? escapeHtml(d.avsender_mottaker) + " – " : "";
    const datoVis = escapeHtml(d.dato);

    return `
      <article class='card'>
        <h3>${escapeHtml(d.tittel)}</h3>
        <p class='meta'>
          ${datoVis} – ${escapeHtml(String(d.dokumentID || ""))} – ${am}
          <span class='${typeClass}'>${typeIcon} ${escapeHtml(d.dokumenttype || "")}</span>
        </p>
        <p>Status: <span class='${statusClass}'>${d.status}</span></p>
        ${filesHtml}
        ${link ? `<p class='footer-link'><a href='${link}' target='_blank' aria-label='Åpne journalposten'>Se journalposten</a></p>` : ""}
      </article>`;
  }).join("");

  const container = document.getElementById("container");
  if (container) container.innerHTML = cards;

  renderPagination("pagination-top", currentPage, filtered.length, perPage);
  renderPagination("pagination-bottom", currentPage, filtered.length, perPage);

  renderSummary(filtered.length);
  buildStats(filtered);
}
