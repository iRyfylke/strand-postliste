from playwright.sync_api import sync_playwright
from datetime import datetime, date

from utils_files import (
    ensure_directories,
    load_config,
    load_all_postliste_from_shards,
    load_changes_sharded,
    save_changes_sharded,
    merge_and_save_sharded_to_folder,
)

from scraper_core_incremental import hent_side_incremental
from scraper_changes import detect_changes, build_change_entry

CONFIG_FILE = "../config/config.json"


def main():
    print("[INFO] Starter incremental scraper…")

    ensure_directories()
    config = load_config(CONFIG_FILE)

    mode = config.get("mode", "incremental")
    max_pages = int(config.get(f"max_pages_{mode}", 50))

    print(f"[INFO] Modus: {mode}, max_pages: {max_pages}")

    # Last ALLE shards fra data/shards/
    existing_dict, _all_existing_list = load_all_postliste_from_shards()
    updated = dict(existing_dict)

    # Last changes fra data/changes/
    changes = load_changes_sharded()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])

        for page_num in range(1, max_pages + 1):
            docs = hent_side_incremental(page_num, browser)

            if not docs:
                print(f"[INFO] Ingen dokumenter på side {page_num}. Stopper.")
                break

            print(f"[INFO] Behandler {len(docs)} dokumenter fra side {page_num}")

            for d in docs:
                doc_id = d["dokumentID"]
                is_new, change_dict = detect_changes(updated, d)

                if is_new:
                    print(f"[NEW] {doc_id} – {d['tittel']}")
                    changes.append(build_change_entry(doc_id, d["tittel"], change_dict, "NEW"))

                elif change_dict:
                    print(f"[UPDATE] {doc_id} – {', '.join(change_dict.keys())}")
                    changes.append(build_change_entry(doc_id, d["tittel"], change_dict, "UPDATE"))

                updated[doc_id] = d

            # Incremental stop condition
            known = sum(1 for d in docs if d["dokumentID"] in existing_dict)
            if known == len(docs):
                print("[INFO] Incremental: alle dokumenter på denne siden er kjente. Stopper.")
                break

        browser.close()

    # Lagre shards i data/shards/
    merge_and_save_sharded_to_folder(existing_dict, list(updated.values()), folder="data/shards")

    # Lagre changes i data/changes/
    save_changes_sharded(changes, folder="data/changes")

    print(f"[INFO] Incremental scraper ferdig.")


if __name__ == "__main__":
    main()
