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

// ===============================
//  Laster shards i stedet for postliste.json
// ===============================

export async function loadPostliste() {
    // 1. Last indexfilen
    const indexRes = await fetch("../data/postliste_index.json");
    const shardFiles = await indexRes.json();

    // 2. Last alle shards parallelt
    const shardPromises = shardFiles.map(async (filename) => {
        const res = await fetch(`../data/${filename}`);
        return res.json();
    });

    const shardData = await Promise.all(shardPromises);

    // 3. Slå sammen alle entries til én liste
    const allEntries = shardData.flat();

    // 4. Lag et map: dokumentID → dokument
    const map = {};
    for (const d of allEntries) {
        map[d.dokumentID] = d;
    }

    return map;
}
