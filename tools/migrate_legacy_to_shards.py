import json
import sys
from pathlib import Path

# Legg til src/scrapers i sys.path slik at utils_files kan importeres
ROOT = Path(__file__).resolve().parent.parent
SCRAPERS_DIR = ROOT / "src" / "scrapers"
sys.path.append(str(SCRAPERS_DIR))

from utils_files import (
    load_all_postliste_from_shards,
    merge_and_save_sharded_to_folder,
    load_changes_sharded,
    save_changes_sharded,
)

POSTLISTE_LEGACY = ROOT / "data" / "postliste_1.json"
CHANGES_LEGACY = ROOT / "data" / "changes.json"
SHARDS_DIR = ROOT / "data" / "shards"
CHANGES_DIR = ROOT / "data" / "changes"


def main():
    migrated_anything = False

    print("=== MIGRERING STARTER ===")
    print(f"Repo-root: {ROOT}")

    # ---------------------------------------------------------
    # 1. Migrer postliste_1.json → data/shards/
    # ---------------------------------------------------------
    if POSTLISTE_LEGACY.exists():
        print("[INFO] Leser legacy postliste_1.json...")
        docs = json.loads(POSTLISTE_LEGACY.read_text(encoding="utf-8"))
        print(f"[INFO] Fant {len(docs)} dokumenter i legacy postliste_1.json")

        existing_dict, _ = load_all_postliste_from_shards(str(SHARDS_DIR))
        print(f"[INFO] Eksisterende shards inneholder {len(existing_dict)} dokumenter")

        merge_and_save_sharded_to_folder(
            existing_dict,
            docs,
            folder=str(SHARDS_DIR),
        )

        print("[INFO] Migrerte postliste_1.json inn i shards")
        migrated_anything = True
    else:
        print("[INFO] Ingen legacy postliste_1.json funnet.")

    # ---------------------------------------------------------
    # 2. Migrer changes.json → data/changes/changes_*.json
    # ---------------------------------------------------------
    if CHANGES_LEGACY.exists():
        print("[INFO] Leser legacy changes.json...")
        changes = json.loads(CHANGES_LEGACY.read_text(encoding="utf-8"))
        print(f"[INFO] Fant {len(changes)} endringer i legacy changes.json")

        existing_changes = load_changes_sharded(str(CHANGES_DIR))
        print(f"[INFO] Eksisterende changes-shards inneholder {len(existing_changes)} endringer")

        merged = existing_changes + changes

        save_changes_sharded(merged, folder=str(CHANGES_DIR))

        print("[INFO] Migrerte changes.json inn i changes-shards")
        migrated_anything = True
    else:
        print("[INFO] Ingen legacy changes.json funnet.")

    # ---------------------------------------------------------
    # 3. Sjekk om migrering faktisk skjedde
    # ---------------------------------------------------------
    if not migrated_anything:
        print("[ERROR] Ingen legacy-filer ble migrert. Avbryter.")
        sys.exit(1)

    print("=== MIGRERING FULLFØRT ===")
    sys.exit(0)


if __name__ == "__main__":
    main()
