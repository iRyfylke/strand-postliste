import argparse
import asyncio
from utils_dates import parse_cli_date
from utils_files import (
    ensure_directories,
    load_config,
    merge_and_save_sharded,
    atomic_write,
    load_archive_year,
    append_missing,
    save_failed_pages,
    find_missing_docs,
)
from utils_concurrency import compute_concurrency
from utils_playwright_setup import create_playwright_context
from scraper_core_async import scrape_page_with_filter

DEFAULT_CONFIG_FILE = "../config/config.json"
FILTERED_FILE = "../../data/postliste_filtered.json"


async def run_scrape_async(
    start_date=None,
    end_date=None,
    config_path=DEFAULT_CONFIG_FILE,
    mode="publish",
):
    print(f"[INFO] Starter ASYNC PARALLELL scraper_dates i modus='{mode}'…")

    ensure_directories()
    cfg = load_config(config_path)

    start_page = int(cfg.get("start_page", 1))
    max_pages = int(cfg.get("max_pages", 100))
    per_page = int(cfg.get("per_page", 100))
    step = 1 if max_pages > start_page else -1
    total_pages = abs(max_pages - start_page) + 1

    print("[INFO] Konfigurasjon:")
    print(f"       start_page  = {start_page}")
    print(f"       max_pages   = {max_pages}")
    print(f"       step        = {step}")
    print(f"       total_pages = {total_pages}")
    print(f"       per_page    = {per_page}")
    print(f"       start_date  = {start_date}")
    print(f"       end_date    = {end_date}")

    # ---------------------------------------------------------
    # SETUP: concurrency + Playwright
    # ---------------------------------------------------------
    CONCURRENCY = compute_concurrency()
    print(f"[INFO] Bruker CONCURRENCY={CONCURRENCY}")

    p, browser, context = await create_playwright_context()
    semaphore = asyncio.Semaphore(CONCURRENCY)

    # ---------------------------------------------------------
    # SCRAPE ALL PAGES
    # ---------------------------------------------------------
    async def task_for_page(page_num, idx):
        page = await context.new_page()
        try:
            return await scrape_page_with_filter(
                page=page,
                page_num=page_num,
                per_page=per_page,
                start_date=start_date,
                end_date=end_date,
                semaphore=semaphore,
                index=idx,
                total_pages=total_pages,
            )
        finally:
            await page.close()

    tasks = [
        task_for_page(page_num, idx)
        for idx, page_num in enumerate(
            range(start_page, max_pages + step, step),
            start=1,
        )
    ]

    results = await asyncio.gather(*tasks)

    await context.close()
    await browser.close()
    await p.stop()

    # ---------------------------------------------------------
    # COLLECT RESULTS
    # ---------------------------------------------------------
    all_docs = []
    failed_pages = []

    for batch in results:
        if isinstance(batch, dict) and "failed" in batch:
            failed_pages.append(batch["failed"])
        elif isinstance(batch, list):
            all_docs.extend(batch)

    print(f"[INFO] Totalt hentet {len(all_docs)} dokumenter innenfor dato-range.")
    print(f"[INFO] Antall feilede sider: {len(failed_pages)}")

    # ---------------------------------------------------------
    # REPAIR MODE
    # ---------------------------------------------------------
    if mode == "repair":
        print("[INFO] Repair-modus aktivert. Leser archive…")

        year = start_date.year if start_date else "unknown"

        archive_dict = load_archive_year(year)
        missing_docs = find_missing_docs(all_docs, archive_dict)

        print(f"[INFO] Fant {len(missing_docs)} nye manglende dokumenter.")

        append_missing(year, missing_docs)
        save_failed_pages(year, failed_pages)

        print("[INFO] Repair fullført.")
        return

    # ---------------------------------------------------------
    # NORMAL MODES
    # ---------------------------------------------------------
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
    parser.add_argument("--config", default=DEFAULT_CONFIG_FILE)
    parser.add_argument(
        "--mode",
        default="publish",
        choices=["full", "publish", "repair"],
    )
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
