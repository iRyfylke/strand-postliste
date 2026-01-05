from playwright.sync_api import sync_playwright
from datetime import datetime, date

from utils_files import (
    ensure_directories,
    load_config,
    load_existing,
    load_changes,
    atomic_write,
    save_changes
)

from scraper_core_incremental import hent_side_incremental
from scraper_changes import detect_changes, build_change_entry

CONFIG_FILE = "src/config/config.json"
DATA_FILE = "data/postliste.json"
CHANGES_FILE = "data/changes.json"

def main():
    print("[INFO] Starter scraper…")

    ensure_directories()
    config = load_config()

    mode = config.get("mode", "incremental")
    max_pages = int(config.get(f"max_pages_{mode}", 50))

    print(f"[INFO] Modus: {mode}, max_pages: {max_pages}")

    existing = load_existing()
    updated = dict(existing)
    changes = load_changes()

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

            # Incremental stop
            if mode == "incremental":
                known = sum(1 for d in docs if d["dokumentID"] in existing)
                if known == len(docs):
                    print("[INFO] Incremental: alle dokumenter på denne siden er kjente. Stopper.")
                    break

        browser.close()

    # Merge og lagre
    latest_existing = load_existing()
    latest_existing.update(updated)

    def sort_key(x):
        try:
            return datetime.strptime(x.get("dato"), "%d.%m.%Y").date()
        except:
            return date.min

    data_list = sorted(latest_existing.values(), key=sort_key, reverse=True)
    atomic_write(DATA_FILE, data_list)
    save_changes(changes)

    print(f"[INFO] Lagret JSON med {len(data_list)} dokumenter")
    print(f"[INFO] Logget {len(changes)} endringshendelser i {CHANGES_FILE}")

if __name__ == "__main__":
    main()
