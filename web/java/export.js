// export.js – funksjoner for eksport og deling
import { getState, getFilteredData } from './render.js';

export function exportCSV() {
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

  const csv = rows
    .map(r => r.map(v => `"${String(v).replace(/"/g, '""')}"`).join(","))
    .join("\n");

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

export function exportPDF() {
  window.print();
}

export function copyShareLink() {
  const { currentSearch, currentFilter, currentStatus, dateFrom, dateTo, currentSort, currentPage } = getState();

  const params = new URLSearchParams();
  if (currentSearch) params.set("q", currentSearch);
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
    if (!el) return;
    const prev = el.textContent;
    el.textContent = "Delingslenke kopiert!";
    setTimeout(() => el.textContent = prev, 1500);
  });
}
