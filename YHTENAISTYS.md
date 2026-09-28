# Yhtenäistys

Työkalut on koottu tähän repoon (ks. *Tehty*). Nyt yhtenäistetään merkkaus:
kirjojen `src/` on yhä mdBookin murretta, ja `convert.py` kääntää sen joka
ajolla. Tavoite on kirjoittaa lähde Zensicalin merkinnöin aina, kun se on
helppoa ja luontevaa, ja poistaa vastaava muunnos. Omat merkinnät jäävät.

Muunnoksen voi poistaa vasta, kun se on ajettu jokaisen kirjan lähteeseen ja
koekirjaan (`tests/book/`). Haara kiinnittää oman työkaluversionsa, joten sen
lähde kirjoitetaan uusiksi ennen kuin osoitin siirtyy versioon ilman muunnosta.

## mdBook-merkinnät ja Zensical-vastineet

| mdBook | Zensical | ohj1 | ohj2 | jy | convert.py |
| --- | --- | --- | --- | --- | --- |
| `> [!VINKKI]` | `!!! tip "Vinkki"` | 22 | 75 | 61 | `convert_alerts` |
| `<details>`, monirivinen `<summary>` | `<details markdown="1">`, `markdown="block"` | 32 | 86 + 6 | 2 | `convert_details` |
| ` ```java,ignore ` | ` ```{ .java .ignore } ` | 27 | 289 | 787 | `convert_fences` |
| `(#käyttö)`, `## Otsikko{#id}` | `(#kaytto)`, `## Otsikko {#id}` | 3 | 6 + 1 | – | `convert_anchors` |
| `<br />` omana kappaleenaan | pois | – | 4 | – | `drop_breaks` |
| `<div class="req">` | `<div class="req" markdown="1">` | – | 9 | – | `convert_divs` |
| `### [Windows](#tab/win)` … `***` | `=== "Windows"` | 14 | 9 | – | `convert_tabs` |
| `<i class="bi bi-chevron-right">` | `›` | ✓ | 58 | – | `convert_icons` |
| `<i class="bi bi-list">` ym. | `:material-menu:` ym. | – | 22 | – | `convert_icons`, `icons/` |
| `<i class="bi bi-stars">` | `:material-creation:{ .jyu-bonus }` | 5 | 30 | – | `convert_bonus_marks` |
| sisennetty otsikko | otsikko sarakkeessa 0 | ✓ | – | – | `dedent_headings` |
| `SUMMARY.md` | `nav:` käsin | 55 | 72 | 106 | `build_nav` |
| `{{#include polku}}` | `--8<-- "polku"` | 2 | 194 | – | `convert_includes` |

Luku = esiintymät lähteessä (ohj1 `dev`, ohj2 ja jy `main`, 2026-09-28;
välilehdistä joukot, `SUMMARY.md`:stä rivit), – = ei esiintymiä, ✓ = kirjoitettu
uusiksi. Kun rivillä ei ole lukuja, sen muunnoksen voi poistaa. Poistettu
2026-09-21: `[siirrot]` (`NEST_UNDER`) ja `DROP_SECTIONS`.

- **Aidat:** `fence_language` on ensin opetettava lukemaan `{ .kieli … }`,
  muuten piilo- ja korostusrivit katoavat (ohj2 66, jy 44 lohkoa).
- **Alertit:** sisältö sisennetään neljällä välilyönnillä. Zensicalin
  `callouts`-liitännäinen pitäisi merkinnän `> [!…]`, mutta suomenkieliset
  tyypit tarvitsisivat oman CSS:n. Kokeilematta.
- **Välilehdet** viimeisenä, koska sisennetty `> [!` ei ole alertti.
  `extra.tab_labels` jää: `content.html` ei linkitä tiedostovälilehtiä.
  Nyt välilehden sisällä oleva `<details>` jää `<p>`-kääreeseen (ohj1 4,
  ohj2 4 lohkoa), koska `convert_tabs` sisentää sen. Tarkista, korjaako
  `===`-muoto tai `???` (`pymdownx.details`) tämän.
- **Bonusmerkki:** lyhytkoodia ei jäsennetä `<summary>`-rivillä, jolla on 4/5
  (ohj1) ja 22/30 (ohj2) merkeistä. Kokeilematta.
- **`SUMMARY.md`:** `nav.yml` on generoitu, joten käsin kirjoitettu `nav:`
  menee kirjan `mkdocs.yml`:ään, ja `build_print_page` lukee sen sieltä.
  Lukujen numerot kirjoitetaan otsikoihin tai jäävät koodiksi.
- **`{{#include}}`:** `pymdownx.snippets` ei ole oletuslistalla, ja oma
  `markdown_extensions` korvaa koko listan (PERUSTELUT.md, Ansat). Polut
  ratkeavat `base_path`ista eivätkä sivusta. Kokeilematta.

## Omat merkinnät, jotka jäävät

Vastinetta ei ole, tai se vaatisi laskemaan käsin. Perustelut:
[PERUSTELUT.md](PERUSTELUT.md) ja funktioiden docstringit.

| Merkintä | convert.py | Miksi jää |
| --- | --- | --- |
| `//-` piilorivi | `hide_lines` | muuten `data-hidden="1 3"` käsin ja uudet numerot joka lisäyksellä |
| `// HIGHLIGHT_GREEN_BEGIN` … `_END` | `mark_highlights` | sama |
| `// FILE: Nimi.java` | `convert_files` | yksi rivi välilehden ja `.multifile`-aidan sijaan |
| `<task>`, `<task-title>`, `<points>` | `convert_tasks` | kortti on HTML-kehys, jota ei kirjoiteta käsin |
| `<visa>`, `<walkthrough>`, `<animation>` | `convert_quizzes`, `convert_walkthroughs`, `convert_animations` | omia ominaisuuksia |
| ` ```plantuml `, ` ```bob ` | `convert_plantuml`, `convert_svgbob` | piirto ei ole teeman ominaisuus |
| suoraan kirjoitettu `›` | `convert_icons` | valikkopolun nuoli vaimealla värillä |
| (koko kirja) | `build_print_page`, `build_extra`, `mark_speech` | tulostussivu, muokkauslinkit, välilehtimuisti, ääneenluku |

## Järjestys ja työtapa

1. Heti: `dedent_headings` (ei esiintymiä).
2. `convert_page`n järjestyksessä: ankkurit, aidat, alertit, details,
   `<br />`, divit, bonusmerkit, ikonit ja välilehdet viimeisenä.
3. `SUMMARY.md` ja `{{#include}}`, kun numerointi ja snippets on kokeiltu.

Yksi commit per muunnos per kirja. Lähde kirjoitetaan skriptillä, useimmiten
muunnoksen omalla funktiolla. Todennus: `docs/` pysyy tavulleen samana
(ikoneissa vertaa `site/`:ä), ja `./zensical/run.sh test` menee läpi.
Muunnos, sen testit ja koekirjan merkinnät poistuvat samassa
työkalucommitissa. Muut haarat (esim. ohj1 `rakenne-2027`) saavat saman
skriptin; konfliktissa otetaan haaran versio ja ajetaan skripti uudelleen.

**Avoin: vaihtoehto C.** Jäljelle jäävät sivukohtaiset muunnokset
Python-Markdown-esikäsittelijöiksi (`markdown_extensions`; Zensical ei tue
`hooks:`-avainta). Silloin `docs_dir: src` säilyttäisi linkit, kuvapolut,
`edit_uri`:n ja historian, eikä `sync_docs`ia, vahtia eikä jäänteiden
siivousta tarvittaisi. Kirjan tason askel jää: tulostussivu, `tab_labels` ja
kaavioiden välimuisti. Päätetään, kun kohta 2 on tehty.

## Tehty: työkalut yhteen repoon

Kirjat ottivat tämän repon submoduleksi 2026-09-18. mdBook poistettiin
kirjoista 2026-09-18–20 ja kirjakohtaiset poikkeukset 2026-09-21. Vaiheet,
todennus ja päiväkirja: `git show 4f8433d:YHTENAISTYS.md`.

- Työkalumuutos tehdään tähän repoon, ja kirjat päivittävät osoittimen, ensin
  `main`iin (README: Työkalujen muuttaminen).
- `pages.yml` kääntää `main`in ja `dev`in (`/dev/`, pidetään, päätös
  2026-09-23) `main`in komennoilla, kumpikin omalla osoittimellaan. Kun
  työkalujen käyttötapa muuttuu, jokainen käännettävä haara siirtyy kerralla.
- Sivustovalikko on ohj1:ssä ja jypelidocsissa, ei ohj2:ssa (päätös 2026-09-20).
- Devcontainer hakee submodulen ja ajaa `setup.sh`:n.
- Testit kääntävät koekirjan repon omalla `mkdocs.yml`:llä (`copy_book`), joten
  test_sitemenu.py riippuu kirjan `site_name`sta ja `extra.sites`-listasta.

Avoimet kysymykset:

- Otsikko "Kokeile käynnistää pelisi" (`> [!KOKEILE]`) on Jypeli-sanastoa.
  Yleisempi oletus vai kirjan oma otsikko `kirja.toml`issa?
- LICENSE puuttuu tästä reposta.
