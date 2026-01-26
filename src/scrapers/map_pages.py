#!/usr/bin/env python3
import asyncio
import json
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright
from scraper_core_async import hent_side_async

OUTPUT_FILE = Path("../../data/page_year_map.json")
MAX_PAGES = 3600  # litt høyere enn dagens 3536 for sikkerhet
CONCURRENCY = 6   # justerbar

def extract_years(docs):
    years = set()
    for d in docs:
        dato = d.get("dato") or d.get("dato_iso")
        if not dato:
            continue
        try:
            if "-" in dato:
                dt = datetime.fromisoformat(dato)
            else:
                dt = datetime.strptime(dato, "%d.%m.%Y")
            years.add(dt.year)
        except:
            pass
    return sorted(list(years))


async def scrape_page(context, page_num, semaphore):
    async with semaphore:
        page = await context.new_page()
        try:
            docs = await hent_side_async(
                page_num=page_num,
                page=page,
                per_page=100,
                timeout=20_000,
                retries=3,
            )
        finally:
            await page.close()

        if not docs:
            return page_num, []

        years = extract_years(docs)
        return page_num, years


async def main():
    print("[INFO] Starter mapping av alle sider…")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
        )
        context = await browser.new_context()

        async def block_resources(route):
            if route.request.resource_type in ["image", "media"]:
                await route.abort()
            else:
                await route.continue_()

        await context.route("**/*", block_resources)

        semaphore = asyncio.Semaphore(CONCURRENCY)

        tasks = []
        for page_num in range(1, MAX_PAGES + 1):
            tasks.append(scrape_page(context, page_num, semaphore))

        results = await asyncio.gather(*tasks)

        await context.close()
        await browser.close()

    page_map = {str(page): years for page, years in results if years}

    print(f"[INFO] Fant {len(page_map)} sider med dokumenter.")
    OUTPUT_FILE.write_text(json.dumps(page_map, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[INFO] Lagret kart i {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
