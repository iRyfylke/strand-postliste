import asyncio
import random
from utils_playwright_async import safe_text, safe_goto
from utils_dates import parse_date_from_page, format_date

BASE_URL = (
    "https://www.strand.kommune.no/tjenester/politikk-innsyn-og-medvirkning/"
    "postliste-dokumenter-og-vedtak/sok-i-post-dokumenter-og-saker/#/"
    "?page={page}&pageSize={page_size}"
)


async def _wait_for_content(page, page_num, timeout: int) -> bool:
    try:
        try:
            await page.wait_for_load_state("networkidle", timeout=timeout)
        except Exception as e:
            print(f"[WARN] Side {page_num}: wait_for_load_state('networkidle') feilet: {e}")

        await page.wait_for_timeout(400)

        try:
            await page.evaluate("window.scrollBy(0, 200)")
            await page.wait_for_timeout(300)
        except Exception as e:
            print(f"[WARN] Side {page_num}: scroll-nudge feilet: {e}")

        try:
            await page.wait_for_selector(
                "article.bc-content-teaser--item",
                timeout=timeout,
                state="attached",
            )
        except Exception as e:
            print(f"[WARN] Ingen artikler funnet på side {page_num} (selector-timeout): {e}")
            return False

        return True

    except Exception as e:
        print(f"[WARN] Side {page_num}: _wait_for_content feilet: {e}")
        return False


async def _is_truly_empty_page(page, page_num) -> bool:
    try:
        container = await page.query_selector("main, .bc-content, body")
        if not container:
            return False

        html = await page.content()
        text = (html or "").lower()

        markers = [
            "ingen dokumenter",
            "ingen treff",
            "ingen resultater",
            "ingen saker",
        ]

        if any(m in text for m in markers):
            print(f"[INFO] Side {page_num}: side ser ut til å være tom (ingen dokumenter).")
            return True

        artikler = await page.query_selector_all("article.bc-content-teaser--item")
        if len(artikler) == 0:
            print(f"[WARN] Side {page_num}: 0 artikler og ingen tydelig 'ingen dokumenter'-tekst.")
            return False

        return False

    except Exception as e:
        print(f"[WARN] Side {page_num}: _is_truly_empty_page feilet: {e}")
        return False


async def hent_side_async(page_num, page, per_page, retries=5, timeout=10_000):
    """
    DOM-basert scraper:
      - Leser listevisning
      - Går inn på detaljside
      - Henter filer
    """

    url = BASE_URL.format(page=page_num, page_size=per_page)

    for attempt in range(1, retries + 1):
        try:
            print(f"[INFO] (async) Åpner side {page_num} (forsøk {attempt}/{retries}): {url}")

            ok = await safe_goto(page, url, retries=1, timeout=timeout)
            if not ok:
                raise RuntimeError("safe_goto feilet")

            loaded = await _wait_for_content(page, page_num, timeout=timeout)
            if not loaded:
                if await _is_truly_empty_page(page, page_num):
                    print(f"[INFO] (async) Side {page_num} er tom, men gyldig. Returnerer tom liste.")
                    return []
                raise RuntimeError("Innhold ikke lastet / ingen artikler tilgjengelig")

            artikler = await page.query_selector_all("article.bc-content-teaser--item")
            antall = len(artikler)
            print(f"[INFO] (async) Fant {antall} dokumenter på side {page_num}")

            if antall == 0:
                if await _is_truly_empty_page(page, page_num):
                    print(f"[INFO] (async) Side {page_num} er tom, men gyldig (etter artikler-sjekk).")
                    return []
                raise RuntimeError("0 artikler funnet uten klar indikasjon på tom side")

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
            print(f"[WARN] (async) Feil ved lasting/parsing av side {page_num} (forsøk {attempt}/{retries}): {e}")

            base_delay = 1.0 * (2 ** (attempt - 1))
            jitter = random.uniform(0, 0.5 * base_delay)
            delay = min(base_delay + jitter, 20.0)

            print(f"[INFO] (async) Venter {delay:.2f}s før nytt forsøk på side {page_num}…")
            await asyncio.sleep(delay)

    print(f"[ERROR] (async) Side {page_num} feilet etter {retries} forsøk.")
    return None
