import asyncio
import random
from utils_playwright_async import safe_text, safe_goto
from utils_dates import parse_date_from_page, format_date

# ---------------------------------------------------------
# LEGACY-URL (KRITISK FOR FULL DOM / 100 PR SIDE)
# ---------------------------------------------------------
BASE_URL = (
    "https://www.strand.kommune.no/tjenester/politikk-innsyn-og-medvirkning/"
    "postliste-dokumenter-og-vedtak/sok-i-post-dokumenter-og-saker/#/"
    "?page={page}&pageSize={page_size}"
)


# ---------------------------------------------------------
# INTERNAL HELPERS
# ---------------------------------------------------------
async def _wait_for_content(page, page_num, timeout: int) -> bool:
    """Sørger for at innholdet er lastet nok til å hente artikler."""
    try:
        try:
            await page.wait_for_load_state("networkidle", timeout=timeout)
        except Exception as e:
            print(f"[WARN] Side {page_num}: networkidle feilet: {e}")

        # Liten ekstra pause for å være sikker på at alt er rendret
        await page.wait_for_timeout(300)

        try:
            await page.wait_for_selector(
                "article.bc-content-teaser--item",
                timeout=timeout,
                state="attached",
            )
            return True
        except Exception:
            print(f"[WARN] Side {page_num}: ingen artikler funnet (selector-timeout)")
            return False

    except Exception as e:
        print(f"[WARN] Side {page_num}: _wait_for_content feilet: {e}")
        return False


async def _is_truly_empty_page(page, page_num) -> bool:
    """Avgjør om siden faktisk er tom."""
    try:
        html = (await page.content() or "").lower()

        empty_markers = [
            "ingen dokumenter",
            "ingen treff",
            "ingen resultater",
            "ingen saker",
        ]

        if any(m in html for m in empty_markers):
            print(f"[INFO] Side {page_num}: tom side (ingen dokumenter).")
            return True

        artikler = await page.query_selector_all("article.bc-content-teaser--item")
        if len(artikler) == 0:
            print(f"[WARN] Side {page_num}: 0 artikler og ingen tom-side-tekst.")
            return False

        return False

    except Exception as e:
        print(f"[WARN] Side {page_num}: _is_truly_empty_page feilet: {e}")
        return False


async def _fetch_files_for_doc(context, detalj_link, dokid, timeout: int):
    """Henter filer fra detaljside i egen page."""
    filer = []

    if not detalj_link:
        return filer

    dp = await context.new_page()
    try:
        if await safe_goto(dp, detalj_link, retries=1, timeout=timeout):
            await dp.wait_for_timeout(150)

            links = await dp.query_selector_all("a")
            for fl in links:
                try:
                    href = await fl.get_attribute("href")
                    tekst = await fl.inner_text()
                except Exception:
                    continue

                if href and "/api/presentation/v2/nye-innsyn/filer" in href:
                    abs_url = href if href.startswith("http") else "https://www.strand.kommune.no" + href
                    filer.append({
                        "tekst": (tekst or "").strip(),
                        "url": abs_url,
                    })
    except Exception as e:
        print(f"[WARN] Klarte ikke hente filer for {dokid}: {e}")
    finally:
        try:
            await dp.close()
        except Exception:
            pass

    return filer


# ---------------------------------------------------------
# PUBLIC SCRAPER FUNCTION
# ---------------------------------------------------------
async def hent_side_async(page_num, page, per_page, retries=5, timeout=10_000):
    """
    DOM-basert async-scraper (legacy-visning):
      - Leser listevisning (100 artikler per side)
      - Går inn på detaljside i egen page
      - Henter filer
    """

    url = BASE_URL.format(page=page_num, page_size=per_page)

    for attempt in range(1, retries + 1):
        try:
            print(f"[INFO] Åpner side {page_num} (forsøk {attempt}/{retries}): {url}")

            if not await safe_goto(page, url, retries=1, timeout=timeout):
                raise RuntimeError("safe_goto feilet")

            if not await _wait_for_content(page, page_num, timeout):
                if await _is_truly_empty_page(page, page_num):
                    print(f"[INFO] Side {page_num} er tom. Returnerer [].")
                    return []
                raise RuntimeError("Innhold ikke lastet")

            artikler = await page.query_selector_all("article.bc-content-teaser--item")
            if not artikler:
                if await _is_truly_empty_page(page, page_num):
                    print(f"[INFO] Side {page_num} er tom. Returnerer [].")
                    return []
                raise RuntimeError("0 artikler funnet uten tom-side-indikasjon")

            print(f"[INFO] Side {page_num}: fant {len(artikler)} artikler i listevisning")

            docs = []
            context = page.context

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
                    if avsender else (f"Mottaker: {mottaker}" if mottaker else "")
                )

                detalj_link = ""
                try:
                    link_elem = await art.evaluate_handle("node => node.closest('a')")
                    if link_elem:
                        detalj_link = await link_elem.get_attribute("href")
                except Exception:
                    pass

                if detalj_link and not detalj_link.startswith("http"):
                    detalj_link = "https://www.strand.kommune.no" + detalj_link

                filer = await _fetch_files_for_doc(
                    context=context,
                    detalj_link=detalj_link,
                    dokid=dokid,
                    timeout=timeout,
                )

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

            print(f"[INFO] Fant {len(docs)} dokumenter på side {page_num}")
            return docs

        except Exception as e:
            print(f"[WARN] Feil ved lasting/parsing av side {page_num} (forsøk {attempt}/{retries}): {e}")

            delay = min((2 ** (attempt - 1)) + random.uniform(0, 0.5), 20.0)
            print(f"[INFO] Venter {delay:.2f}s før nytt forsøk…")
            await asyncio.sleep(delay)

    print(f"[ERROR] Side {page_num} feilet etter {retries} forsøk.")
    return None
