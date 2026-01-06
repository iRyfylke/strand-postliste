from playwright.sync_api import sync_playwright
import argparse
from datetime import datetime
from utils_dates import parse_date_from_page, within_range, parse_cli_date
from utils_files import (
    ensure_directories,
    load_config,
    load_existing,
    merge_and_save,
    atomic_write,
)
from scraper_core import hent_side

DEFAULT_CONFIG_FILE = "../config/config.json"
DATA_FILE = "../../data/postliste.json"
FILTERED_FILE = "../../data/postliste_filtered.json"


def run_scrape(start_date=None, end_date=None, config_path=DEFAULT_CONFIG_FILE, mode="publish"):
    print(f"[INFO] Starter scraper_dates i modus='{mode}'…")

    ensure_directories()
    cfg = load_config(config_path)

    start_page = int(cfg.get("start_page", 1))
    max_pages = int(cfg.get("max_pages", 100))
    per_page = int(cfg.get("per_page", 100))

    # Riktig siderekkefølge avhengig av config
    step = 1 if max_pages > start_page else -1

    print("[INFO] Konfigurasjon:")
    print(f"       start_page = {start_page}")
    print(f"       max_pages  = {max_pages}")
    print(f"       step       = {step}")
    print(f"       per_page   = {per_page}")
    print(f"       start_date = {start_date}")
    print(f"       end_date   = {end_date}")

    all_docs = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])

        for page_num in range(start_page, max_pages + step, step):
            docs = hent_side(page_num, browser, per_page)

            if docs is None:
                # Side feilet etter retries – hopp over, ikke stopp hele scrapen
                print(f"[WARN] Hopper over side {page_num} pga. feil.")
                continue

            # Filtrer dokumenter innenfor dato-range
            for d in docs:
                parsed_date = parse_date_from_page(d.get("dato"))
                if within_range(parsed_date, start_date, end_date):
                    all_docs.append(d)

            # Tidlig stopp hvis ALLE datoer på siden er eldre enn start_date
            parsed_dates = [parse_date_from_page(x.get("dato")) for x in docs if x.get("dato")]

            if start_date and parsed_dates:
                if all(x and x < start_date for x in parsed_dates):
                    print("[INFO] Tidlig stopp: alle datoer på denne siden er eldre enn start_date")
                    break

        browser.close()

    print(f"[INFO] Totalt hentet {len(all_docs)} dokumenter innenfor dato-range.")

    atomic_write(FILTERED_FILE, all_docs)
    print(f"[INFO] Lagret filtrerte resultater til {FILTERED_FILE}")

    if mode == "publish":
        existing = load_existing(DATA_FILE)
        merge_and_save(existing, all_docs, DATA_FILE)
        print(f"[INFO] Oppdatert hoveddatasett i {DATA_FILE}")
    else:
        print("[INFO] FULL-modus: Oppdaterer ikke postliste.json")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=DEFAULT_CONFIG_FILE)
    parser.add_argument("--mode", default="publish", choices=["full", "publish"])
    parser.add_argument("start_date", nargs="?")
    parser.add_argument("end_date", nargs="?")

    args = parser.parse_args()

    start_date = parse_cli_date(args.start_date) if args.start_date else None
    end_date = parse_cli_date(args.end_date) if args.end_date else start_date

    run_scrape(
        start_date=start_date,
        end_date=end_date,
        config_path=args.config,
        mode=args.mode,
    )


if __name__ == "__main__":
    main()
