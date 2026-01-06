import time
from utils_playwright import safe_text, safe_goto
from utils_dates import parse_date_from_page, format_date

BASE_URL = (
    "https://www.strand.kommune.no/tjenester/politikk-innsyn-og-medvirkning/"
    "postliste-dokumenter-og-vedtak/sok-i-post-dokumenter-og-saker/#/"
    "?page={page}&pageSize={page_size}"
)


def hent_side(page_num, browser, per_page, retries=5):
    """
    Henter og parser én side.

    Returnerer:
      - liste med dokumenter ved suksess
      - None ved feil (etter alle retries)
    """
    url = BASE_URL.format(page=page_num, page_size=per_page)

    for attempt in range(1, retries + 1):
        page = None
        try:
            print(f"[INFO] Åpner side {page_num} (forsøk {attempt}/{retries}): {url}")

            page = browser.new_page()

            # Bruker safe_goto for robust navigasjon
            if not safe_goto(page, url, retries=1):
                raise RuntimeError("safe_goto feilet")

            # Litt ekstra tid til å rendre
            page.wait_for_timeout(1500)

            # Vent på artikler (kan ta tid)
            try:
                page.wait_for_selector("article.bc-content-teaser--item", timeout=45000)
            except Exception as e:
                # Hvis ingen artikler finnes etter timeout, betrakt det som feil (ikke ekte tom side)
                print(f"[WARN] Ingen artikler funnet på side {page_num} (forsøk {attempt}/{retries}): {e}")
                raise

            artikler = page.query_selector_all("article.bc-content-teaser--item")
            print(f"[INFO] Fant {len(artikler)} dokumenter på side {page_num}")

            if not artikler:
                # Dette er sannsynligvis en feiltilstand, ikke en ekte tom side
                raise RuntimeError("0 artikler funnet")

            docs = []

            for art in artikler:
                dokid = safe_text(art, ".bc-content-teaser-meta-property--dokumentID dd")
                if not dokid:
                    continue

                tittel = safe_text(art, ".bc-content-teaser-title-text")
                dato_raw = safe_text(art, ".bc-content-teaser-meta-property--dato dd")
                parsed = parse_date_from_page(dato_raw)

                doktype = safe_text(art, ".SakListItem_sakListItemTypeText__16759c")
                avsender = safe_text(art, ".bc-content-teaser-meta-property--avsender dd")
                mottaker = safe_text(art, ".bc-content-teaser-meta-property--mottaker dd")

                am = (
                    f"Avsender: {avsender}"
                    if avsender
                    else (f"Mottaker: {mottaker}" if mottaker else "")
                )

                detalj_link = ""
                try:
                    link_elem = art.evaluate_handle("node => node.closest('a')")
                    detalj_link = link_elem.get_attribute("href") if link_elem else ""
                except Exception:
                    pass

                if detalj_link and not detalj_link.startswith("http"):
                    detalj_link = "https://www.strand.kommune.no" + detalj_link

                filer = []
                if detalj_link:
                    dp = browser.new_page()
                    try:
                        if safe_goto(dp, detalj_link, retries=1):
                            dp.wait_for_timeout(1000)
                            for fl in dp.query_selector_all("a"):
                                href = fl.get_attribute("href")
                                tekst = fl.inner_text()
                                if href and "/api/presentation/v2/nye-innsyn/filer" in href:
                                    abs_url = href if href.startswith("http") else "https://www.strand.kommune.no" + href
                                    filer.append({
                                        "tekst": (tekst or "").strip(),
                                        "url": abs_url
                                    })
                    except Exception as e:
                        print(f"[WARN] Klarte ikke hente filer for {dokid}: {e}")
                    finally:
                        dp.close()

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
            print(f"[WARN] Feil ved lasting/parsing av side {page_num} (forsøk {attempt}/{retries}): {e}")
            time.sleep(2)

        finally:
            if page is not None:
                try:
                    page.close()
                except Exception:
                    pass

    print(f"[ERROR] Side {page_num} feilet etter {retries} forsøk.")
    return None
