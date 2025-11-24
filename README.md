# Strand kommune – uoffisiell postliste speiling

Dette prosjektet skraper den offentlige postlisten til Strand kommune og publiserer resultatene automatisk som en statisk nettside via GitHub Pages. Målet er å gjøre det enklere å følge med på kommunens dokumenter og samtidig synliggjøre hvilke oppføringer som krever innsynsbegjæring.

## ✨ Funksjonalitet

- **Skraping av postlisten**: Henter ut dato, tittel, avsender, mottaker og saksnummer.
- **PDF‑nedlasting**: Lagrer publiserte dokumenter som PDF der lenker er tilgjengelige.
- **Innsynsoppføringer**: Oppføringer uten publisert dokument dupliseres med tydelig merking og en forhåndsutfylt e‑postlenke for innsynsbegjæring.
- **Automatisk publisering**: Genererer `index.html` og `postliste.json` som publiseres direkte fra `main`‑branch til GitHub Pages.
- **Daglig oppdatering**: GitHub Actions kjører skriptet automatisk hver dag og oppdaterer nettsiden.

## 📂 Struktur

- `scraper.py` – hovedskriptet som henter og genererer innhold.
- `templates/base.html` – HTML‑mal som brukes til å bygge nettsiden.
- `assets/styles.css` – enkel CSS for styling.
- `pdf_dokumenter/` – mappe der nedlastede PDF‑filer lagres.
- `postliste.json` – strukturert datauttrekk av postlisten.

## 🚀 Oppsett

1. **Klon repoet** eller opprett det på GitHub.
2. Sørg for at `scraper.py` ligger i rotmappen.
3. Aktiver GitHub Pages:
   - Gå til **Settings → Pages**.
   - Velg **Branch: main** og **Folder: /root**.
4. Workflow (`.github/workflows/publish.yml`) kjører automatisk og oppdaterer siden.

Nettsiden blir tilgjengelig på:  
`https://<brukernavn>.github.io/strand-postliste/`

## ⚖️ Juridiske hensyn

- Dokumentene som publiseres er allerede offentliggjort av kommunen.
- Oppføringer som krever innsyn markeres tydelig og lenker til en forhåndsutfylt e‑post til kommunens postmottak.
- Husk at personopplysninger kan forekomme i dokumentene. Prosjektet bør brukes med varsomhet og tydelig merkes som en **uoffisiell speiling**.

## 🛠️ Videre arbeid

- Finjustere CSS og layout.
- Tilpasse selektorer i `parse_postliste` dersom kommunens HTML‑struktur endres.
- Legge til støtte for flere kommuner.
- Utvide med RSS‑feed eller API for enklere integrasjon.

---

Dette prosjektet er laget som et uoffisielt verktøy for å øke innsyn og transparens. Det er ikke tilknyttet Strand kommune.
