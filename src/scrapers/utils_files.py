import json
from datetime import datetime, date
from pathlib import Path

# =========================================================
#   PATH-HÅNDTERING (INGEN I/O VED IMPORT)
# =========================================================

def get_root():
    """Returnerer repo-root uansett hvor scriptet kjøres fra."""
    return Path(__file__).resolve().parent.parent.parent

def get_data_dir():
    return get_root() / "data"

def get_archive_dir():
    return get_data_dir() / "archive"

def get_changes_file():
    return get_data_dir() / "changes.json"

def get_shard_index_file():
    return get_data_dir() / "postliste_index.json"

SHARD_PREFIX = "postliste_"
SHARD_MAX_BYTES = 50 * 1024 * 1024  # 50 MB


# =========================================================
#   GENERELLE HJELPERE
# =========================================================

def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)

def atomic_write(path, data):
    """Skriver JSON atomisk for å unngå korrupte filer."""
    path = Path(path)
    ensure_dir(path.parent)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


# =========================================================
#   ARCHIVE-FUNKSJONER
# =========================================================

def load_archive_year(year):
    archive_dir = get_archive_dir()
    ensure_dir(archive_dir)

    archive_files = sorted(archive_dir.glob(f"postliste_{year}_*.json"))
    existing = {}

    print(f"[INFO] Leser archive-filer for år {year}…")

    for f in archive_files:
        try:
            docs = json.loads(f.read_text(encoding="utf-8"))
            for d in docs:
                if isinstance(d, dict):
                    did = d.get("dokumentID")
                    if did:
                        existing[did] = d
        except Exception as e:
            print(f"[WARN] Klarte ikke å lese {f}: {e}")

    print(f"[INFO] Totalt {len(existing)} dokumenter funnet i archive for {year}")
    return existing


def find_missing_docs(scraped_docs, archive_dict):
    return [
        d for d in scraped_docs
        if isinstance(d, dict)
        and d.get("dokumentID")
        and d["dokumentID"] not in archive_dict
    ]


def append_missing(year, new_docs):
    archive_dir = get_archive_dir()
    ensure_dir(archive_dir)

    missing_path = archive_dir / f"missing_{year}.json"

    try:
        existing_docs = json.loads(missing_path.read_text(encoding="utf-8"))
        if not isinstance(existing_docs, list):
            existing_docs = []
    except Exception:
        existing_docs = []

    merged = {d["dokumentID"]: d for d in existing_docs if isinstance(d, dict) and d.get("dokumentID")}
    for d in new_docs:
        if isinstance(d, dict) and d.get("dokumentID"):
            merged[d["dokumentID"]] = d

    atomic_write(missing_path, list(merged.values()))
    print(f"[INFO] Lagret/oppdatert missing_{year}.json med totalt {len(merged)} dokumenter.")


def save_failed_pages(year, failed_pages):
    archive_dir = get_archive_dir()
    ensure_dir(archive_dir)

    failed_path = archive_dir / f"failed_pages_{year}.json"
    atomic_write(failed_path, failed_pages)
    print(f"[INFO] Lagret failed_pages_{year}.json med {len(failed_pages)} sider.")


# =========================================================
#   GAMMELT SHARD-SYSTEM (data/)
# =========================================================

def _list_shard_paths():
    data_dir = get_data_dir()
    index_file = get_shard_index_file()

    if index_file.exists():
        try:
            names = json.loads(index_file.read_text(encoding="utf-8"))
            return [data_dir / name for name in names]
        except Exception:
            print("[WARN] Klarte ikke lese shard-index, faller tilbake til glob.")

    return sorted(data_dir.glob(f"{SHARD_PREFIX}*.json"))


def _write_shard_index(paths):
    names = [p.name for p in paths]
    atomic_write(get_shard_index_file(), names)
    print(f"[INFO] Oppdatert shard-indeks med {len(names)} filer.")


def load_all_postliste():
    shards = _list_shard_paths()
    merged = {}
    all_list = []

    for path in shards:
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


def save_postliste_sharded(all_docs):
    data_dir = get_data_dir()
    ensure_dir(data_dir)

    def sort_key(x):
        for key in ("dato_iso", "dato"):
            v = x.get(key)
            if not v:
                continue
            try:
                return (
                    datetime.fromisoformat(v).date()
                    if key == "dato_iso"
                    else datetime.strptime(v, "%d.%m.%Y").date()
                )
            except Exception:
                continue
        return date.min

    all_docs_sorted = sorted(all_docs, key=sort_key, reverse=True)

    shards = []
    current = []
    idx = 1

    def shard_path(i):
        return data_dir / f"{SHARD_PREFIX}{i}.json"

    for doc in all_docs_sorted:
        current.append(doc)
        if len(json.dumps(current, ensure_ascii=False).encode("utf-8")) > SHARD_MAX_BYTES:
            last = current.pop()
            path = shard_path(idx)
            atomic_write(path, current)
            shards.append(path)
            print(f"[INFO] Skrev shard {path} med {len(current)} dokumenter.")
            idx += 1
            current = [last]

    if current:
        path = shard_path(idx)
        atomic_write(path, current)
        shards.append(path)
        print(f"[INFO] Skrev shard {path} med {len(current)} dokumenter.")

    _write_shard_index(shards)

    total = sum(len(json.loads(p.read_text(encoding="utf-8"))) for p in shards)
    print(f"[INFO] Totalt {total} dokumenter fordelt på {len(shards)} shards.")


def merge_and_save_sharded(existing_dict, new_docs):
    updated = dict(existing_dict)
    for d in new_docs:
        updated[d["dokumentID"]] = d
    save_postliste_sharded(list(updated.values()))


# =========================================================
#   CHANGES (GAMMELT SYSTEM)
# =========================================================

def load_changes():
    path = get_changes_file()
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_changes(changes):
    path = get_changes_file()
    ensure_dir(path.parent)
    atomic_write(path, changes)
    print(f"[INFO] Lagret {len(changes)} endringshendelser i {path}")


# =========================================================
#   NYTT SHARD-SYSTEM FOR MORGENSCRAPE (data/shards/)
# =========================================================

def load_all_postliste_from_shards(folder="data/shards"):
    folder = get_root() / folder
    ensure_dir(folder)

    index_file = folder / "postliste_index.json"

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


def merge_and_save_sharded_to_folder(existing_dict, new_docs, folder="data/shards"):
    folder = get_root() / folder
    ensure_dir(folder)

    updated = dict(existing_dict)
    for d in new_docs:
        updated[d["dokumentID"]] = d

    save_postliste_sharded_to_folder(list(updated.values()), folder)


def save_postliste_sharded_to_folder(all_docs, folder):
    folder = get_root() / folder
    ensure_dir(folder)

    def sort_key(x):
        for key in ("dato_iso", "dato"):
            v = x.get(key)
            if not v:
                continue
            try:
                return (
                    datetime.fromisoformat(v).date()
                    if key == "dato_iso"
                    else datetime.strptime(v, "%d.%m.%Y").date()
                )
            except Exception:
                continue
        return date.min

    all_docs_sorted = sorted(all_docs, key=sort_key, reverse=True)

    shards = []
    current = []
    idx = 1

    def shard_path(i):
        return folder / f"postliste_{i}.json"

    for doc in all_docs_sorted:
        current.append(doc)
        if len(json.dumps(current, ensure_ascii=False).encode("utf-8")) > SHARD_MAX_BYTES:
            last = current.pop()
            path = shard_path(idx)
            atomic_write(path, current)
            shards.append(path)
            idx += 1
            current = [last]

    if current:
        path = shard_path(idx)
        atomic_write(path, current)
        shards.append(path)

    index_file = folder / "postliste_index.json"
    names = [p.name for p in shards]
    atomic_write(index_file, names)

    print(f"[INFO] Skrev {len(shards)} shards til {folder}")


# =========================================================
#   NYTT SHARD-SYSTEM FOR CHANGES (data/changes/)
# =========================================================

def load_changes_sharded(folder="data/changes"):
    folder = get_root() / folder
    ensure_dir(folder)

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
    folder = get_root() / folder
    ensure_dir(folder)

    shards = []
    current = []
    idx = 1

    def shard_path(i):
        return folder / f"changes_{i}.json"

    for entry in changes:
        current.append(entry)
        if len(json.dumps(current, ensure_ascii=False).encode("utf-8")) > SHARD_MAX_BYTES:
            last = current.pop()
            path = shard_path(idx)
            atomic_write(path, current)
            shards.append(path)
            idx += 1
            current = [last]

    if current:
        path = shard_path(idx)
        atomic_write(path, current)
        shards.append(path)

    index_file = folder / "changes_index.json"
    names = [p.name for p in shards]
    atomic_write(index_file, names)

    print(f"[INFO] Lagret {len(shards)} changes-shards i {folder}")
