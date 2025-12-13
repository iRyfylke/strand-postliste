// Statistikk og diagrammer med Chart.js

let weeklyChart = null;
let typesChart = null;

export function buildStats(filtered) {
  // Publisert per uke (forenklet uke-beregning)
  const weekly = {};
  filtered.forEach(d => {
    if (d.status === "Publisert" && d.dato) {
      const dt = parseDDMMYYYY(d.dato);
      if (!dt) return;
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
  if (!weeklyCanvas || !typesCanvas) return;

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
        backgroundColor: [
          '#1f6feb','#b78103','#7d3fc2','#0ea5a5','#8b5e34',
          '#14532d','#667085','#e11d48','#06b6d4','#22c55e'
        ]
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { position: 'bottom' } }
    }
  });
}
