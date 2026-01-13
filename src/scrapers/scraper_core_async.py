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
    """
    Robust lastestrategi for SPA-siden:
      - Vent på networkidle
      - Gi JS litt ekstra tid
      - Scroll litt for å trigge lazy loading
      - Fallback til selector-wait
    Returnerer True hvis vi mener siden er lastet nok til å lese innhold.
    """

    try:
        # Vent på at nettverk er relativt stille
        try:
            await page.wait_for_load_state("networkidle", timeout=timeout)
        except Exception as e:
            print(f"[WARN] Side {page_num}: wait_for_load_state('networkidle') feilet: {e}")

        # Gi JS litt tid til å tegne DOM
        await page.wait_for_timeout(400)

        # Scroll-nudge for å trigge evt. lazy loading
        try:
            await page.evaluate("window.scrollBy(0, 200)")
            await page.wait_for_timeout(300)
        except Exception as e:
            print(f"[WARN] Side {page_num}: scroll-nudge feilet: {e}")

        # Fallback / eksplisitt wait på artikler
        try:
            await page.wait_for_selector(
                "article.bc-content-teaser--item",
                timeout=timeout,
                state="attached",
            )
        except Exception as e:
            print(f"[WARN] Ingen artikler funnet på side {page_num} (selector-timeout): {e}")
            # Vi returnerer False her – kallende kode må avgjøre om det er tom side eller feil
            return False

        return True

    except Exception as e:
        print(f"[WARN] Side {page_num}: _wait_for_content feilet: {e}")
        return False


async def _is_truly_empty_page(page, page_num) -> bool:
    """
    Forsøk å avgjøre om siden faktisk er "tom" (ingen dokumenter),
    eller om det er en lastingsfeil.

    Returnerer:
      - True  -> siden virker gyldig, men uten dokumenter (skal IKKE i failed_pages)
      - False -> vi vet ikke / dette bør behandles som teknisk feil
    """

    try:
        # Sjekk om vi har en container for innhold
        container = await page.query_selector("main, .bc-content, body")
        if not container:
            # Ingen fornuftig container – dette lukter teknisk feil
            return False

        html = await page.content()
        text = (html or "").lower()

        # Heuristikk: typiske tekster for tomme resultater
        markers = [
            "ingen dokumenter",
            "ingen treff",
            "ingen resultater",
            "ingen saker",
        ]

        if any(m in text for m in markers):
            print(f"[INFO] Side {page_num}: side ser ut til å være tom (ingen dokumenter).")
            return True

        # Sjekk eksplisitt om vi faktisk har artikler
        artikler = await page.query_selector_all("article.bc-content-teaser--item")
        if len(artikler) == 0:
            # Ingen artikler, ingen "ingen dokumenter"-tekst → usikkert, behandle som feil
            print(f"[WARN] Side {page_num}: 0 artikler og ingen tydelig 'ingen dokumenter'-tekst.")
            return False

        # Har artikler → definitivt ikke tom
        return False

    except Exception as e:
        print(f"[WARN] Side {page_num}: _is_truly_empty_page feilet: {e}")
        return False


async def hent_side_async(page_num, page, per_page, retries=5, timeout=10_000):
    """
    Optimalisert async-versjon av hent_side():
      - Gjenbruker page-instans
      - Navigerer async
      - Raskere detaljvisning
      - Mindre memory leaks
      - Bedre retry-logikk (exponential backoff + jitter)
      - Mer robust retur til hovedsiden
      - Skiller mellom ekte tom side og teknisk feil
    """

    url = BASE_URL.format(page=page_num, page_size=per_page)

    for attempt in range(1, retries + 1):
        try:
            print(f"[INFO] (async) Åpner side {page_num} (forsøk {attempt}/{retries}): {url}")

            # Naviger til siden
            ok = await safe_goto(page, url, retries=1, timeout=timeout)
            if not ok:
                raise RuntimeError("safe_goto feilet")

            # Robust lastestrategi for innholdet
            loaded = await _wait_for_content(page, page_num, timeout=timeout)
            if not loaded:
                # Sjekk om siden faktisk er tom (ikke teknisk feil)
                if await _is_truly_empty_page(page, page_num):
                    # Ekte tom side: returner tom liste slik at den IKKE havner i failed_pages
                    print(f"[INFO] (async) Side {page_num} er tom, men gyldig. Returnerer tom liste.")
                    return []
                # Ellers: kast for å trigge retry
                raise RuntimeError("Innhold ikke lastet / ingen artikler tilgjengelig")

            # Hent artikler
            artikler = await page.query_selector_all("article.bc-content-teaser--item")
            antall = len(artikler)
            print(f"[INFO] (async) Fant {antall} dokumenter på side {page_num}")

            if antall == 0:
                # Samme logikk som over, men ekstra sikkerhet
                if await _is_truly_empty_page(page, page_num):
                    print(f"[INFO] (async) Side {page_num} er tom, men gyldig (etter artikler-sjekk).")
                    return []
                raise RuntimeError("0 artikler funnet uten klar indikasjon på tom side")

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
                    if link_elem:
                        detalj_link = await link_elem.get_attribute("href")
                except Exception:
                    detalj_link = ""

                if detalj_link and not detalj_link.startswith("http"):
                    detalj_link = "https://www.strand.kommune.no" + detalj_link

                # Hent filer (async, raskere)
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
                        # Gå tilbake til hovedsiden
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

            # Exponential backoff + jitter
            base_delay = 1.0 * (2 ** (attempt - 1))  # 1, 2, 4, 8, ...
            jitter = random.uniform(0, 0.5 * base_delay)
            delay = base_delay + jitter
            max_delay = 20.0
            delay = min(delay, max_delay)

            print(f"[INFO] (async) Venter {delay:.2f}s før nytt forsøk på side {page_num}…")
            await asyncio.sleep(delay)

    print(f"[ERROR] (async) Side {page_num} feilet etter {retries} forsøk.")
    return None
