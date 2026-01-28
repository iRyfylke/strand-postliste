import json
from pathlib import Path
import sys

# Legg til src/scrapers i sys.path slik at utils_files kan importeres
ROOT = Path(__file__).resolve().parent.parent  # repo-root
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


def main():
    # --- 1. Migrer postliste_1.json inn i shards ---
    if POSTLISTE_LEGACY.exists():
        print("[INFO] Leser legacy postliste_1.json...")
        docs = json.loads(POSTLISTE_LEGACY.read_text(encoding="utf-8"))

        existing_dict, _ = load_all_postliste_from_shards(str(ROOT / "data" / "shards"))
        print(f"[INFO] Eksisterende shards inneholder {len(existing_dict)} dokumenter")

        print(f"[INFO] Legger til {len(docs)} dokumenter fra legacy postliste_1.json")
        merge_and_save_sharded_to_folder(
            existing_dict,
            docs,
            folder=str(ROOT / "data" / "shards"),
        )
    else:
        print("[INFO] Ingen legacy postliste_1.json funnet.")

    # --- 2. Migrer changes.json inn i changes-shards ---
    if CHANGES_LEGACY.exists():
        print("[INFO] Leser legacy changes.json...")
        changes = json.loads(CHANGES_LEGACY.read_text(encoding="utf-8"))
        print(f"[INFO] Legacy changes.json inneholder {len(changes)} endringer")

        existing_changes = load_changes_sharded(str(ROOT / "data" / "changes"))
        print(f"[INFO] Eksisterende changes-shards inneholder {len(existing_changes)} endringer")

        merged = existing_changes + changes
        print(f"[INFO] Skriver totalt {len(merged)} endringer til changes-shards...")
        save_changes_sharded(merged, folder=str(ROOT / "data" / "changes"))
    else:
        print("[INFO] Ingen legacy changes.json funnet.")

    print("[INFO] Migrering fullført.")


if __name__ == "__main__":
    main()
