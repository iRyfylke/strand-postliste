// Variabler settes inn fra generate_html.py via template.html
// const data = {data_json};
// let perPage = {per_page};

let currentPage = 1;
let currentFilter = "";
let currentSearch = "";
let currentSearchAM = "";
let currentStatus = "";
let currentSort = "dato-desc";
let dateFrom = "";
let dateTo = "";

function escapeHtml(s) {
  if (!s) return "";
  return s.replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;"}[c]));
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

function applySearch() {
  currentSearch = document.getElementById("searchInput").value.trim();
  currentSearchAM = document.getElementById("searchAM").value.trim();
  currentPage = 1;
  renderPage(currentPage);
}

function applyDateFilter() {
  dateFrom = document.getElementById("dateFrom").value;
  dateTo = document.getElementById("dateTo").value;
  currentPage = 1;
  renderPage(currentPage);
}

function setQuickRange(range) {
  const now = new Date();
  if (range === "week") {
    const lastWeek = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 7);
    document.getElementById("dateFrom").value = lastWeek.toISOString().split("T")[0];
    document.getElementById("dateTo").value = now.toISOString().split("T")[0];
  }
  if (range === "month") {
    const lastMonth = new Date(now.getFullYear(), now.getMonth() - 1, now.getDate());
    document.getElementById("dateFrom").value = lastMonth.toISOString().split("T")[0];
    document.getElementById("dateTo").value = now.toISOString().split("T")[0];
  }
  applyDateFilter();
}

function applyFilter() {
  currentFilter = document.getElementById("filterType").value;
  currentPage = 1;
  renderPage(currentPage);
}

function applyStatusFilter() {
  currentStatus = document.getElementById("statusFilter").value;
  currentPage = 1;
  renderPage(currentPage);
}

function applySort() {
  currentSort = document.getElementById("sortSelect").value;
  currentPage = 1;
  renderPage(currentPage);
}

function changePerPage() {
  perPage = parseInt(document.getElementById("perPage").value, 10);
  currentPage = 1;
  renderPage(currentPage);
}

function getFilteredData() {
  let arr = data.slice();

  if (currentSearch) {
    const q = currentSearch.toLowerCase();
    arr = arr.filter(d =>
      (d.tittel && d.tittel.toLowerCase().includes(q)) ||
      (d.dokumentID && String(d.dokumentID).toLowerCase().includes(q))
    );
  }

  if (currentSearchAM) {
    const q = currentSearchAM.toLowerCase();
    arr = arr.filter(d => (d.avsender_mottaker && d.avsender_mottaker.toLowerCase().includes(q)));
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

function renderSummary(totalFiltered) {
  const totalAll = data.length;

  // Sammendragstekst med aktive filtre
  const parts = [];
  if (currentSearch) parts.push(`søk: "${currentSearch}"`);
  if (currentSearchAM) parts.push(`avsender/mottaker: "${currentSearchAM}"`);
  if (currentFilter) parts.push(`type: ${currentFilter}`);
  if (currentStatus) parts.push(`status: ${currentStatus}`);
  if (dateFrom || dateTo) parts.push(`dato: ${dateFrom || "–"} til ${dateTo || "–"}`);
  const ctx = parts.length ? ` (${parts.join(", ")})` : "";

  document.getElementById("summary").textContent =
    `Viser ${totalFiltered} av ${totalAll}${ctx}`;
}

function renderPage(page) {
  const filtered = getFilteredData();
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

  document.getElementById("container").innerHTML = cards;
  renderPagination("pagination-top", page, filtered.length);
  renderPagination("pagination-bottom", page, filtered.length);
  renderSummary(filtered.length);
  buildStats(filtered);
}

function renderPagination(elementId, page, totalItems) {
  const maxPage = Math.ceil(totalItems / perPage) || 1;
  document.getElementById(elementId).innerHTML =
    `<button onclick='prevPage()' ${page === 1 ? "disabled" : ""}>Forrige</button>
     <span>Side ${page} av ${maxPage}</span>
     <button onclick='nextPage()' ${page >= maxPage ? "disabled" : ""}>Neste</button>`;
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

function exportCSV() {
  const filtered = getFilteredData();
  const rows = [["Dato","DokumentID","Tittel","Dokumenttype","Avsender/Mottaker","Status","Journalpostlenke"]];
  filtered.forEach(d => {
    const link = d.journal_link || d.detalj_link || "";
    rows.push([
      d.dato || "",
      String(d.dokumentID || ""),
      (d.tittel || "").replace(/\s+/g, " ").trim(),
      d.dokumenttype || "",
      d.avsender_mottaker || "",
      d.status || "",
      link
    ]);
  });
  const csv = rows.map(r => r.map(v => `"${String(v).replace(/"/g, '""')}"`).join(",")).join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "postliste.csv";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function exportPDF() {
  window.print();
}

function copyShareLink() {
  const params = new URLSearchParams();
  if (currentSearch) params.set("q", currentSearch);
  if (currentSearchAM) params.set("am", currentSearchAM);
  if (currentFilter) params.set("type", currentFilter);
  if (currentStatus) params.set("status", currentStatus);
  if (dateFrom) params.set("from", dateFrom);
  if (dateTo) params.set("to", dateTo);
  params.set("sort", currentSort);
  params.set("perPage", String(perPage));
  params.set("page", String(currentPage));

  const shareUrl = window.location.origin + window.location.pathname + "?" + params.toString();
  navigator.clipboard.writeText(shareUrl).then(() => {
    const el = document.getElementById("summary");
    const prev = el.textContent;
    el.textContent = "Delingslenke kopiert!";
    setTimeout(() => el.textContent = prev, 1500);
  });
}

// Chart.js
let weeklyChart = null;
let typesChart = null;

function buildStats(filtered) {
  // Publisert per uke (ISO-aktig uke-nummer, forenklet)
  const weekly = {};
  filtered.forEach(d => {
    if (d.status === "Publisert" && d.dato) {
      const dt = parseDDMMYYYY(d.dato);
      if (!dt) return;
      // Forenklet uke-beregning (kalenderuke ~)
      const startOfYear = new Date(dt.getFullYear(), 0, 1);
      const dayDiff = Math.floor((dt - startOfYear) / 86400000) + 1;
      const week = Math.ceil(dayDiff / 7);
      const key = `${dt.getFullYear()}-Uke${week}`;
      weekly[key] = (weekly[key] || 0) + 1;
    }
  });
  const weeklyLabels = Object.keys(weekly).sort();
  const weeklyData = weeklyLabels.map(k => weekly[k]);

  // Fordeling på dokumenttyper
  const types = {};
  filtered.forEach(d => {
    const t = d.dokumenttype || "Ukjent";
    types[t] = (types[t] || 0) + 1;
  });
  const typeLabels = Object.keys(types).sort();
  const typeData = typeLabels.map(k => types[k]);

  const weeklyCanvas = document.getElementById("chartWeekly");
  const typesCanvas = document.getElementById("chartTypes");

  if (weeklyChart) weeklyChart.destroy();
  if (typesChart) typesChart.destroy();

  weeklyChart = new Chart(weeklyCanvas, {
    type: 'bar',
    data: {
      labels: weeklyLabels,
      datasets: [{
        label: 'Publisert',
        data: weeklyData,
        backgroundColor: '#1f6feb'
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { autoSkip: true, maxRotation: 0 } },
        y: { beginAtZero: true, precision: 0 }
      }
    }
  });

  typesChart = new Chart(typesCanvas, {
    type: 'pie',
    data: {
      labels: typeLabels,
      datasets: [{
        data: typeData,
        backgroundColor: ['#1f6feb','#b78103','#7d3fc2','#0ea5a5','#8b5e34','#14532d','#667085','#e11d48','#06b6d4','#22c55e']
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { position: 'bottom' } }
    }
  });
}

// Init fra URL params og første render
function applyParamsFromURL() {
  const url = new URL(window.location.href);
  const q = url.searchParams.get("q") || "";
  const am = url.searchParams.get("am") || "";
  const type = url.searchParams.get("type") || "";
  const status = url.searchParams.get("status") || "";
  const from = url.searchParams.get("from") || "";
  const to = url.searchParams.get("to") || "";
  const sort = url.searchParams.get("sort") || "dato-desc";
  const pp = parseInt(url.searchParams.get("perPage") || String(perPage), 10);
  const pg = parseInt(url.searchParams.get("page") || "1", 10);

  document.getElementById("searchInput").value = q;
  document.getElementById("searchAM").value = am;
  document.getElementById("filterType").value = type;
  document.getElementById("statusFilter").value = status;
  document.getElementById("dateFrom").value = from;
  document.getElementById("dateTo").value = to;
  document.getElementById("sortSelect").value = sort;

  const perPageSelect = document.getElementById("perPage");
  const opt = Array.from(perPageSelect.options).find(o => parseInt(o.value,10) === pp);
  if (opt) perPageSelect.value = String(pp);

  currentSearch = q;
  currentSearchAM = am;
  currentFilter = type;
  currentStatus = status;
  dateFrom = from;
  dateTo = to;
  currentSort = sort;
  perPage = pp;
  currentPage = pg;
}

document.addEventListener("DOMContentLoaded", () => {
  applyParamsFromURL();
  renderPage(currentPage);
});
