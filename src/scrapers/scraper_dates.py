from playwright.sync_api import sync_playwright
from datetime import datetime
import argparse

from utils_dates import parse_cli_date, parse_date_from_page, within_range
from utils_files import ensure_directories, load_config, load_existing, merge_and_save
from scraper_core import hent_side

CONFIG_FILE = "../config/config.json"
DATA_FILE = "../../data/postliste.json"

parser = argparse.ArgumentParser()
parser.add_argument("--config", default=CONFIG_FILE)
parser.add_argument("start_date", nargs="?")
parser.add_argument("end_date", nargs="?")
args = parser.parse_args()

def main(start_date=None, end_date=None):
    print("[INFO] Starter scraper_dates…")

    ensure_directories()
    cfg = load_config(args.config)

    start_page = int(cfg.get("start_page", 1))
    max_pages = int(cfg.get("max_pages", 100))
    per_page = int(cfg.get("per_page", 100))

    print(f"[INFO] start_page={start_page}, max_pages={max_pages}, per_page={per_page}")

    all_docs = []
    existing = load_existing(DATA_FILE)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])

        for page_num in range(start_page, max_pages + 1):
            docs = hent_side(page_num, browser, per_page)
            if not docs:
                break

            for d in docs:
                pd = parse_date_from_page(d.get("dato"))
                if within_range(pd, start_date, end_date):
                    all_docs.append(d)

            parsed_dates = [parse_date_from_page(x.get("dato")) for x in docs if x.get("dato")]
            if start_date and parsed_dates and all(x and x < start_date for x in parsed_dates):
                print("[INFO] Tidlig stopp: alle datoer på siden er eldre enn start_date")
                break

        browser.close()

    print(f"[INFO] Totalt hentet {len(all_docs)} dokumenter innenfor dato-range.")
    merge_and_save(existing, all_docs, DATA_FILE)

if __name__ == "__main__":
    sd = args.start_date
    ed = args.end_date

    start_date = parse_cli_date(sd) if sd else None
    end_date = parse_cli_date(ed) if ed else None

    if start_date and not end_date:
        end_date = start_date

    main(start_date=start_date, end_date=end_date)
