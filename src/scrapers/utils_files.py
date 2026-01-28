import os
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

def get_changes_file():
    return get_data_dir() / "changes.json"

def get_shard_index_file():
    return get_data_dir() / "postliste_index.json"

SHARD_PREFIX = "postliste_"
SHARD_MAX_BYTES = 50 * 1024 * 1024  # 50 MB


# =========================================================
#   GENERELLE HJELPERE
# =========================================================

def ensure_directories():
    data_dir = get_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)

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


# =========================================================
#   ARCHIVE-FUNKSJONER
# =========================================================

def load_archive_year(year):
    archive_dir = get_data_dir() / "archive"
    archive_files = sorted(archive_dir.glob(f"postliste_{year}_*.json"))
    existing = {}

    print(f"[INFO] Leser archive-filer for år {year}…")

    for f in archive_files:
        try:
            with f.open("r", encoding="utf-8") as infile:
                docs = json.load(infile)
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
    missing = []
    for d in scraped_docs:
        did = d.get("dokumentID")
        if did and did not in archive_dict:
            missing.append(d)
    return missing


def append_missing(year, new_docs):
    if not new_docs:
        print(f"[INFO] Ingen nye missing-dokumenter å lagre for {year}.")
        return

    archive_dir = get_data_dir() / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)

    missing_path = archive_dir / f"missing_{year}.json"

    existing_docs = []
    if missing_path.exists():
        try:
            existing_docs = json.loads(missing_path.read_text(encoding="utf-8"))
            if not isinstance(existing_docs, list):
                existing_docs = []
        except Exception as e:
            print(f"[WARN] Klarte ikke å lese eksisterende missing-fil {missing_path}: {e}")

    merged_by_id = {}

    for d in existing_docs:
        if isinstance(d, dict):
            did = d.get("dokumentID")
            if did:
                merged_by_id[did] = d

    for d in new_docs:
        if isinstance(d, dict):
            did = d.get("dokumentID")
            if did:
                merged_by_id[did] = d

    final_list = list(merged_by_id.values())
    atomic_write(missing_path, final_list)
    print(f"[INFO] Lagret/oppdatert missing_{year}.json med totalt {len(final_list)} dokumenter.")


def save_failed_pages(year, failed_pages):
    archive_dir = get_data_dir() / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)

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
    index_file = get_shard_index_file()
    names = [p.name for p in paths]
    atomic_write(index_file, names)
    print(f"[INFO] Oppdatert shard-indeks med {len(names)} filer.")


def load_all_postliste():
    ensure_directories()
    shards = _list_shard_paths()
    merged = {}
    all_list = []

    if not shards:
        return {}, []

    for path in shards:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                for d in data:
                    did = d.get("dokumentID")
                    if did:
                        merged[did] = d
                all_list.extend(data)
        except Exception as e:
            print(f"[WARN] Klarte ikke lese shard {path}: {e}")

    return merged, all_list


def save_postliste_sharded(all_docs):
    data_dir = get_data_dir()
    ensure_directories()

    def sort_key(x):
        for key in ("dato_iso", "dato"):
            v = x.get(key)
            if not v:
                continue
            try:
                return datetime.fromisoformat(v).date() if key == "dato_iso" else datetime.strptime(v, "%d.%m.%Y").date()
            except Exception:
                continue
        return date.min

    all_docs_sorted = sorted(all_docs, key=sort_key, reverse=True)

    shards = []
    current = []
    current_index = 1

    def current_path(idx):
        return data_dir / f"{SHARD_PREFIX}{idx}.json"

    for doc in all_docs_sorted:
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
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(changes, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[INFO] Lagret {len(changes)} endringshendelser i {path}")


# =========================================================
#   NYTT SHARD-SYSTEM FOR MORGENSCRAPE (data/shards/)
# =========================================================

def load_all_postliste_from_shards(folder="data/shards"):
    folder = get_root() / folder
    folder.mkdir(parents=True, exist_ok=True)

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
    folder.mkdir(parents=True, exist_ok=True)

    updated = dict(existing_dict)
    for d in new_docs:
        updated[d["dokumentID"]] = d

    save_postliste_sharded_to_folder(list(updated.values()), folder)


def save_postliste_sharded_to_folder(all_docs, folder):
    folder = get_root() / folder
    folder.mkdir(parents=True, exist_ok=True)

    def sort_key(x):
        for key in ("dato_iso", "dato"):
            v = x.get(key)
            if not v:
                continue
            try:
                return datetime.fromisoformat(v).date() if key == "dato_iso" else datetime.strptime(v, "%d.%m.%Y").date()
            except Exception:
                continue
        return date.min

    all_docs_sorted = sorted(all_docs, key=sort_key, reverse=True)

    shards = []
    current = []
    current_index = 1

    def shard_path(idx):
        return folder / f"postliste_{idx}.json"

    for doc in all_docs_sorted:
        current.append(doc)
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

    index_file = folder / "postliste_index.json"
    names = [p.name for p in shards]
    atomic_write(index_file, names)

    print(f"[INFO] Skrev {len(shards)} shards til {folder}")


# =========================================================
#   NYTT SHARD-SYSTEM FOR CHANGES (data/changes/)
# =========================================================

def load_changes_sharded(folder="data/changes"):
    folder = get_root() / folder
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
    folder = get_root() / folder
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
