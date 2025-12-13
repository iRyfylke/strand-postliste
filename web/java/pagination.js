// pagination.js – håndterer sidetall og navigasjon

function renderPagination(elementId, page, totalItems) {
  const maxPage = Math.ceil(totalItems / perPage) || 1;
  const el = document.getElementById(elementId);
  if (!el) return;

  // Bygg knappene
  el.innerHTML = "";

  const prevBtn = document.createElement("button");
  prevBtn.textContent = "◀ Forrige";
  prevBtn.disabled = page === 1;
  prevBtn.onclick = prevPage;
  el.appendChild(prevBtn);

  const info = document.createElement("span");
  info.textContent = ` Side ${page} av ${maxPage} `;
  el.appendChild(info);

  const nextBtn = document.createElement("button");
  nextBtn.textContent = "Neste ▶";
  nextBtn.disabled = page >= maxPage;
  nextBtn.onclick = nextPage;
  el.appendChild(nextBtn);
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
