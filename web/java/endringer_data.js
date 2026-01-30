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
    const index = await indexRes.json();

    // 2. Hent liste over shard-filer
    const shardFiles = index; // index er en liste med filnavn

    // 3. Last alle shards parallelt
    const shardPromises = shardFiles.map(async (filename) => {
        const res = await fetch(`../data/shards/${filename}`);
        return res.json(); // hver shard er en ren liste
    });

    const shardData = await Promise.all(shardPromises);

    // 4. Slå sammen alle entries til én liste
    const allEntries = shardData.flat();

    // 5. Lag et map: dokumentID → dokument
    const map = {};
    for (const d of allEntries) {
        map[d.dokumentID] = d;
    }

    return map;
}

