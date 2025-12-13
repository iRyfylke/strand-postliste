let currentFilter = "";
let currentSearch = "";
let currentStatus = "";
let currentSort = "dato-desc";
let dateFrom = "";
let dateTo = "";
let perPage = 25; // default, kan overstyres av dropdown
let currentPage = 1;

function applySearch() {
  const input = document.getElementById("searchInput");
  currentSearch = input ? input.value.trim() : "";
  currentPage = 1;
  renderPage(currentPage);
}

function applyDateFilter() {
  const fromEl = document.getElementById("dateFrom");
  const toEl = document.getElementById("dateTo");
  dateFrom = fromEl ? fromEl.value : "";
  dateTo = toEl ? toEl.value : "";
  currentPage = 1;
  renderPage(currentPage);
}

function applyFilter() {
  const el = document.getElementById("filterType");
  currentFilter = el ? el.value : "";
  currentPage = 1;
  renderPage(currentPage);
}

function applyStatusFilter() {
  const el = document.getElementById("statusFilter");
  currentStatus = el ? el.value : "";
  currentPage = 1;
  renderPage(currentPage);
}

function applySort() {
  const el = document.getElementById("sortSelect");
  currentSort = el ? el.value : "dato-desc";
  currentPage = 1;
  renderPage(currentPage);
}

function changePerPage() {
  const el = document.getElementById("perPage");
  perPage = el ? parseInt(el.value, 10) : perPage;
  currentPage = 1;
  renderPage(currentPage);
}

// Koble alle filterfelter til event listeners
document.addEventListener("DOMContentLoaded", () => {
  // Søkefelt oppdateres mens du skriver
  const searchInput = document.getElementById("searchInput");
  if (searchInput) {
    searchInput.addEventListener("input", applySearch);
  }

  // Dato-filter oppdateres når du endrer feltene
  const dateFromEl = document.getElementById("dateFrom");
  const dateToEl = document.getElementById("dateTo");
  if (dateFromEl) dateFromEl.addEventListener("change", applyDateFilter);
  if (dateToEl) dateToEl.addEventListener("change", applyDateFilter);

  // Dropdown for type-filter
  const filterTypeEl = document.getElementById("filterType");
  if (filterTypeEl) filterTypeEl.addEventListener("change", applyFilter);

  // Status-filter
  const statusFilterEl = document.getElementById("statusFilter");
  if (statusFilterEl) statusFilterEl.addEventListener("change", applyStatusFilter);

  // Sorteringsvalg
  const sortSelectEl = document.getElementById("sortSelect");
  if (sortSelectEl) sortSelectEl.addEventListener("change", applySort);

  // Antall per side
  const perPageEl = document.getElementById("perPage");
  if (perPageEl) perPageEl.addEventListener("change", changePerPage);
});
