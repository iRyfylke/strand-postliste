#!/usr/bin/env python3
import os
import glob
import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

# ---------------------------------------------------------
# PATHS
# ---------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
ARCHIVE_DIR = DATA_DIR / "archive"

CHUNK_PREFIX = "postliste_"
CHUNK_MAX_BYTES = 50 * 1024 * 1024  # 50 MB
INDEX_FILE = DATA_DIR / "postliste_index.json"


# ---------------------------------------------------------
# Hjelpefunksjoner
# ---------------------------------------------------------
def iter_archive_files() -> List[Path]:
    """Finn alle archive-filer som inneholder postliste-data."""
    pattern = str(ARCHIVE_DIR / "postliste_*.json")
    files = [Path(p) for p in glob.glob(pattern)]
    files = [
        f for f in files
        if "missing_" not in f.name and "failed_pages" not in f.name
    ]
    files.sort()
    return files


def load_unique_docs() -> List[Dict[str, Any]]:
    """Les alle archive-filer og dedupe basert på dokumentID."""
    seen_ids = set()
    all_docs: List[Dict[str, Any]] = []

    files = iter_archive_files()
    print(f"[INFO] Fant {len(files)} archive-filer.")

    for f in files:
        print(f"[INFO] Leser {f} …")
        try:
            with f.open("r", encoding="utf-8") as infile:
                docs = json.load(infile)
        except Exception as e:
            print(f"[WARN] Klarte ikke å lese {f}: {e}")
            continue

        if not isinstance(docs, list):
            print(f"[WARN] Filen {f} inneholder ikke en liste. Hopper over.")
            continue

        for d in docs:
            dokid = d.get("dokumentID")
            if dokid:
                if dokid in seen_ids:
                    continue
                seen_ids.add(dokid)

            all_docs.append(d)

    print(f"[INFO] Totalt {len(all_docs)} unike dokumenter samlet.")
    return all_docs


def sort_docs(docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sorter dokumenter kronologisk (eldst → nyest)."""

    def key_fn(d: Dict[str, Any]):
        if d.get("dato_iso"):
            try:
                return datetime.fromisoformat(d["dato_iso"])
            except Exception:
                pass
        if d.get("dato"):
            try:
                return datetime.strptime(d["dato"], "%d.%m.%Y")
            except Exception:
                pass
        return datetime.min

    docs_sorted = sorted(docs, key=key_fn)
    print("[INFO] Dokumenter sortert kronologisk.")
    return docs_sorted


def chunk_size_bytes(chunk: List[Dict[str, Any]]) -> int:
    """Returner faktisk størrelse i bytes for JSON-serialisert chunk."""
    return len(json.dumps(chunk, ensure_ascii=False).encode("utf-8"))


def write_chunks(docs: List[Dict[str, Any]]):
    """Skriv ut dokumentene i shards + indexfil."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    chunk_index = 1
    current_chunk: List[Dict[str, Any]] = []
    index_entries = []

    def chunk_path(idx: int) -> Path:
        return DATA_DIR / f"{CHUNK_PREFIX}{idx}.json"

    for doc in docs:
        test_chunk = current_chunk + [doc]
        size = chunk_size_bytes(test_chunk)

        if size > CHUNK_MAX_BYTES and current_chunk:
            # Skriv eksisterende chunk
            out_path = chunk_path(chunk_index)
            with out_path.open("w", encoding="utf-8") as outfile:
                json.dump(current_chunk, outfile, ensure_ascii=False, indent=2)

            # Metadata
            index_entries.append({
                "file": out_path.name,
                "count": len(current_chunk),
                "size_mb": round(chunk_size_bytes(current_chunk) / 1024 / 1024, 2),
                "first_date": current_chunk[0].get("dato_iso") or current_chunk[0].get("dato"),
                "last_date": current_chunk[-1].get("dato_iso") or current_chunk[-1].get("dato"),
            })

            print(
                f"[INFO] Skrev {out_path.name} "
                f"({len(current_chunk)} dokumenter, "
                f"{chunk_size_bytes(current_chunk)/1024/1024:.2f} MB)"
            )

            chunk_index += 1
            current_chunk = [doc]
        else:
            current_chunk.append(doc)

    # Siste chunk
    if current_chunk:
        out_path = chunk_path(chunk_index)
        with out_path.open("w", encoding="utf-8") as outfile:
            json.dump(current_chunk, outfile, ensure_ascii=False, indent=2)

        index_entries.append({
            "file": out_path.name,
            "count": len(current_chunk),
            "size_mb": round(chunk_size_bytes(current_chunk) / 1024 / 1024, 2),
            "first_date": current_chunk[0].get("dato_iso") or current_chunk[0].get("dato"),
            "last_date": current_chunk[-1].get("dato_iso") or current_chunk[-1].get("dato"),
        })

        print(
            f"[INFO] Skrev {out_path.name} "
            f"({len(current_chunk)} dokumenter, "
            f"{chunk_size_bytes(current_chunk)/1024/1024:.2f} MB)"
        )

    # Skriv indexfil
    with INDEX_FILE.open("w", encoding="utf-8") as f:
        json.dump(index_entries, f, ensure_ascii=False, indent=2)

    print(f"[INFO] Skrev indexfil: {INDEX_FILE}")
    print(f"[INFO] Ferdig. Totalt {len(index_entries)} shards generert.")


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
def main():
    print("[INFO] Starter bygging av postliste-chunks fra data/archive/ …")
    docs = load_unique_docs()
    docs = sort_docs(docs)
    write_chunks(docs)
    print("[INFO] Bygging av shards fullført.")


if __name__ == "__main__":
    main()
