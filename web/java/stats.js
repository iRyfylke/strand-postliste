// stats.js – Statistikk og diagrammer med Chart.js
import { parseDDMMYYYY } from './render.js';

// Chart-instansene (slik at vi kan destroy() ved oppdatering)
let monthlyChart = null;
let typesChart = null;
let statusChart = null;
let yearChart = null;

export function initStats(data) {
  if (!Array.isArray(data)) {
    console.error("Data er ikke en liste:", data);
    return;
  }

  buildCharts(data);
}

function buildCharts(data) {
  // ============================
  // Forhåndsallokerte datastrukturer
  // ============================
  const perMonth = {};
  const perType = {};
  const perStatus = { "Publisert": 0, "Må bes om innsyn": 0 };
  const perYear = {};

  // ============================
  // Én gjennomgang av alle dokumenter
  // ============================
  for (const d of data) {
    // Dokumenttype
    const type = d.dokumenttype || "Ukjent";
    perType[type] = (perType[type] || 0) + 1;

    // Status
    if (d.status === "Publisert") perStatus["Publisert"]++;
    else perStatus["Må bes om innsyn"]++;

    // Dato (må være gyldig)
    const dt = parseDDMMYYYY(d.dato);
    if (!dt) continue;

    // Per måned
    const monthKey = `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, "0")}`;
    perMonth[monthKey] = (perMonth[monthKey] || 0) + 1;

    // Per år
    const year = dt.getFullYear();
    perYear[year] = (perYear[year] || 0) + 1;
  }

  // ============================
  // Konverter til arrays for Chart.js
  // ============================
  const monthLabels = Object.keys(perMonth).sort();
  const monthData = monthLabels.map(k => perMonth[k]);

  const typeLabels = Object.keys(perType).sort();
  const typeData = typeLabels.map(k => perType[k]);

  const statusLabels = Object.keys(perStatus);
  const statusData = statusLabels.map(k => perStatus[k]);

  const yearLabels = Object.keys(perYear).sort();
  const yearData = yearLabels.map(k => perYear[k]);

  // ============================
  // Hent canvas-elementer
  // ============================
  const cMonth = document.getElementById("chartPerMonth");
  const cType = document.getElementById("chartPerType");
  const cStatus = document.getElementById("chartStatus");
  const cYear = document.getElementById("chartPerYear");

  if (!cMonth || !cType || !cStatus || !cYear) {
    console.warn("Statistikk-canvas mangler i HTML");
    return;
  }

  // ============================
  // Destroy gamle grafer
  // ============================
  monthlyChart?.destroy();
  typesChart?.destroy();
  statusChart?.destroy();
  yearChart?.destroy();

  // ============================
  // 📈 Dokumenter per måned
  // ============================
  monthlyChart = new Chart(cMonth, {
    type: 'line',
    data: {
      labels: monthLabels,
      datasets: [{
        label: 'Dokumenter per måned',
        data: monthData,
        borderColor: '#1f6feb',
        backgroundColor: 'rgba(31, 111, 235, 0.2)',
        tension: 0.2
      }]
    },
    options: {
      responsive: true,
      scales: { y: { beginAtZero: true } }
    }
  });

  // ============================
  // 📄 Dokumenter per type
  // ============================
  typesChart = new Chart(cType, {
    type: 'bar',
    data: {
      labels: typeLabels,
      datasets: [{
        label: 'Antall dokumenter',
        data: typeData,
        backgroundColor: '#7d3fc2'
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true } }
    }
  });

  // ============================
  // 📊 Publisert vs. Innsyn
  // ============================
  statusChart = new Chart(cStatus, {
    type: 'pie',
    data: {
      labels: statusLabels,
      datasets: [{
        data: statusData,
        backgroundColor: ['#1a7f37', '#b42318']
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { position: 'bottom' } }
    }
  });

  // ============================
  // 📅 Dokumenter per år
  // ============================
  yearChart = new Chart(cYear, {
    type: 'bar',
    data: {
      labels: yearLabels,
      datasets: [{
        label: 'Dokumenter per år',
        data: yearData,
        backgroundColor: '#0ea5a5'
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true } }
    }
  });
}
