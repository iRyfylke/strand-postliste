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

    const latest = changes
    .filter(c => c.type === "UPDATE")
    .slice(0, 20);

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
        .slice(0, 20);

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

    for (const c of fileChanges.slice(0, 20)) {
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
//  POPUP-DETALJVISNING
// ---------------------------

function showDetail(change, postliste) {
    const modal = document.getElementById("detail-modal");
    const body = document.getElementById("modal-body");

    const doc = postliste[change.dokumentID];

    body.innerHTML = `
        <h2>${doc?.tittel || "Ukjent dokument"}</h2>
        <p><strong>DokumentID:</strong> ${change.dokumentID}</p>
        <p><strong>Tidspunkt:</strong> ${change.tidspunkt}</p>
        <p><strong>Type:</strong> ${change.type}</p>

        <h3>Endringer:</h3>
        <pre>${JSON.stringify(change.endringer, null, 2)}</pre>
    `;

    modal.classList.remove("hidden");
}

document.getElementById("modal-close").addEventListener("click", () => {
    document.getElementById("detail-modal").classList.add("hidden");
});
