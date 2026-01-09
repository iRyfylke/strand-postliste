import asyncio
from utils_playwright import safe_text
from utils_dates import parse_date_from_page, format_date

BASE_URL = (
    "https://www.strand.kommune.no/tjenester/politikk-innsyn-og-medvirkning/"
    "postliste-dokumenter-og-vedtak/sok-i-post-dokumenter-og-saker/#/"
    "?page={page}&pageSize={page_size}"
)


async def hent_side_async(page_num, page, per_page, retries=5, timeout=10_000):
    """
    Asynkron, optimalisert versjon av hent_side():
      - Gjenbruker page-instans
      - Navigerer async
      - Blokkerer unødvendige ressurser (gjøres i context)
      - Raskere detaljvisning
      - Mindre memory leaks
      - Bedre retry-logikk
    """

    url = BASE_URL.format(page=page_num, page_size=per_page)

    for attempt in range(1, retries + 1):
        try:
            print(f"[INFO] (async) Åpner side {page_num} (forsøk {attempt}/{retries}): {url}")

            # Naviger til siden
            await page.goto(url, timeout=timeout, wait_until="domcontentloaded")

            # Kort pause for rendering
            await page.wait_for_timeout(200)

            # Vent på artikler
            try:
                await page.wait_for_selector("article.bc-content-teaser--item", timeout=timeout)
            except Exception as e:
                print(f"[WARN] Ingen artikler funnet på side {page_num}: {e}")
                raise

            artikler = await page.query_selector_all("article.bc-content-teaser--item")
            antall = len(artikler)
            print(f"[INFO] (async) Fant {antall} dokumenter på side {page_num}")

            if antall == 0:
                raise RuntimeError("0 artikler funnet")

            docs = []

            # Hent dokumenter
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

                # Hent detalj-link
                detalj_link = ""
                try:
                    link_elem = await art.evaluate_handle("node => node.closest('a')")
                    detalj_link = await link_elem.get_attribute("href") if link_elem else ""
                except Exception:
                    pass

                if detalj_link and not detalj_link.startswith("http"):
                    detalj_link = "https://www.strand.kommune.no" + detalj_link

                # Hent filer (async, raskere)
                filer = []
                if detalj_link:
                    try:
                        await page.goto(detalj_link, timeout=timeout, wait_until="domcontentloaded")
                        await page.wait_for_timeout(150)

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
                        # Gå tilbake til hovedsiden
                        await page.goto(url, timeout=timeout, wait_until="domcontentloaded")
                        await page.wait_for_timeout(100)

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
            print(f"[WARN] (async) Feil ved lasting/parsing av side {page_num} (forsøk {attempt}/{retries}): {e}")
            await asyncio.sleep(1)

    print(f"[ERROR] (async) Side {page_num} feilet etter {retries} forsøk.")
    return None
