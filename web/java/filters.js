import { renderPage, setSearch, setFilter, setStatus, setDateRange, setSort, setPage } from './render.js';

// === Filterfunksjoner ===
function applySearch() {
  const input = document.getElementById("searchInput");
  setSearch(input ? input.value.trim() : "");
  setPage(1);
  renderPage(1);
}

function applyDateFilter() {
  const fromEl = document.getElementById("dateFrom");
  const toEl = document.getElementById("dateTo");
  setDateRange(fromEl ? fromEl.value : "", toEl ? toEl.value : "");
  setPage(1);
  renderPage(1);
}

function applyFilter() {
  const el = document.getElementById("filterType");
  setFilter(el ? el.value : "");
  setPage(1);
  renderPage(1);
}

function applyStatusFilter() {
  const el = document.getElementById("statusFilter");
  setStatus(el ? el.value : "");
  setPage(1);
  renderPage(1);
}

function applySort() {
  const el = document.getElementById("sortSelect");
  setSort(el ? el.value : "dato-desc");
  setPage(1);
  renderPage(1);
}

function changePerPage() {
  const el = document.getElementById("perPage");
  if (el && el.value) {
    const newVal = parseInt(el.value, 10);
    if (!isNaN(newVal)) {
      perPage = newVal; // perPage er definert i template.html
    }
  }
  setPage(1);
  renderPage(1);
}

// === Koble filterfelter til event listeners ===
document.addEventListener("DOMContentLoaded", () => {
  const searchInput = document.getElementById("searchInput");
  if (searchInput) searchInput.addEventListener("input", applySearch);

  const dateFromEl = document.getElementById("dateFrom");
  const dateToEl = document.getElementById("dateTo");
  if (dateFromEl) dateFromEl.addEventListener("change", applyDateFilter);
  if (dateToEl) dateToEl.addEventListener("change", applyDateFilter);

  const filterTypeEl = document.getElementById("filterType");
  if (filterTypeEl) filterTypeEl.addEventListener("change", applyFilter);

  const statusFilterEl = document.getElementById("statusFilter");
  if (statusFilterEl) statusFilterEl.addEventListener("change", applyStatusFilter);

  const sortSelectEl = document.getElementById("sortSelect");
  if (sortSelectEl) sortSelectEl.addEventListener("change", applySort);

  const perPageEl = document.getElementById("perPage");
  if (perPageEl) perPageEl.addEventListener("change", changePerPage);
});
