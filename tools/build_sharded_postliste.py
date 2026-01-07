import json
from pathlib import Path
from datetime import datetime, date

DATA_DIR = Path("data")
ARCHIVE_DIR = DATA_DIR / "archive"
OUTPUT_DIR = DATA_DIR

SHARD_PREFIX = "postliste_"
SHARD_MAX_BYTES = 50 * 1024 * 1024
SHARD_INDEX_FILE = OUTPUT_DIR / "postliste_index.json"


def sort_key(x):
    for key in ("dato_iso", "dato"):
        v = x.get(key)
        if not v:
            continue
        try:
            if key == "dato_iso":
                return datetime.fromisoformat(v).date()
            else:
                return datetime.strptime(v, "%d.%m.%Y").date()
        except Exception:
            continue
    return date.min


def atomic_write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def main():
    all_docs = []

    # 1) Les alle årsfilene fra data/archive/
    for path in sorted(ARCHIVE_DIR.glob("postliste_*.json")):
        print(f"[INFO] Leser arkivfil {path}")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                all_docs.extend(data)
        except Exception as e:
            print(f"[WARN] Klarte ikke lese {path}: {e}")

    # 2) Hvis du vil inkludere eksisterende data/postliste.json:
    legacy = DATA_DIR / "postliste.json"
    if legacy.exists():
        print(f"[INFO] Leser legacy {legacy}")
        try:
            data = json.loads(legacy.read_text(encoding="utf-8"))
            if isinstance(data, list):
                all_docs.extend(data)
        except Exception as e:
            print(f"[WARN] Klarte ikke lese {legacy}: {e}")

    # 3) Dedup basert på dokumentID
    merged = {}
    for d in all_docs:
        if not isinstance(d, dict):
            continue
        did = d.get("dokumentID")
        if not did:
            continue
        merged[did] = d

    docs = list(merged.values())
    docs_sorted = sorted(docs, key=sort_key, reverse=True)
    print(f"[INFO] Totalt {len(docs_sorted)} unike dokumenter etter sammenslåing.")

    # 4) Shard dem ut
    shards = []
    current = []
    current_index = 1

    def current_path(idx):
        return OUTPUT_DIR / f"{SHARD_PREFIX}{idx}.json"

    for doc in docs_sorted:
        current.append(doc)
        serialized = json.dumps(current, ensure_ascii=False)
        if len(serialized.encode("utf-8")) > SHARD_MAX_BYTES:
            last = current.pop()
            path = current_path(current_index)
            atomic_write(path, current)
            shards.append(path)
            print(f"[INFO] Skrev shard {path} med {len(current)} dokumenter.")
            current_index += 1
            current = [last]

    if current:
        path = current_path(current_index)
        atomic_write(path, current)
        shards.append(path)
        print(f"[INFO] Skrev shard {path} med {len(current)} dokumenter.")

    # 5) Skriv index
    atomic_write(SHARD_INDEX_FILE, [p.name for p in shards])

    total = sum(len(json.loads(p.read_text(encoding="utf-8"))) for p in shards)
    print(f"[INFO] Ferdig: {total} dokumenter fordelt på {len(shards)} shards.")
    print("[INFO] Nå kan du fase ut data/postliste.json hvis du vil.")


if __name__ == "__main__":
    main()
