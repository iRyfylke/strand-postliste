import os
import json
from datetime import datetime, date
from pathlib import Path

# Rot for datafiler
DATA_DIR = Path("../../data")

# Endringslogg
CHANGES_FILE = DATA_DIR / "changes.json"

# Sharding-konfig
SHARD_PREFIX = "postliste_"
SHARD_INDEX_FILE = DATA_DIR / "postliste_index.json"
SHARD_MAX_BYTES = 50 * 1024 * 1024  # 50 MB margin mot GitHubs 100 MB-grense


def ensure_directories():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def ensure_file(path, default):
    """Oppretter fil med default-innhold hvis den ikke finnes."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(json.dumps(default, ensure_ascii=False, indent=2), encoding="utf-8")


def load_config(path):
    """Laster config-fil, oppretter default hvis mangler."""
    ensure_file(path, {
        "start_page": 1,
        "max_pages": 100,
        "per_page": 100
    })
    return json.loads(Path(path).read_text(encoding="utf-8"))


def atomic_write(path, data):
    """Skriver JSON atomisk for å unngå korrupte filer."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


# ------------------------------------------------------------------
#  Archive-hjelpere
# ------------------------------------------------------------------

def load_archive_year(year):
    """
    Leser alle archive-filer for et gitt år:
      data/archive/postliste_<year>_*.json

    Returnerer:
      dict { dokumentID: dokument }
    """
    archive_dir = DATA_DIR / "archive"
    archive_files = sorted(archive_dir.glob(f"postliste_{year}_*.json"))
    existing = {}

    print(f"[INFO] Leser archive-filer for år {year}…")

    for f in archive_files:
        try:
            with f.open("r", encoding="utf-8") as infile:
                docs = json.load(infile)
                for d in docs:
                    if not isinstance(d, dict):
                        continue
                    dokid = d.get("dokumentID")
                    if dokid:
                        existing[dokid] = d
        except Exception as e:
            print(f"[WARN] Klarte ikke å lese {f}: {e}")

    print(f"[INFO] Totalt {len(existing)} dokumenter funnet i archive for {year}")
    return existing

def find_missing_docs(scraped_docs, archive_dict):
    """
    Returnerer liste over dokumenter som finnes i scraped_docs,
    men ikke i archive_dict.
    """
    missing = []
    for d in scraped_docs:
        did = d.get("dokumentID")
        if did and did not in archive_dict:
            missing.append(d)
    return missing

def append_missing(year, new_docs):
    """
    Append'er nye manglende dokumenter til missing_<year>.json
    og deduper på dokumentID.

    Resultat:
      data/archive/missing_<year>.json
      inneholder ALL historisk missing, uten duplikater.
    """
    if not new_docs:
        print(f"[INFO] Ingen nye missing-dokumenter å lagre for {year}.")
        return

    archive_dir = DATA_DIR / "archive"
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
            existing_docs = []

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
    """
    Overskriver failed_pages_<year>.json med dagens liste
    over feilede sider.

    Resultat:
      data/archive/failed_pages_<year>.json
      gjenspeiler TIL ENHVER TID gjenværende feilede sider.
    """
    archive_dir = DATA_DIR / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)

    failed_path = archive_dir / f"failed_pages_{year}.json"
    atomic_write(failed_path, failed_pages)
    print(f"[INFO] Lagret failed_pages_{year}.json med {len(failed_pages)} sider.")


# ------------------------------------------------------------------
#  Sharding: postliste_1.json, postliste_2.json, ...
# ------------------------------------------------------------------

def _list_shard_paths():
    """Returnerer alle postliste_N.json som Path-objekter, sortert på N."""
    if SHARD_INDEX_FILE.exists():
        try:
            names = json.loads(SHARD_INDEX_FILE.read_text(encoding="utf-8"))
            return [DATA_DIR / name for name in names]
        except Exception:
            print("[WARN] Klarte ikke lese shard-index, faller tilbake til glob.")
    shards = sorted(DATA_DIR.glob(f"{SHARD_PREFIX}*.json"))
    return shards


def _write_shard_index(paths):
    """Oppdaterer postliste_index.json med liste over shard-filnavn."""
    names = [p.name for p in paths]
    atomic_write(SHARD_INDEX_FILE, names)
    print(f"[INFO] Oppdatert shard-indeks med {len(names)} filer.")


def load_all_postliste():
    """
    Leser ALLE postliste_N.json og returnerer:
      - dict { dokumentID: oppføring }
      - og en flat liste
    """
    ensure_directories()
    shards = _list_shard_paths()
    merged = {}
    all_list = []

    if not shards:
        return {}, []

    for path in shards:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                continue
            for d in data:
                if not isinstance(d, dict):
                    continue
                did = d.get("dokumentID")
                if not did:
                    continue
                merged[did] = d
            all_list.extend(data)
        except Exception as e:
            print(f"[WARN] Klarte ikke lese shard {path}: {e}")

    return merged, all_list


def save_postliste_sharded(all_docs):
    """
    Tar en liste med dokumenter (allerede sortert nyest først)
    og skriver dem ut til postliste_N.json-filer under DATA_DIR.
    """
    ensure_directories()

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

    all_docs_sorted = sorted(all_docs, key=sort_key, reverse=True)

    shards = []
    current = []
    current_index = 1

    def current_path(idx):
        return DATA_DIR / f"{SHARD_PREFIX}{idx}.json"

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
    """Slår sammen eksisterende dokumenter (dict) med nye dokumenter (liste)."""
    updated = dict(existing_dict)
    for d in new_docs:
        updated[d["dokumentID"]] = d

    save_postliste_sharded(list(updated.values()))


# ---------------------------------------------------------
#   Endringslogg-funksjoner for incremental scraper
# ---------------------------------------------------------

def load_changes():
    """Laster tidligere endringslogg fra changes.json."""
    path = CHANGES_FILE
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_changes(changes):
    """Lagrer endringslogg til changes.json."""
    path = CHANGES_FILE
    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text(
        json.dumps(changes, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"[INFO] Lagret {len(changes)} endringshendelser i {CHANGES_FILE}")
