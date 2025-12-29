⭐ Overordnet struktur for endringsdashboardet
Dashboardet får tre seksjoner:

🟦 SEKSJON 1 — Topplinje KPI‑er (det viktigste først)
Disse KPI‑ene gir et øyeblikksbilde av aktiviteten i kommunen.

1. Nye dokumenter (siste 30 dager)
Antall dokumenter med type = NEW

Viser hvor mye nytt som publiseres

2. Oppdaterte dokumenter (siste 30 dager)
Antall dokumenter med type = UPDATE

Viser hvor mye som endres i etterkant

3. Endringsrate (%)
endringsrate
=
oppdaterte dokumenter
nye + oppdaterte
×
100
Dette er en av de mest interessante KPI‑ene:

Høy rate → mye etterarbeid, revisjon, feilretting

Lav rate → stabil publiseringsprosess

4. Dokumenter med nye filer
Antall dokumenter der filer_count har økt

Dette er ofte de viktigste endringene

5. Dokumenter med statusendring
F.eks. . “Må bes om innsyn” → “Publisert”

Viktig for innsynsarbeid og transparens

🟩 SEKSJON 2 — Grafer og trender
Dette er den visuelle kjernen i dashboardet.

6. Endringer per dag / uke / måned (linjegraf)
Viser aktivitetsnivå over tid

Avslører topper (møter, politiske saker, store publiseringsdager)

7. Endringer per dokumenttype (bar chart)
Eksempler:

Møteinnkalling

Saksdokument

Protokoll

Brev

Notat

Gir innsikt i hvilke prosesser som er mest dynamiske.

8. Hvilke felter endres mest? (heatmap eller bar chart)
Basert på endringer i changes.json:

status

tittel

dokumenttype

avsender_mottaker

detalj_link

dato

dato_iso

filer_count

Dette er en av de mest verdifulle grafene:

Hvis “status” endres ofte → kommunen publiserer dokumenter i flere steg

Hvis “tittel” endres ofte → kvalitetssikring skjer etter publisering

Hvis “filer_count” endres ofte → nye vedlegg legges til fortløpende

9. Endringer per måned (trendlinje)
Langsiktig utvikling

Perfekt for å se om kommunen blir mer eller mindre stabil over tid

🟧 SEKSJON 3 — Dyp innsikt og tabeller
10. Siste 50 endringer (tabell)
Kolonner:

tidspunkt

dokumentID

tittel

type (NEW/UPDATE)

hvilke felter som endret seg

11. Dokumenter med flest endringer (toppliste)
Viser dokumenter som har vært gjennom mange revisjoner

Kan indikere:

komplekse saker

feilretting

politiske prosesser

innsynsforespørsler

12. Dokumenter med nye filer (tabell)
Viser dokumenter som har fått nye vedlegg

Høy verdi for innsyn og kontroll

13. Endringshistorikk for valgt dokument (detaljvisning)
Når du klikker på et dokument:

vis alle endringer i kronologisk rekkefølge

highlight hva som ble endret

vis gamle og nye verdier

Dette er ekstremt nyttig for revisjon og sporbarhet.

🎨 Hvordan dashboardet kan se ut (visuelt)
Topplinje (5 KPI‑bokser)
Store tall

Fargekoder (grønn/blå/oransje)

Ikoner (📄 🔄 📈 📎 🔓)

Midtseksjon (grafer)
Linjegraf: endringer over tid

Bar chart: endringer per dokumenttype

Heatmap: hvilke felter endres mest

Bunnseksjon (tabeller)
Siste endringer

Dokumenter med flest endringer

Dokumenter med nye filer

Høyre side (detaljvisning)
Når du klikker på en rad i tabellen

Viser full historikk for dokumentet
