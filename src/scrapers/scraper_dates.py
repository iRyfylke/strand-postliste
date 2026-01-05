from playwright.sync_api import sync_playwright
import argparse

from datetime import datetime, date

from utils_dates import (
    parse_cli_date,
    parse_date_from_page,
    within_range,
)
from utils_files import (
    ensure_directories,
    load_config,
    load_existing,
    merge_and_save,
    atomic_write,
)
from scraper_core import hent_side  # hent_side(page_num, browser, per_page)

DEFAULT_CONFIG_FILE = "../config/config.json"
DATA_FILE = "../../data/postliste.json"
FILTERED_FILE = "../../data/postliste_filtered.json"


def run_scrape(start_date=None, end_date=None, config_path=DEFAULT_CONFIG_FILE, mode="publish"):
    print(f"[INFO] Starter scraper_dates i modus='{mode}'…")

    if mode not in ("full", "publish"):
        raise ValueError(f"Ugyldig mode: {mode}. Må være 'full' eller 'publish'.")

    ensure_directories()
    cfg = load_config(config_path)

    start_page = int(cfg.get("start_page", 1))
    max_pages = int(cfg.get("max_pages", 100))
    per_page = int(cfg.get("per_page", 100))

    print(f"[INFO] start_page={start_page}, max_pages={max_pages}, per_page={per_page}")

    all_docs = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])

        for page_num in range(start_page, max_pages + 1):
            docs = hent_side(page_num, browser, per_page)

            if not docs:
                print(f"[INFO] Ingen dokumenter på side {page_num}. Stopper.")
                break

            # Filtrer på dato-range
            for d in docs:
                parsed_date = parse_date_from_page(d.get("dato"))
                if within_range(parsed_date, start_date, end_date):
                    all_docs.append(d)

            # Tidlig stopp dersom alle datoer på siden er eldre enn start_date
            parsed_dates = [parse_date_from_page(x.get("dato")) for x in docs if x.get("dato")]
            if start_date and parsed_dates and all(x and x < start_date for x in parsed_dates):
                print("[INFO] Tidlig stopp: alle datoer på denne siden er eldre enn start_date")
                break

        browser.close()

    print(f"[INFO] Totalt hentet {len(all_docs)} dokumenter innenfor dato-range.")

    # 1) Alltid lagre filtrerte resultater separat (for H1/H2 eller debugging)
    atomic_write(FILTERED_FILE, all_docs)
    print(f"[INFO] Lagret filtrerte resultater til {FILTERED_FILE}")

    # 2) Kun i publish-modus skal vi oppdatere hoveddatasettet
    if mode == "publish":
        existing = load_existing(DATA_FILE)
        merge_and_save(existing, all_docs, DATA_FILE)
        print(f"[INFO] Oppdatert hoveddatasett i {DATA_FILE}")
    else:
        print("[INFO] FULL-modus: Oppdaterer ikke postliste.json")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        default=DEFAULT_CONFIG_FILE,
        help="Sti til config-fil (default: ../config/config.json)",
    )
    parser.add_argument(
        "--mode",
        default="publish",
        choices=["full", "publish"],
        help="Kjøringsmodus: 'full' for historisk arkiv, 'publish' for å oppdatere postliste.json",
    )
    parser.add_argument("start_date", nargs="?")
    parser.add_argument("end_date", nargs="?")

    args = parser.parse_args()

    start_date = parse_cli_date(args.start_date) if args.start_date else None
    end_date = parse_cli_date(args.end_date) if args.end_date else None

    if start_date and not end_date:
        end_date = start_date

    run_scrape(
        start_date=start_date,
        end_date=end_date,
        config_path=args.config,
        mode=args.mode,
    )


if __name__ == "__main__":
    main()
