// ===============================
//  endringer_tables.js
//  Tabeller og detaljvisning
// ===============================

export function renderTables(changes, postliste) {

    // ---------------------------
    // 1. Siste endringer
    // ---------------------------
    const tbody = document.querySelector("#table-latest-changes tbody");
    tbody.innerHTML = "";

    const latest = changes.slice(0, 50);

    for (const c of latest) {
        const tr = document.createElement("tr");

        tr.innerHTML = `
            <td>${c.tidspunkt}</td>
            <td>${c.dokumentID}</td>
            <td>${postliste[c.dokumentID]?.tittel || ""}</td>
            <td>${c.type}</td>
            <td>${Object.keys(c.endringer || {}).join(", ")}</td>
        `;

        tr.addEventListener("click", () => showDetail(c, postliste));

        tbody.appendChild(tr);
    }


    // ---------------------------
    // 2. Dokumenter med flest endringer
    // ---------------------------
    const counts = {};

    for (const c of changes) {
        counts[c.dokumentID] = (counts[c.dokumentID] || 0) + 1;
    }

    const sorted = Object.entries(counts)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 50);

    const tbody2 = document.querySelector("#table-most-changed tbody");
    tbody2.innerHTML = "";

    for (const [docID, count] of sorted) {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${docID}</td>
            <td>${postliste[docID]?.tittel || ""}</td>
            <td>${count}</td>
        `;
        tbody2.appendChild(tr);
    }


    // ---------------------------
    // 3. Dokumenter med nye filer
    // ---------------------------
    const tbody3 = document.querySelector("#table-new-files tbody");
    tbody3.innerHTML = "";

    const fileChanges = changes.filter(c =>
        c.endringer && c.endringer.filer_count
    );

    for (const c of fileChanges.slice(0, 50)) {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${c.dokumentID}</td>
            <td>${postliste[c.dokumentID]?.tittel || ""}</td>
            <td>${c.endringer.filer_count?.ny || "?"}</td>
        `;
        tbody3.appendChild(tr);
    }
}


// ---------------------------
//  Detaljvisning
// ---------------------------

function showDetail(change, postliste) {
    const section = document.getElementById("detail-section");
    const container = document.getElementById("detail-content");

    section.classList.remove("hidden");

    const doc = postliste[change.dokumentID];

    container.innerHTML = `
        <h3>${doc?.tittel || "Ukjent dokument"}</h3>
        <p><strong>DokumentID:</strong> ${change.dokumentID}</p>
        <p><strong>Tidspunkt:</strong> ${change.tidspunkt}</p>
        <p><strong>Type:</strong> ${change.type}</p>

        <h4>Endringer:</h4>
        <pre>${JSON.stringify(change.endringer, null, 2)}</pre>
    `;
}
