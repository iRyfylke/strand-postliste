import os
import sys
import json
import time
import logging
from typing import List, Dict, Any, Optional

import requests


BASE_URL = "https://www.strand.kommune.no"
OVERVIEW_URL = f"{BASE_URL}/api/presentation/v2/nye-innsyn/overview"
DOCUMENT_URL_TEMPLATE = f"{BASE_URL}/api/presentation/v2/nye-innsyn/dokument/{{identifier}}"


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def make_session() -> requests.Session:
    """
    Lager en requests-session med fornuftige headers.
    """
    s = requests.Session()
    s.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.6099.200 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "nb-NO,nb;q=0.9,en;q=0.8",
        "Content-Type": "application/json",
        "Origin": BASE_URL,
        "Referer": (
            f"{BASE_URL}/tjenester/politikk-innsyn-og-medvirkning/"
            "postliste-dokumenter-og-vedtak/sok-i-post-dokumenter-og-saker/"
        ),
    })
    return s


def fetch_overview_page(
    session: requests.Session,
    page: int,
    page_size: int = 100,
    max_retries: int = 3,
    delay: float = 0.5,
) -> List[Dict[str, Any]]:
    """
    Henter én side fra overview-API-et.
    Returnerer listen av items (kan være tom).
    """
    payload = {
        "type": 0,
        "keyValues": [
            {"key": "page", "value": str(page)},
            {"key": "pageSize", "value": str(page_size)},
        ],
    }

    for attempt in range(1, max_retries + 1):
        try:
            logging.info(f"Fetcher overview page={page}, forsøk {attempt}/{max_retries}")
            resp = session.post(OVERVIEW_URL, json=payload, timeout=30)
            if resp.status_code != 200:
                logging.warning(f"Overview page {page} ga status {resp.status_code}")
                time.sleep(delay)
                continue

            data = resp.json()
            items = (
                data.get("content", {})
                    .get("searchItems", {})
                    .get("items", [])
            )
            logging.info(f"Overview page {page}: fikk {len(items)} items")
            return items

        except Exception as e:
            logging.warning(f"Feil ved henting av overview page {page}: {e}")
            time.sleep(delay)

    logging.error(f"Ga opp overview page {page} etter {max_retries} forsøk")
    return []


def fetch_document_details(
    session: requests.Session,
    identifier: str,
    max_retries: int = 3,
    delay: float = 0.5,
) -> Optional[Dict[str, Any]]:
    """
    Henter detaljer (inkl. vedlegg) for et gitt identifier.
    """
    url = DOCUMENT_URL_TEMPLATE.format(identifier=identifier)
    params = {"fromMeeting": "false"}

    for attempt in range(1, max_retries + 1):
        try:
            logging.info(f"Henter detaljer for identifier={identifier}, forsøk {attempt}/{max_retries}")
            resp = session.get(url, params=params, timeout=30)
            if resp.status_code != 200:
                logging.warning(f"Detaljkall ga status {resp.status_code} for identifier={identifier}")
                time.sleep(delay)
                continue

            data = resp.json()
            return data.get("content", {}).get("model", {})

        except Exception as e:
            logging.warning(f"Feil ved detaljkall for identifier={identifier}: {e}")
            time.sleep(delay)

    logging.error(f"Ga opp detaljkall for identifier={identifier} etter {max_retries} forsøk")
    return None


def parse_date_str(date_str: Optional[str]) -> Optional[str]:
    """
    Input: '06.01.2026' -> '2026-01-06'
    Returnerer ISO-dato eller None.
    """
    if not date_str:
        return None
    try:
        d, m, y = date_str.split(".")
        return f"{y}-{m.zfill(2)}-{d.zfill(2)}"
    except Exception:
        return None


def extract_year(date_str: Optional[str]) -> Optional[int]:
    """
    Henter årstall fra '06.01.2026'.
    """
    if not date_str:
        return None
    parts = date_str.split(".")
    if len(parts) != 3:
        return None
    try:
        return int(parts[2])
    except ValueError:
        return None


def build_document_record(
    overview_item: Dict[str, Any],
    details: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Mapper overview + details til vårt dokumentformat.
    """
    props = overview_item.get("properties", {}) or {}
    dato_raw = props.get("dato")
    dato_iso = parse_date_str(dato_raw)

    # Avsender/mottaker – overview og details kan utfylle hverandre
    avsender = props.get("avsender")
    mottaker = props.get("mottaker")

    if details:
        fra = details.get("fra") or []
        til = details.get("til") or []
        if not avsender and fra:
            avsender = ", ".join(fra)
        if not mottaker and til:
            mottaker = ", ".join(til)

    if avsender:
        am = f"Avsender: {avsender}"
    elif mottaker:
        am = f"Mottaker: {mottaker}"
    else:
        am = ""

    # Filer fra details.vedleggGruppe
    filer: List[Dict[str, Any]] = []
    if details:
        grupper = details.get("vedleggGruppe") or []
        for g in grupper:
            vlist = g.get("vedlegg") or []
            for v in vlist:
                file_url = v.get("fileUrl")
                if not file_url:
                    continue
                if not file_url.startswith("http"):
                    file_url = BASE_URL + file_url

                filer.append({
                    "tittel": v.get("title"),
                    "filtype": v.get("filtype"),
                    "filstorrelse": v.get("filstorrelseFormatted"),
                    "visibility": v.get("visibility"),
                    "url": file_url,
                })

    status = "Publisert" if filer else "Må bes om innsyn"

    record = {
        "tittel": overview_item.get("title"),
        "dato": dato_raw,
        "dato_iso": dato_iso,
        "dokumentID": props.get("dokumentID"),
        "dokumenttype": overview_item.get("type"),
        "avsender_mottaker": am,
        "journal_link": None,  # vi har ikke ren frontend-URL her; kan konstrueres ved behov
        "filer": filer,
        "status": status,
        "identifier": overview_item.get("identifier"),
        "synlighet": props.get("synlighet"),
    }

    if details:
        record["friendlyId"] = details.get("friendlyId")
        record["journaldatoFormatted"] = details.get("journaldatoFormatted")

    return record


def scrape_year(year: int, max_pages: int = 10000, page_size: int = 100) -> List[Dict[str, Any]]:
    """
    Skraper alle sider via API-et og filtrerer på gitt år (på dato-feltet i overview).
    Vi stopper når overview-API-et returnerer 0 items.
    """
    session = make_session()
    all_docs: List[Dict[str, Any]] = []

    for page in range(1, max_pages + 1):
        items = fetch_overview_page(session, page=page, page_size=page_size)
        if not items:
            logging.info(f"Ingen flere items på page={page}, stopper paginering.")
            break

        # Filtrer på år basert på properties.dato
        relevant_items = []
        for item in items:
            props = item.get("properties", {}) or {}
            dato_raw = props.get("dato")
            y = extract_year(dato_raw)
            if y == year:
                relevant_items.append(item)

        logging.info(f"Page={page}: {len(relevant_items)} items matchet år={year}")

        for item in relevant_items:
            identifier = item.get("identifier")
            if not identifier:
                continue

            details = fetch_document_details(session, identifier)
            record = build_document_record(item, details)
            all_docs.append(record)

        # Liten pause for å være snill mot serveren
        time.sleep(0.2)

    logging.info(f"Totalt {len(all_docs)} dokumenter funnet for år={year}")
    return all_docs


def main():
    if len(sys.argv) < 2:
        print("Bruk: python scraper_api.py <year>")
        sys.exit(1)

    try:
        year = int(sys.argv[1])
    except ValueError:
        print("Year må være et heltall, f.eks. 2014")
        sys.exit(1)

    os.makedirs("data", exist_ok=True)
    output_path = os.path.join("data", f"postliste_api_{year}.jsonl")

    docs = scrape_year(year)

    with open(output_path, "w", encoding="utf-8") as f:
        for d in docs:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")

    logging.info(f"Skrevet {len(docs)} dokumenter til {output_path}")


if __name__ == "__main__":
    main()
