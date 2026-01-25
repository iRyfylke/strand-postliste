#!/usr/bin/env python3
import os
import json
import hashlib
from pathlib import Path

DATA_DIR = Path("data")
ARCHIVE_DIR = DATA_DIR / "archive"
SHARDS_DIR = DATA_DIR / "shards"
TEMP_STREAM = DATA_DIR / "tmp_stream.jsonl"
INDEX_FILE = DATA_DIR / "postliste_index.json"

ENTRIES_PER_SHARD = 10000  # kan flyttes til config.json senere


def ensure_dirs():
    SHARDS_DIR.mkdir(exist_ok=True)
    if TEMP_STREAM.exists():
        TEMP_STREAM.unlink()


def iter_archive_files():
    """Returnerer alle filer som skal inngå i merge."""
    for f in sorted(ARCHIVE_DIR.glob("*.json")):
        yield f
    # inkluder gamle postliste_1.json
    old = DATA_DIR / "postliste_1.json"
    if old.exists():
        yield old


def stream_entries():
    """Streamer alle entries til en midlertidig fil, deduper via ID."""
    seen = set()
    count = 0

    with TEMP_STREAM.open("w", encoding="utf-8") as out:
        for file in iter_archive_files():
            print(f"[INFO] Leser {file}")
            try:
                with file.open("r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                print(f"[WARN] Klarte ikke lese {file}: {e}")
                continue

            for entry in data:
                entry_id = entry.get("id")
                if not entry_id:
                    continue
                if entry_id in seen:
                    continue
                seen.add(entry_id)

                # skriv som én linje
                out.write(json.dumps(entry, ensure_ascii=False) + "\n")
                count += 1

    print(f"[INFO] Streamet {count} unike entries")
    return count


def extract_metadata():
    """Leser stream-filen og bygger en liste med (dato, offset)."""
    metadata = []
    with TEMP_STREAM.open("r", encoding="utf-8") as f:
        offset = 0
        for line in f:
            try:
                obj = json.loads(line)
            except:
                offset += len(line.encode("utf-8"))
                continue

            dato = obj.get("dato") or obj.get("date") or ""
            metadata.append((dato, offset))
            offset += len(line.encode("utf-8"))

    print(f"[INFO] Metadata entries: {len(metadata)}")
    return metadata


def sort_metadata(metadata):
    """Sorter etter dato (strengsortering fungerer siden datoformatet er ISO)."""
    metadata.sort(key=lambda x: x[0])
    print("[INFO] Metadata sortert etter dato")
    return metadata


def write_shards(metadata):
    """Streamer entries ut i sortert rekkefølge og chunker i shards."""
    total = len(metadata)
    shard_index = 0
    written = 0

    # åpne stream for random access
    with TEMP_STREAM.open("r", encoding="utf-8") as f:

        def read_entry_at(offset):
            f.seek(offset)
            line = f.readline()
            return json.loads(line)

        while written < total:
            chunk = metadata[written:written + ENTRIES_PER_SHARD]
            shard_file = SHARDS_DIR / f"postliste_{shard_index}.json"

            entries = []
            for _, offset in chunk:
                entries.append(read_entry_at(offset))

            with shard_file.open("w", encoding="utf-8") as out:
                json.dump(entries, out, ensure_ascii=False, indent=2)

            print(f"[INFO] Skrev {shard_file} ({len(entries)} entries)")

            written += len(chunk)
            shard_index += 1

    return shard_index, total


def write_index(num_shards, total_entries):
    index = {
        "total_entries": total_entries,
        "entries_per_shard": ENTRIES_PER_SHARD,
        "shards": []
    }

    start = 0
    for i in range(num_shards):
        end = min(start + ENTRIES_PER_SHARD - 1, total_entries - 1)
        index["shards"].append({
            "file": f"postliste_{i}.json",
            "start": start,
            "end": end
        })
        start += ENTRIES_PER_SHARD

    with INDEX_FILE.open("w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f"[INFO] Skrev index til {INDEX_FILE}")


def main():
    print("[INFO] Starter build-shards (streaming + sortering etter dato)")
    ensure_dirs()

    total = stream_entries()
    metadata = extract_metadata()
    metadata = sort_metadata(metadata)
    num_shards, total_entries = write_shards(metadata)
    write_index(num_shards, total_entries)

    print("[INFO] Ferdig!")


if __name__ == "__main__":
    main()
