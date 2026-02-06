import asyncio
import random
from utils_playwright_async import safe_text, safe_goto
from utils_dates import parse_date_from_page, format_date

# ---------------------------------------------------------
# KORRIGERT URL (kritisk!)
# ---------------------------------------------------------
BASE_URL = (
    "https://www.strand.kommune.no/tjenester/politikk-innsyn-og-medvirkning/"
    "postliste-dokumenter-og-vedtak/sok-i-post-dokumenter-og-saker/"
    "?page={page}&pageSize={page_size}"
)


# ---------------------------------------------------------
# INTERNAL HELPERS
# ---------------------------------------------------------
async def _wait_for_initial_content(page, page_num, timeout: int) -> bool:
    """Sørger for at første batch med innhold er lastet."""
    try:
        try:
            await page.wait_for_load_state("networkidle", timeout=timeout)
        except Exception as e:
            print(f"[WARN] Side {page_num}: networkidle feilet: {e}")

        # Liten ekstra pause for SPA-hydrering
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
        print(f"[WARN] Side {page_num}: _wait_for_initial_content feilet: {e}")
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


async def _scroll_and_collect_list_docs(page, page_num, per_page, timeout: int):
    """
    Håndterer virtualisert liste:
    - scroller gjennom siden
    - leser artikler ved hver scroll
    - lagrer dokumenter keyed på dokumentID (for å unngå duplikater)
    """
    seen_ids = set()
    docs = []

    max_scrolls = 30
    last_seen_count = 0

    for i in range(max_scrolls):
        # Liten pause for å la DOM oppdatere seg
        await page.wait_for_timeout(200)

        artikler = await page.query_selector_all("article.bc-content-teaser--item")

        if i == 0 and not artikler:
            # Første forsøk, ingen artikler – la caller håndtere tom side
            break

        for art in artikler:
            dokid = await safe_text(art, ".bc-content-teaser-meta-property--dokumentID dd")
            if not dokid or dokid in seen_ids:
                continue

            seen_ids.add(dokid)

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

            docs.append({
                "tittel": tittel,
                "dato": format_date(parsed),
                "dato_iso": parsed.isoformat() if parsed else None,
                "dokumentID": dokid,
                "dokumenttype": doktype,
                "avsender_mottaker": am,
                "journal_link": detalj_link,
                # filer/status fylles inn senere
            })

        # Hvis vi har nådd per_page (typisk 100), er vi ferdige
        if len(seen_ids) >= per_page:
            break

        # Hvis ingen nye dokumenter siden forrige runde, anta at vi er ferdige
        if len(seen_ids) == last_seen_count:
            # En ekstra scroll helt til bunn for sikkerhets skyld
            try:
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(300)
            except Exception as e:
                print(f"[WARN] Side {page_num}: scrollTo bottom feilet: {e}")
            # Sjekk én gang til
            artikler = await page.query_selector_all("article.bc-content-teaser--item")
            new_ids = set()
            for art in artikler:
                dokid = await safe_text(art, ".bc-content-teaser-meta-property--dokumentID dd")
                if dokid and dokid not in seen_ids:
                    new_ids.add(dokid)
            if not new_ids:
                break

        last_seen_count = len(seen_ids)

        # Scroll videre nedover
        try:
            await page.evaluate("window.scrollBy(0, window.innerHeight * 0.9)")
        except Exception as e:
            print(f"[WARN] Side {page_num}: scrollBy feilet: {e}")
            break

    print(f"[INFO] Side {page_num}: samlet {len(docs)} dokumenter fra listevisning")
    return docs


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
    DOM-basert async-scraper:
      - Leser listevisning (virtualisert)
      - Scroller og samler ALLE dokumenter (via dokumentID)
      - Går inn på detaljside i egen page
      - Henter filer
    """

    url = BASE_URL.format(page=page_num, page_size=per_page)

    for attempt in range(1, retries + 1):
        try:
            print(f"[INFO] Åpner side {page_num} (forsøk {attempt}/{retries}): {url}")

            if not await safe_goto(page, url, retries=1, timeout=timeout):
                raise RuntimeError("safe_goto feilet")

            if not await _wait_for_initial_content(page, page_num, timeout):
                if await _is_truly_empty_page(page, page_num):
                    print(f"[INFO] Side {page_num} er tom. Returnerer [].")
                    return []
                raise RuntimeError("Innhold ikke lastet")

            # Samle alle dokumenter fra listevisning (virtualisert)
            docs = await _scroll_and_collect_list_docs(
                page=page,
                page_num=page_num,
                per_page=per_page,
                timeout=timeout,
            )

            if not docs:
                if await _is_truly_empty_page(page, page_num):
                    print(f"[INFO] Side {page_num} er tom. Returnerer [].")
                    return []
                raise RuntimeError("0 dokumenter funnet uten tom-side-indikasjon")

            # Hent filer fra detaljsider i egen page
            context = page.context
            enriched_docs = []

            for d in docs:
                dokid = d.get("dokumentID")
                detalj_link = d.get("journal_link")

                filer = await _fetch_files_for_doc(
                    context=context,
                    detalj_link=detalj_link,
                    dokid=dokid,
                    timeout=timeout,
                )

                status = "Publisert" if filer else "Må bes om innsyn"

                d["filer"] = filer
                d["status"] = status

                enriched_docs.append(d)

            print(f"[INFO] Fant {len(enriched_docs)} dokumenter på side {page_num}")
            return enriched_docs

        except Exception as e:
            print(f"[WARN] Feil ved lasting/parsing av side {page_num} (forsøk {attempt}/{retries}): {e}")

            delay = min((2 ** (attempt - 1)) + random.uniform(0, 0.5), 20.0)
            print(f"[INFO] Venter {delay:.2f}s før nytt forsøk…")
            await asyncio.sleep(delay)

    print(f"[ERROR] Side {page_num} feilet etter {retries} forsøk.")
    return None
