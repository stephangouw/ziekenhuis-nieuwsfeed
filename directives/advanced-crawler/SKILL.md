---
name: advanced-crawler
description: Skill voor het robuust scrapen van 35 ziekenhuiswebsites met een RSS-first fallback strategie, uitgebreide paginering, AJAX-ondersteuning, bronvalidatie en strikte rate-limiting. Gebruik dit wanneer de nieuws-feed van een nieuw ziekenhuis of netwerk moet worden ontsloten en artikelen (limiet: 6 maanden terug) gevonden moeten worden.
---

# Advanced Hospital News Crawler

Deze skill beschrijft de vaste werkwijze voor het extraheren van nieuwsberichten van ziekenhuisportals. Omdat we ~35 zeer wisselende websites targeten en het merendeel géén actieve RSS-feed meer aanbiedt, leunt deze skill primair op intelligente datumherkenning, flexibele patroonherkenning, en geavanceerde paginering.

## � Stap 1: RSS-feed Controle (Prioriteit)

Onderzoek eerst of de website een actieve RSS-feed heeft voor nieuws. Dit is de meest efficiënte route en voorkomt fouten die via HTML scraping kunnen ontstaan.
- Zoek naar endpoints zoals `/rss`, `/feed`, of `/nieuws/feed/`.
- Controleer de `<header>` van de HTML-broncode voor onzichtbare `link rel="alternate" type="application/rss+xml"` verwijzingen (bijv. WordPress, Drupal).
- Als de feed valide XML data en actueel nieuws tot 6 maanden terug levert, is dit doel bereikt. Zo niet, activeer dan de Fallback Website Portal methode (Stap 2).

## 🛑 Stap 2: Fallback Bronvalidatie (De Portal)

Als er geen RSS-feed is, identificeer dan de exacte URL van de nieuwsoverzichtspagina (de 'Portal'). 

### Uitsluitingen (Blacklisting)
Om ruis te voorkomen, negeer de volgende link-patronen:
- **Talen:** `/english/`, `/polski/`, `?lang=en`
- **Patiëntenzorg:** `/patienten/`, `/aandoeningen/`, `/behandelingen/`, `/specialismen/`
- **Overig:** `/contact/`, `/over-ons/`, `/werken-bij/`, `/bereikbaarheid/`
- **Fundraising/Andere Info:** `/stichting/`, `/vrienden-van/`, `vacatures`, `agenda`

## 🛠️ Stap 3: Extractie & Brede Paginering

Na validatie navigeert het script om de artikelen op te halen. De focus ligt hierbij cruciaal op **Datumherkenning** en **Paginering**.

### Datumherkenning (Cruciaal voor Definition of Done)
De datums op moderne portals zijn vaak extreem divers geformateerd. De skill móét in staat zijn om de "6-maanden-regel" blind toe te passen door al het volgende te engineeren:
1. **Nederlandse Tekst Formaten:** "14 februari 2026", "12 maart", "14-02-2026". Converteer deze via een taal-bewuste datetime parser (zoals `dateparser`) naar één standaardformaat (bijv. YYYY-MM-DD).
2. **Relatieve Datums:** "3 weken geleden", "2 dagen geleden". De module moet exact begrijpen welke datum dit vandaag betekent.

### Uitgebreide Paginering-Logica (Robuustheid)
Bijna alle sites eisen dat de skill de archieven doorsoekt met knoppen. Vang de volgende variaties dynamisch af:
1. **URL Query Parameters & Path:** `?page=2`, `?p=2`, `/pagina/2/`, `/page/2/`.
2. **HTML Navigatie Elementen:** Link met attribuut `rel="next"`, Anchor tags met letterlijke tekst `Volgende`, `Vorige` (afhankelijk van structuur), of een pijl symbool (`&raquo;`, `>`).
3. **Dynamische Banners / Knoppen ('Load More' / 'Toon Meer'):** 
   - Knoppen met label zoals "Laad meer", "Toon meer", "Meer nieuws". Vaak triggert dit AJAX/JSON verzoeken in plaats van een full-page-reload. Als het onmogelijk is de REST API te benaderen, vereist dit incidenteel Headless rendering.

### De 6-Maanden Cutoff (De Rem)
De operatie stopt direct de iteratieve loop wanneer aan deze voorwaarde is voldaan:
1. Transformeer de datum van het **oudst getoonde artikel** op de huidge pagina.
2. Is deze datum ouder dan **vandaag minus 6 maanden** (circa 180 dagen)?
   - **JA:** Stop de lus en bewaar het resultaat.
   - **NEE:** Zoek/trigger de 'Volgende' knop of API call en laad de volgende batch in.

## Best Practices
- **Extractie-Output:** Het script moet altijd de expliciete bron van extractie (`[Bron: RSS feed]` vs `[Bron: Website Scraper]`) toevoegen aan het object of de string-output, naast de **titel**, **publicatiedatum** en **directe URL** van het volledige artikel.
- **Throttling & Deduplicatie:** Pas ten minste 3 seconden `time.sleep` toe tussen paginering-verzoeken en ontdubbel op basis van `url` om "Sticky Topnieuws" of tegels die bovenin elke resultatenlijst ('Isala-stijl') terugkeren af te handelen.
