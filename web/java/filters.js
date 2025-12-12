let currentFilter = "";
let currentSearch = "";
let currentStatus = "";
let currentSort = "dato-desc";
let dateFrom = "";
let dateTo = "";

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
/*
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
*/
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

