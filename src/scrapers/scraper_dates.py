import argparse
import asyncio
import os
import json
from pathlib import Path
from playwright.async_api import async_playwright

from utils_dates import parse_date_from_page, within_range, parse_cli_date
from utils_files import ensure_directories, atomic_write
from scraper_core_async import hent_side_async

ROOT = Path(__file__).resolve().parent.parent.parent
FILTERED_FILE = ROOT / "data/postliste_filtered.json"


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
    print(f"[INFO] CPU-kjerner: {cpu_count} (kjører sekvensielt for fullscrape)")

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

        page = await context.new_page()

        if mode == "repair":
            for page_num in failed_pages:
                print(f"[INFO] Repair: scraper side {page_num}")
                batch = await hent_side_async(
                    page_num=page_num,
                    page=page,
                    per_page=per_page,
                    retries=5,
                    timeout=20_000,
                )

                if batch is None:
                    new_failed.append(page_num)
                    continue

                for d in batch:
                    parsed = parse_date_from_page(d.get("dato"))
                    if within_range(parsed, start_date, end_date):
                        all_docs.append(d)
        else:
            page_num = 1
            empty_streak = 0
            older_streak = 0

            while True:
                print(f"[INFO] Fullscrape: scraper side {page_num}")
                batch = await hent_side_async(
                    page_num=page_num,
                    page=page,
                    per_page=per_page,
                    retries=5,
                    timeout=20_000,
                )

                if batch is None:
                    new_failed.append(page_num)
                    page_num += 1
                    continue

                if len(batch) == 0:
                    empty_streak += 1
                    print(f"[INFO] Tom side (len=0). empty_streak={empty_streak}")
                else:
                    empty_streak = 0

                in_range = []
                all_older_than_start = True

                for d in batch:
                    parsed = parse_date_from_page(d.get("dato"))
                    if parsed is None:
                        all_older_than_start = False
                        continue

                    if parsed >= start_date:
                        all_older_than_start = False

                    if within_range(parsed, start_date, end_date):
                        in_range.append(d)

                print(f"[INFO] Side {page_num}: {len(in_range)} dokumenter innenfor dato-range")

                if in_range:
                    all_docs.extend(in_range)

                if all_older_than_start:
                    older_streak += 1
                    print(f"[INFO] Alle dokumenter på side {page_num} er eldre enn start_date. older_streak={older_streak}")
                else:
                    older_streak = 0

                if empty_streak >= 2:
                    print("[INFO] To tomme sider på rad. Stopper fullscrape.")
                    break

                if older_streak >= 2:
                    print("[INFO] To sider på rad kun med dokumenter eldre enn start_date. Stopper fullscrape.")
                    break

                page_num += 1

        await page.close()
        await context.close()
        await browser.close()

    print(f"[INFO] Totalt hentet {len(all_docs)} dokumenter innenfor dato-range.")

    if year is not None:
        save_failed_pages(year, new_failed)
        print(f"[INFO] Oppdatert failed_pages_{year}.json → {new_failed}")
    else:
        print("[WARN] year=None, hopper over lagring av failed_pages")

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
