Strand kommune postliste-scraper
Dette prosjektet automatiserer innhenting og publisering av kommunens postliste (journalposter) med Python-scrapere og GitHub Actions. Systemet dekker daglige oppdateringer, planlagte oppdateringer og full historisk scraping.

Funksjoner
Daglig scraping (incremental)

Workflow: morgen.yml

Kjører hver morgen kl. 06:00

Henter nye oppføringer og oppdaterer endrede oppføringer

Bruker scraper.py i incremental-modus

Oppdaterings-scraping (update)

Workflow: oppdatering.yml

Kan kjøres manuelt eller planlagt

Går gjennom et konfigurerbart antall sider (standard 50)

Henter både nye oppføringer og oppdaterer eksisterende

Publisering (HTML)

Workflow: publish.yml

Genererer index.html fra postliste.json

Publiserer oppdatert postliste som statisk HTML

Full historisk scraping

Workflow: fullscrape.yml

Henter hele år eller halvår ved dato-intervall

Bruker scraper_dates.py

Resultat lagres i archive/ som egne JSON-filer (for eksempel postliste_2006_H1.json)

Konfigurasjon
Alle scrapere leser innstillinger fra config.json. . Eksempel:
{
  "mode": "incremental",
  "max_pages_incremental": 10,
  "max_pages_update": 50,
  "max_pages_full": 200,
  "per_page": 100
}
mode: styrer hvordan scraperen kjører (incremental, update, full)

max_pages_incremental: antall sider som sjekkes i daglig scraping

max_pages_update: antall sider som sjekkes i oppdateringsmodus

max_pages_full: antall sider som sjekkes i full scraping

per_page: antall oppføringer per side

For fullscrape.yml brukes en egen config_fullscrape.json for historiske intervaller, slik at config.json for daglig drift ikke overskrives.

Scrapere
scraper.py
Brukes av morgen.yml

Kjører i incremental-modus

Stopper først når alle oppføringer på en side er kjente

Fanger både nye og oppdaterte oppføringer

Sorterer kronologisk basert på ekte dato (ikke tekst)

scraper_dates.py
Brukes av fullscrape.yml

Kjører i full-modus

Leser max_pages_full og per_page fra config.json

Tar inn dato eller periode som argument:

python scraper_dates.py 2025-12-01

python scraper_dates.py 2025-01-01 2025-12-31

Sorterer kronologisk basert på ekte dato (parsed_date)

Filstruktur
.
├── archive/                # Historiske JSON-filer (fullscrape)
├── postliste.json          # Hovedfil med siste oppføringer
├── index.html              # Generert HTML fra postliste.json
├── scraper.py              # Incremental scraper
├── scraper_dates.py        # Full scraper med dato-intervall
├── generate_html.py        # Lager HTML fra JSON
├── config.json             # Daglig konfigurasjon
├── config_fullscrape.json  # Fullscrape-konfigurasjon
└── .github/workflows/      # GitHub Actions workflows
Workflows
morgen.yml

Daglig incremental scraping og generering av HTML

oppdatering.yml

Manuell eller planlagt update-scraping

publish.yml

Genererer og publiserer HTML basert på postliste.json

fullscrape.yml

Full historisk scraping for år/halvår, lagrer JSON i archive/

Output
JSON-filer (postliste.json og arkivfiler) med alle oppføringer

HTML (index.html) for lesbar presentasjon

Hver oppføring inneholder:

tittel

dato (dd.mm.yyyy)

parsed_date (ISO)

dokumentID

dokumenttype

avsender_mottaker

journal_link

filer

status

Bruk
Daglig drift skjer automatisk via GitHub Actions

Fullscrape trigges manuelt via workflow_dispatch med valgt dato-interval

Alle endringer commit-tes og pushes automatisk til repoet

Viktig
Incremental-modus stopper først når alle oppføringer på en side er kjente

Update-modus henter både nye og oppdaterte oppføringer

Full-modus brukes for historiske perioder og henter opptil max_pages_full sider

config.json er kilden til sannhet for scraper-innstillinger, mens config_fullscrape.json brukes kun av fullscrape.yml
