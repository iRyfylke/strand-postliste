import argparse
import asyncio
import os
import json
from pathlib import Path
from playwright.async_api import async_playwright

from utils_dates import parse_date_from_page, within_range, parse_cli_date
from utils_files import (
    ensure_directories,
    atomic_write,
)

from scraper_core_async import hent_side_async

# Absolutte paths
ROOT = Path(__file__).resolve().parent.parent.parent
FILTERED_FILE = ROOT / "data/postliste_filtered.json"


# ---------------------------------------------------------
# LOAD ARCHIVE YEAR
# ---------------------------------------------------------
def load_archive_year(year):
    archive_dir = ROOT / "data/archive_new"
    archive_files = sorted(archive_dir.glob(f"postliste_{year}_*.json"))
    existing = {}

    print(f"[INFO] Leser archive-filer for år {year}…")

    for f in archive_files:
        try:
            docs = json.loads(f.read_text(encoding="utf-8"))
            for d in docs:
                dokid = d.get("dokumentID")
                if dokid:
                    existing[dokid] = d
        except Exception as e:
            print(f"[WARN] Klarte ikke å lese {f}: {e}")

    print(f"[INFO] Totalt {len(existing)} dokumenter funnet i archive for {year}")
    return existing


# ---------------------------------------------------------
# FAILED PAGES
# ---------------------------------------------------------
def load_failed_pages(year):
    path = ROOT / f"data/archive_new/failed_pages_{year}.json"
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_failed_pages(year, pages):
    path = ROOT / f"data/archive_new/failed_pages_{year}.json"
    atomic_write(path, sorted(list(set(pages))))


# ---------------------------------------------------------
# SCRAPE SINGLE PAGE
# ---------------------------------------------------------
async def scrape_single_page(context, page_num, per_page, start_date, end_date):
    print(f"[INFO] Scraper side {page_num}")

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
async def run_scrape_async(start_date=None, end_date=None, mode="publish"):
    print(f"[INFO] Starter ASYNC scraper_dates i modus='{mode}'…")

    ensure_directories()

    print("[INFO] Konfigurasjon:")
    print(f"       start_date  = {start_date}")
    print(f"       end_date    = {end_date}")

    all_docs = []

    year = start_date.year if start_date else None
    failed_pages = []

    if mode == "repair":
        failed_pages = load_failed_pages(year)
        print(f"[INFO] Repair-modus: Leser failed_pages_{year}.json → {failed_pages}")

    cpu_count = os.cpu_count() or 2
    CONCURRENCY = min(6, max(2, cpu_count - 1))  # beholdt for ev. videre bruk
    print(f"[INFO] CPU-kjerner: {cpu_count}, (CONCURRENCY={CONCURRENCY}, men kjører sekvensielt for fullscrape)")

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

        per_page = 100
        new_failed = []

        if mode == "repair":
            # Kjør kun på sidene som tidligere feilet
            for page_num in failed_pages:
                batch = await scrape_single_page(
                    context=context,
                    page_num=page_num,
                    per_page=per_page,
                    start_date=start_date,
                    end_date=end_date,
                )
                if batch is None:
                    new_failed.append(page_num)
                else:
                    all_docs.extend(batch)
        else:
            # FULLSCRAPE: start på side 1, stopp når vi har 2 tomme sider på rad (etter datofilter)
            page_num = 1
            empty_streak = 0

            while True:
                batch = await scrape_single_page(
                    context=context,
                    page_num=page_num,
                    per_page=per_page,
                    start_date=start_date,
                    end_date=end_date,
                )

                if batch is None:
                    # ekte feil → logg som failed page
                    new_failed.append(page_num)
                elif len(batch) == 0:
                    empty_streak += 1
                    print(f"[INFO] Tom side etter filtrering (streak={empty_streak})")
                else:
                    empty_streak = 0
                    all_docs.extend(batch)

                if empty_streak >= 2:
                    print("[INFO] To tomme sider på rad. Stopper fullscrape.")
                    break

                page_num += 1

        await context.close()
        await browser.close()

    print(f"[INFO] Totalt hentet {len(all_docs)} dokumenter innenfor dato-range.")

    # FAILED PAGES UPDATE
    if year is not None:
        save_failed_pages(year, new_failed)
        print(f"[INFO] Oppdatert failed_pages_{year}.json → {new_failed}")
    else:
        print("[WARN] year=None, hopper over lagring av failed_pages")

    # REPAIR MODE
    if mode == "repair":
        print("[INFO] Repair-modus aktivert. Leser archive…")

        existing_dict = load_archive_year(year)

        missing_docs = []
        for d in all_docs:
            dokid = d.get("dokumentID")
            if dokid and dokid not in existing_dict:
                missing_docs.append(d)

        missing_file = ROOT / f"data/archive_new/missing_{year}.json"
        atomic_write(missing_file, missing_docs)

        print("[INFO] Repair fullført.")
        return

    # NORMAL MODES (FULL)
    atomic_write(FILTERED_FILE, all_docs)
    print("[INFO] FULL-modus: Oppdaterer ikke hoveddatasettet")


def main():
    parser = argparse.ArgumentParser()
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
            mode=args.mode,
        )
    )


if __name__ == "__main__":
    main()
