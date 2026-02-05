import argparse
import asyncio
import os
import glob
import json
from pathlib import Path
from playwright.async_api import async_playwright

from utils_dates import parse_date_from_page, within_range, parse_cli_date
from utils_files import (
    ensure_directories,
    load_config,
    merge_and_save_sharded,
    atomic_write,
)
from scraper_core_async import hent_side_async


# ---------------------------------------------------------
# PATHS
# ---------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_CONFIG_FILE = ROOT / "config/config.json"
FILTERED_FILE = ROOT / "data/postliste_filtered.json"
ARCHIVE_DIR = ROOT / "data/archive_new"


# ---------------------------------------------------------
# LOAD ARCHIVE YEAR
# ---------------------------------------------------------
def load_archive_year(year: int) -> dict:
    """Load all archive files for a given year into a dict keyed by dokumentID."""
    archive_files = glob.glob(str(ARCHIVE_DIR / f"postliste_{year}_*.json"))
    existing = {}

    print(f"[INFO] Leser archive-filer for år {year}…")

    for f in archive_files:
        try:
            with open(f, "r", encoding="utf-8") as infile:
                docs = json.load(infile)
                for d in docs:
                    dokid = d.get("dokumentID")
                    if dokid:
                        existing[dokid] = d
        except Exception as e:
            print(f"[WARN] Klarte ikke å lese {f}: {e}")

    print(f"[INFO] Totalt {len(existing)} dokumenter funnet i archive for {year}")
    return existing


# ---------------------------------------------------------
# FAILED PAGES – LOAD & SAVE
# ---------------------------------------------------------
def load_failed_pages(year: int) -> list:
    path = ARCHIVE_DIR / f"failed_pages_{year}.json"
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_failed_pages(year: int, pages: list):
    path = ARCHIVE_DIR / f"failed_pages_{year}.json"
    atomic_write(path, sorted(list(set(pages))))


# ---------------------------------------------------------
# SCRAPE SINGLE PAGE
# ---------------------------------------------------------
async def scrape_single_page(
    context,
    page_num: int,
    per_page: int,
    start_date,
    end_date,
    semaphore,
    index: int,
    total_pages: int,
):
    print(f"[INFO] Scraper side {index} av {total_pages} (page_num={page_num})")

    async with semaphore:
        page = await context.new_page()
        try:
            docs = await hent_side_async(
                page_num=page_num,
                page=page,
                per_page=per_page,
                timeout=20_000,
                retries=5,
            )
        finally:
            await page.close()

        if docs is None:
            print(f"[WARN] FEIL: Klarte ikke hente side {page_num} (docs=None)")
            return None

        if len(docs) == 0:
            print(f"[INFO] Side {page_num} er tom (0 dokumenter)")
            return []

        filtered = []
        for d in docs:
            parsed_date = parse_date_from_page(d.get("dato"))
            if within_range(parsed_date, start_date, end_date):
                filtered.append(d)

        print(f"[INFO] Side {page_num}: {len(filtered)} dokumenter innenfor dato-range")
        return filtered


# ---------------------------------------------------------
# MAIN SCRAPER
# ---------------------------------------------------------
async def run_scrape_async(start_date=None, end_date=None, config_path=DEFAULT_CONFIG_FILE, mode="publish"):
    print(f"[INFO] Starter ASYNC PARALLELL scraper_dates i modus='{mode}'…")

    ensure_directories()
    cfg = load_config(config_path)

    start_page = int(cfg.get("start_page", 1))
    max_pages = int(cfg.get("max_pages", 100))
    per_page = int(cfg.get("per_page", 100))
    step = 1 if max_pages >= start_page else -1

    page_list = list(range(start_page, max_pages + step, step))
    total_pages = len(page_list)

    print("[INFO] Konfigurasjon:")
    print(f"       start_page  = {start_page}")
    print(f"       max_pages   = {max_pages}")
    print(f"       step        = {step}")
    print(f"       total_pages = {total_pages}")
    print(f"       per_page    = {per_page}")
    print(f"       start_date  = {start_date}")
    print(f"       end_date    = {end_date}")

    all_docs = []
    year = start_date.year if start_date else None

    # Load failed pages for repair mode
    if mode == "repair":
        page_list = load_failed_pages(year)
        print(f"[INFO] Repair-modus: Leser failed_pages_{year}.json → {page_list}")

    cpu_count = os.cpu_count() or 2
    concurrency = min(6, max(2, cpu_count - 1))
    print(f"[INFO] CPU-kjerner: {cpu_count}, bruker CONCURRENCY={concurrency}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-background-networking",
                "--disable-background-timer-throttling",
                "--disable-renderer-backgrounding",
            ],
        )

        context = await browser.new_context()

        async def block_resources(route):
            if route.request.resource_type in ["image", "media"]:
                await route.abort()
            else:
                await route.continue_()

        await context.route("**/*", block_resources)

        semaphore = asyncio.Semaphore(concurrency)

        tasks = [
            scrape_single_page(
                context=context,
                page_num=page_num,
                per_page=per_page,
                start_date=start_date,
                end_date=end_date,
                semaphore=semaphore,
                index=idx,
                total_pages=total_pages,
            )
            for idx, page_num in enumerate(page_list, start=1)
        ]

        results = await asyncio.gather(*tasks)

        for batch in results:
            if batch:
                all_docs.extend(batch)

        await context.close()
        await browser.close()

    print(f"[INFO] Totalt hentet {len(all_docs)} dokumenter innenfor dato-range.")

    # Update failed pages
    new_failed = [
        page_num
        for page_num, batch in zip(page_list, results)
        if batch is None
    ]

    if year is not None:
        save_failed_pages(year, new_failed)
        print(f"[INFO] Oppdatert failed_pages_{year}.json → {new_failed}")

    # Repair mode: write missing docs
    if mode == "repair":
        print("[INFO] Repair-modus aktivert. Leser archive…")
        existing_dict = load_archive_year(year)

        missing_docs = [
            d for d in all_docs
            if d.get("dokumentID") and d["dokumentID"] not in existing_dict
        ]

        missing_file = ARCHIVE_DIR / f"missing_{year}.json"
        atomic_write(missing_file, missing_docs)

        print(f"[INFO] Repair fullført. Fant {len(missing_docs)} manglende dokumenter.")
        return

    # Normal modes
    atomic_write(FILTERED_FILE, all_docs)

    if mode == "publish":
        from utils_files import load_all_postliste
        existing_dict, _ = load_all_postliste()
        merge_and_save_sharded(existing_dict, all_docs)
        print("[INFO] Oppdatert shard-basert hoveddatasett.")
    else:
        print("[INFO] FULL-modus: Oppdaterer ikke hoveddatasettet")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_FILE))
    parser.add_argument("--mode", default="publish", choices=["full", "publish", "repair"])
    parser.add_argument("start_date", nargs="?")
    parser.add_argument("end_date", nargs="?")

    args = parser.parse_args()

    start_date = parse_cli_date(args.start_date) if args.start_date else None
    end_date = parse_cli_date(args.end_date) if args.end_date else start_date

    asyncio.run(
        run_scrape_async(
            start_date=start_date,
            end_date=end_date,
            config_path=args.config,
            mode=args.mode,
        )
    )


if __name__ == "__main__":
    main()
