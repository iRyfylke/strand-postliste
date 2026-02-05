import json
from datetime import datetime, date
from pathlib import Path

# ---------------------------------------------------------
# PATHS
# ---------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT / "data"
ARCHIVE_DIR = DATA_DIR / "archive_new"
SHARDS_DIR = DATA_DIR / "shards"
CHANGES_DIR = DATA_DIR / "changes"

SHARD_INDEX_FILE = DATA_DIR / "postliste_index.json"
CHANGES_INDEX_FILE = CHANGES_DIR / "changes_index.json"

SHARD_PREFIX = "postliste_"
SHARD_MAX_BYTES = 50 * 1024 * 1024  # 50 MB margin mot GitHub 100 MB-grense


# ---------------------------------------------------------
# GENERELLE HJELPERE
# ---------------------------------------------------------
def ensure_directories():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def ensure_file(path, default):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(json.dumps(default, ensure_ascii=False, indent=2), encoding="utf-8")


def load_config(path):
    ensure_file(path, {
        "start_page": 1,
        "max_pages": 100,
        "per_page": 100
    })
    return json.loads(Path(path).read_text(encoding="utf-8"))


def atomic_write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


# ---------------------------------------------------------
# SHARD-LESING
# ---------------------------------------------------------
def load_all_postliste_from_shards(folder="data/shards"):
    folder = (ROOT / folder).resolve()
    folder.mkdir(parents=True, exist_ok=True)

    index_file = folder.parent / "postliste_index.json"

    if index_file.exists():
        try:
            names = json.loads(index_file.read_text(encoding="utf-8"))
            shard_paths = [folder / name for name in names]
        except Exception:
            shard_paths = sorted(folder.glob("postliste_*.json"))
    else:
        shard_paths = sorted(folder.glob("postliste_*.json"))

    merged = {}
    all_list = []

    for path in shard_paths:
        try:
            docs = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(docs, list):
                for d in docs:
                    did = d.get("dokumentID")
                    if did:
                        merged[did] = d
                all_list.extend(docs)
        except Exception as e:
            print(f"[WARN] Klarte ikke lese shard {path}: {e}")

    return merged, all_list


# ---------------------------------------------------------
# SHARD-SKRIVING
# ---------------------------------------------------------
def merge_and_save_sharded_to_folder(existing_dict, new_docs, folder="data/shards"):
    folder = (ROOT / folder).resolve()
    folder.mkdir(parents=True, exist_ok=True)

    updated = dict(existing_dict)
    for d in new_docs:
        updated[d["dokumentID"]] = d

    save_postliste_sharded_to_folder(list(updated.values()), folder)


def save_postliste_sharded_to_folder(all_docs, folder):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)

    def sort_key(x):
        for key in ("dato_iso", "dato"):
            v = x.get(key)
            if not v:
                continue
            try:
                if key == "dato_iso":
                    return datetime.fromisoformat(v).date()
                return datetime.strptime(v, "%d.%m.%Y").date()
            except Exception:
                continue
        return date.min

    all_docs_sorted = sorted(all_docs, key=sort_key, reverse=True)

    shards = []
    chunk = []
    index = 0
    MAX_PER_SHARD = 10000

    for doc in all_docs_sorted:
        chunk.append(doc)
        if len(chunk) >= MAX_PER_SHARD:
            shard_path = folder / f"postliste_{index}.json"
            atomic_write(shard_path, chunk)
            shards.append(shard_path)
            chunk = []
            index += 1

    if chunk:
        shard_path = folder / f"postliste_{index}.json"
        atomic_write(shard_path, chunk)
        shards.append(shard_path)

    index_file = folder.parent / "postliste_index.json"
    names = [p.name for p in shards]
    atomic_write(index_file, names)

    print(f"[INFO] Skrev {len(shards)} shards til {folder}")


# ---------------------------------------------------------
# CHANGES (sharded)
# ---------------------------------------------------------
def load_changes_sharded(folder="data/changes"):
    folder = (ROOT / folder).resolve()
    folder.mkdir(parents=True, exist_ok=True)

    index_file = folder / "changes_index.json"

    if index_file.exists():
        try:
            names = json.loads(index_file.read_text(encoding="utf-8"))
            shard_paths = [folder / name for name in names]
        except Exception:
            shard_paths = sorted(folder.glob("changes_*.json"))
    else:
        shard_paths = sorted(folder.glob("changes_*.json"))

    all_changes = []

    for path in shard_paths:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                all_changes.extend(data)
        except Exception as e:
            print(f"[WARN] Klarte ikke lese changes-shard {path}: {e}")

    return all_changes


def save_changes_sharded(changes, folder="data/changes"):
    folder = (ROOT / folder).resolve()
    folder.mkdir(parents=True, exist_ok=True)

    shards = []
    current = []
    current_index = 1

    def shard_path(idx):
        return folder / f"changes_{idx}.json"

    for entry in changes:
        current.append(entry)
        serialized = json.dumps(current, ensure_ascii=False)
        if len(serialized.encode("utf-8")) > SHARD_MAX_BYTES:
            last = current.pop()
            path = shard_path(current_index)
            atomic_write(path, current)
            shards.append(path)
            current_index += 1
            current = [last]

    if current:
        path = shard_path(current_index)
        atomic_write(path, current)
        shards.append(path)

    index_file = folder / "changes_index.json"
    names = [p.name for p in shards]
    atomic_write(index_file, names)

    print(f"[INFO] Lagret {len(shards)} changes-shards i {folder}")
