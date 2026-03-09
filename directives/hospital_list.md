# Ziekenhuis Portal Overzicht (Crawler 2.0)

Dit document bevat de volledige lijst van de ~35 doel-ziekenhuizen, inclusief hun netwerk, URL's en specifieke technische aandachtspunten (edge cases) voor de Advanced Crawler.

| Categorie | Ziekenhuis | RSS-feed? | Directe nieuws-portal (URL) | Aandachtspunt voor skill |
| :--- | :--- | :--- | :--- | :--- |
| **Brainport** | Elkerliek | Nee | `elkerliek.nl/nieuws-overzicht` | Gebruikt filteropties bovenaan. |
| | SJG Weert | Nee | `sjgweert.nl/nieuws` | Let op: korte intro-teksten. |
| | Máxima Medisch Centrum | Nee | `mmc.nl/over-mmc/nieuws/` | Gebruikt een 'Laad meer' knop (scroll). |
| | Catharina Ziekenhuis | Ja | `catharinaziekenhuis.nl/nieuws/feed/` | RSS is hier de snelste methode. |
| | St. Anna Ziekenhuis | Nee | `st-anna.nl/actueel/nieuws/` | Eenvoudige lijst, filter op datum. |
| **mProve** | Isala | Nee | `isala.nl/nieuws` | Maakt gebruik van 'tegels'. |
| | Noordwest | Nee | `nwz.nl/nieuwsoverzicht-pagina` | Gebruikt Playwright voor Next.js SPA en genummerde paginering (1, 2, 3...). |
| | Rijnstate | Nee | `rijnstate.nl/nieuws` | Filter op 'Nieuwsbericht'. |
| | Zuyderland | Ja | `zuyderland.nl/nieuws/feed/` | RSS beschikbaar via WordPress. |
| | Albert Schweitzer ziekenhuis | Nee | `asz.nl/nieuws/nieuwsberichten/` | Gebruikt paginanummers (1, 2, 3). |
| | Jeroen Bosch Ziekenhuis | Nee | `jeroenboschziekenhuis.nl/nieuws` | **PLAYWRIGHT VEREIST** (Zware anti-bot obstructie, curl_cffi geblokkeerd). Gebruikt paginering `?page=`. |
| **NFU** | Amsterdam UMC | Nee | `amsterdamumc.org/nl/nieuws.htm` | Veel wetenschappelijk nieuws. |
| | Erasmus MC | Nee | `erasmusmc.nl/nl-nl/nieuws` | Filter op datum is essentieel. |
| | LUMC | Nee | `lumc.nl/over-lumc/nieuws` | Let op: negeer agenda-items. |
| | MUMC+ | Nee | `mumc.nl/actueel/nieuws` | Gebruikt 'Laad meer' systeem. |
| | Radboudumc | Nee | `radboudumc.nl/nieuws` | Zeer actueel, veel berichten. |
| | UMCG | Nee | `nieuws.umcg.nl` | Eigen subdomein voor nieuws. |
| | UMC Utrecht | Nee | `umcutrecht.nl/nl/over-ons/nieuws` | Paginering via 'Vorige/Volgende'. |
| **STZ / Overig**| Amphia | Nee | `amphia.nl/nieuws` | Gebruikt categorie-labels. |
| | St. Antonius | Nee | `antoniusziekenhuis.nl/nieuws` | Negeer de zoekbalk-resultaten. |
| | CWZ | Nee | `cwz.nl/actueel/nieuws` | Filter op de laatste 6 maanden. |
| | ETZ | Nee | `etz.nl/nieuws` | Let op: verschillende locaties. |
| | Franciscus | Nee | `franciscus.nl/nieuws` | Gebruikt paginanummers. |
| | Gelre | Nee | `gelreziekenhuizen.nl/nieuws` | Filter op 'Patiëntennieuws'. |
| | HMC | Nee | `haaglandenmc.nl/nieuws` | Let op: negeer de 'HMC-magazines'. |
| | HagaZiekenhuis| Nee | `hagaziekenhuis.nl/nieuws` | Gebruikt een simpel lijstje. |
| | Maasstad | Nee | `maasstadziekenhuis.nl/nieuws` | Controleer op publicatiedatum. |
| | Martini | Nee | `martiniziekenhuis.nl/nieuws` | Let op: negeer vacatures. |
| | Meander MC | Nee | `meandermc.nl/nieuws` | Gebruikt 'Toon meer' knop. |
| | MST | Nee | `mst.nl/nieuws` | Let op: negeer banners. |
| | OLVG | Nee | `olvg.nl/nieuws` | Heeft vaak meerdere tags. |
| | Spaarne G. | Nee | `spaarnegasthuis.nl/nieuws` | Let op: regio Haarlem/Hoofddorp. |
| | Gelderse Vallei | Nee | `geldersevallei.nl/nieuws` | Gebruikt heldere datum-notatie. |
| | Bravis | Nee | `bravisziekenhuis.nl/nieuws` | Let op: negeer de stichting. |
