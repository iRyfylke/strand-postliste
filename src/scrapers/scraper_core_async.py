from utils_dates import parse_date_from_page, within_range
from utils_playwright_async import safe_text, safe_goto
from utils_dates import format_date

BASE_URL = (
    "https://www.strand.kommune.no/tjenester/politikk-innsyn-og-medvirkning/"
    "postliste-dokumenter-og-vedtak/sok-i-post-dokumenter-og-saker/#/"
    "?page={page}&pageSize={page_size}"
)


async def hent_side_async(page_num, page, per_page, retries=5, timeout=10_000):
    """
    Henter en side med dokumenter (async).
    Returnerer liste med dokumenter eller None ved feil.
    """
    url = BASE_URL.format(page=page_num, page_size=per_page)

    for attempt in range(1, retries + 1):
        try:
            print(f"[INFO] (async) Åpner side {page_num} (forsøk {attempt}/{retries}): {url}")

            ok = await safe_goto(page, url, retries=1, timeout=timeout)
            if not ok:
                raise RuntimeError("safe_goto feilet")

            await page.wait_for_timeout(150)

            await page.wait_for_selector(
                "article.bc-content-teaser--item",
                timeout=timeout,
                state="attached",
            )

            artikler = await page.query_selector_all("article.bc-content-teaser--item")
            if not artikler:
                raise RuntimeError("0 artikler funnet")

            docs = []

            for art in artikler:
                dokid = await safe_text(art, ".bc-content-teaser-meta-property--dokumentID dd")
                if not dokid:
                    continue

                tittel = await safe_text(art, ".bc-content-teaser-title-text")
                dato_raw = await safe_text(art, ".bc-content-teaser-meta-property--dato dd")
                parsed = parse_date_from_page(dato_raw)

                doktype = await safe_text(art, ".SakListItem_sakListItemTypeText__16759c")
                avsender = await safe_text(art, ".bc-content-teaser-meta-property--avsender dd")
                mottaker = await safe_text(art, ".bc-content-teaser-meta-property--mottaker dd")

                am = (
                    f"Avsender: {avsender}"
                    if avsender
                    else (f"Mottaker: {mottaker}" if mottaker else "")
                )

                detalj_link = ""
                try:
                    link_elem = await art.evaluate_handle("node => node.closest('a')")
                    if link_elem:
                        detalj_link = await link_elem.get_attribute("href")
                except Exception:
                    detalj_link = ""

                if detalj_link and not detalj_link.startswith("http"):
                    detalj_link = "https://www.strand.kommune.no" + detalj_link

                filer = []
                if detalj_link:
                    try:
                        ok = await safe_goto(page, detalj_link, retries=1, timeout=timeout)
                        if ok:
                            await page.wait_for_timeout(120)

                            links = await page.query_selector_all("a")
                            for fl in links:
                                href = await fl.get_attribute("href")
                                tekst = await fl.inner_text()

                                if href and "/api/presentation/v2/nye-innsyn/filer" in href:
                                    abs_url = href if href.startswith("http") else "https://www.strand.kommune.no" + href
                                    filer.append({
                                        "tekst": (tekst or "").strip(),
                                        "url": abs_url
                                    })

                    except Exception as e:
                        print(f"[WARN] (async) Klarte ikke hente filer for {dokid}: {e}")

                    finally:
                        await safe_goto(page, url, retries=1, timeout=timeout)
                        await page.wait_for_timeout(80)

                status = "Publisert" if filer else "Må bes om innsyn"

                docs.append({
                    "tittel": tittel,
                    "dato": format_date(parsed),
                    "dato_iso": parsed.isoformat() if parsed else None,
                    "dokumentID": dokid,
                    "dokumenttype": doktype,
                    "avsender_mottaker": am,
                    "journal_link": detalj_link,
                    "filer": filer,
                    "status": status,
                })

            return docs

        except Exception as e:
            print(f"[WARN] (async) Feil ved lasting/parsing av side {page_num}: {e}")
            await asyncio.sleep(1)

    print(f"[ERROR] (async) Side {page_num} feilet etter {retries} forsøk.")
    return None


async def scrape_page_with_filter(
    page,
    page_num,
    per_page,
    start_date,
    end_date,
    semaphore,
    index,
    total_pages,
    timeout=20000,
):
    """
    Wrapper rundt hent_side_async() som:
      - henter en side
      - filtrerer dokumenter på dato
      - returnerer enten liste eller {"failed": page_num}
    """

    print(f"[INFO] Scraper side {index} av {total_pages} (page_num={page_num})")

    async with semaphore:
        docs = await hent_side_async(
            page_num=page_num,
            page=page,
            per_page=per_page,
            timeout=timeout,
            retries=5,
        )

        if not docs:
            return {"failed": page_num}

        filtered = []
        for d in docs:
            parsed_date = parse_date_from_page(d.get("dato"))
            if within_range(parsed_date, start_date, end_date):
                filtered.append(d)

        return filtered
