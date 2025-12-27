// stats.js – Statistikk og diagrammer med Chart.js
import { parseDDMMYYYY } from './render.js';

// Chart-instansene (slik at vi kan destroy() ved oppdatering)
let weeklyChart = null;
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
  // 1) Dokumenter per måned
  // ============================
  const perMonth = {};
  data.forEach(d => {
    const dt = parseDDMMYYYY(d.dato);
    if (!dt) return;
    const key = `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, "0")}`;
    perMonth[key] = (perMonth[key] || 0) + 1;
  });

  const monthLabels = Object.keys(perMonth).sort();
  const monthData = monthLabels.map(k => perMonth[k]);

  // ============================
  // 2) Dokumenter per type
  // ============================
  const types = {};
  data.forEach(d => {
    const t = d.dokumenttype || "Ukjent";
    types[t] = (types[t] || 0) + 1;
  });

  const typeLabels = Object.keys(types).sort();
  const typeData = typeLabels.map(k => types[k]);

  // ============================
  // 3) Publisert vs. Innsyn
  // ============================
  const status = { "Publisert": 0, "Må bes om innsyn": 0 };
  data.forEach(d => {
    if (d.status === "Publisert") status["Publisert"]++;
    else status["Må bes om innsyn"]++;
  });

  const statusLabels = Object.keys(status);
  const statusData = statusLabels.map(k => status[k]);

  // ============================
  // 4) Dokumenter per år
  // ============================
  const perYear = {};
  data.forEach(d => {
    const dt = parseDDMMYYYY(d.dato);
    if (!dt) return;
    const year = dt.getFullYear();
    perYear[year] = (perYear[year] || 0) + 1;
  });

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

  // Destroy gamle grafer hvis de finnes
  if (weeklyChart) weeklyChart.destroy();
  if (typesChart) typesChart.destroy();
  if (statusChart) statusChart.destroy();
  if (yearChart) yearChart.destroy();

  // ============================
  // 📈 Dokumenter per måned
  // ============================
  weeklyChart = new Chart(cMonth, {
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
      scales: {
        y: { beginAtZero: true }
      }
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
      scales: {
        y: { beginAtZero: true }
      }
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
      scales: {
        y: { beginAtZero: true }
      }
    }
  });
}
