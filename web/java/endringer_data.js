// ===============================
//  endringer_data.js
//  Laster og parser datafiler
// ===============================

export async function loadChanges() {
    const res = await fetch("../data/changes.json");
    const data = await res.json();

    // Sorter nyeste først
    return data.sort((a, b) => new Date(b.tidspunkt) - new Date(a.tidspunkt));
}

export async function loadPostliste() {
    const res = await fetch("../data/postliste.json");
    const data = await res.json();

    // Map dokumentID → dokument
    const map = {};
    for (const d of data) {
        map[d.dokumentID] = d;
    }
    return map;
}
