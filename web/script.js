// Entry point for å hente inn modulene fra web/java/

import './java/filters.js';
import { renderPage, setData } from './java/render.js';
import { loadPostliste } from './java/endringer_data.js';
import './java/export.js';
import './java/stats.js';

// Global konfig (brukes av filters.js)
window.perPage = 50;

document.addEventListener("DOMContentLoaded", async () => {
  // 1. Last datasettet fra shards
  const map = await loadPostliste();

  // 2. Konverter map → array (render.js forventer en liste)
  const arr = Object.values(map);

  // 3. Sett data i render.js
  setData(arr);

  // 4. Hent side fra URL
  const params = new URLSearchParams(window.location.search);
  const page = parseInt(params.get("page"), 10);

  // 5. Render første side
  renderPage(!isNaN(page) ? page : 1);
});
