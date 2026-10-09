# Tausta

Työkalut alkoivat ohj2:n koeputkena, jossa mdBook-kirja käännettiin
Zensicalilla. Periaate oli, että jokainen lisäys perustellaan jollakin
mdBookin ominaisuudella, jota kirja oikeasti käyttää. ohj1 kopioi koeputken ja
lisäsi omansa, ja ohj1:n versio (`rakenne-2027`, 39316cf) siirrettiin tähän
repoon 2026-09-18. Siitä lähtien muutokset on tehty täällä, ja ne ovat
kaikkien kirjojen käytössä.

Tämä tiedosto kertoo, mistä ominaisuudet tulivat. Ajan tasalla olevat tiedot
ovat muualla: käyttö ja ominaisuudet [README.md](README.md):ssä, perustelut
[PERUSTELUT.md](PERUSTELUT.md):ssä ja merkkauksen yhtenäistys
[YHTENAISTYS.md](YHTENAISTYS.md):ssä. Koeputken README kokonaisuudessaan
(käynnistys, mittaukset, ohj1:n muutokset tiedosto tiedostolta):
`git show 1f0ef94:TAUSTA.md`.

## mdBookin ominaisuudet

Koeputken tarkistuslista: mdBookin ominaisuus ja sen vastine.

| mdBook | Vastine |
| --- | --- |
| `SUMMARY.md`: numeroidut luvut, osan otsikko linkkinä osan etusivulle | `build_nav`, `navigation.indexes` |
| `{{#include tiedosto}}` | `convert_includes` |
| `> [!VINKKI]` ym. | `convert_alerts`, teeman admonition |
| `<details>` | `convert_details` (`markdown="1"`) |
| `<task>`, `<points>`, `<handout>` | `convert_tasks`, tasks.css: riippuva numerointi laatikon sijaan |
| `<div class="ht-reqs">` | `convert_divs`, requirements.css: numerointi 1.1, 1.2, … CSS-laskurista |
| `### [Windows](#tab/win)` | `convert_tabs`, `content.tabs.link` |
| ajonappi (playground) | playground.js: sama palvelin ja pyyntö kuin mdBookissa |
| `,ignore`, `,noplayground` | `convert_fences`: attribuutit luokiksi, väritys säilyy |
| `editable` (ACE-editori) | playground.js ilman ACE:a: muokattava `<code>`, "Peruuta muutokset"; väritys ei päivity kirjoittaessa, eikä ohjelma saa syötettä |
| `//-` piilorivit | `hide_lines`, hidelines.js: silmänappi; ajoon rivit menevät |
| `HIGHLIGHT_*_BEGIN/END` | `mark_highlights`, highlights.js |
| `// FILE:` monitiedostolohkot | `convert_files`: tiedosto per välilehti |
| plantuml, bob, mermaid | `convert_plantuml` (kuva), `convert_svgbob` (upotettu SVG); mermaid toimi aluksi teeman mermaid.js:llä, nyt `convert_mermaid` (beautiful-mermaid, upotettu SVG, 2026-10-08) |
| `<asciinema>` | asciinema.js; soitin vain sivuille, joilla on nauhoitus |
| `<i class="bi …">`, `<i class="fa …">` | `convert_icons`: teeman glyfit ja valikkopolun › |
| bonusmerkki `<i class="bi bi-stars">` | `convert_bonus_marks`; nyt oma merkintä `<i class="jyu-star"></i>` (2026-10-04) |
| ääkköset ankkureissa (`#käyttö`) | `convert_anchors`: sama muoto kuin teeman otsikkotunnuksissa |
| tulostus: koko kirja yhdeksi PDF:ksi | `build_print_page`, print.js/css |
| edellinen/seuraava, lisenssi ja linkit alatunnisteessa | `navigation.footer`, copyright.html |
| `.html`-päätteiset osoitteet (TIMin linkit) | hyväksyttiin, että vanhat osoitteet menivät vaihdossa rikki |
| KaTeX | ei käytössä, jätettiin pois |
| JYU-paletti ja kultainen korostus | ei tehty: värit ovat teeman. Bonusliuskan kulta on tummennettu, koska mdBookin `#C29A5B` on valkoista vasten vain 2,4:1 |

Haku, oikean reunan sisällysluettelo, responsiivinen navigaatio ja
teemanvaihdin tulivat teemalta sellaisinaan.

## Mitä ohj1 toi

ohj1 lisäsi ohj2:n koeputkeen seuraavat:

- C#: piilorivit, korostukset ja ajonappi `csharp`-lohkoille, ajo Jypelin
  kanssa (`feature-jypeli`) ja tulosteen kuvat (Jypelin ikkuna ilman tyhjää
  tekstilaatikkoa). Ajopyynnössä on `multifile`-kenttä vain
  monitiedostolohkolla, koska palvelimen C#-polku aikakatkaisee pyynnön,
  jossa on `multifile: false`.
- Oppaiden alertit Kokeile, Ei toimi vielä ja Kysymys jypelidocsista, jossa
  ne korvasivat TIM-wikin kuvat.
- Tiedostot, joista ei tehdä sivua (nyt `kirja.toml`:n `ei_sivuja`): mdBook
  kääntää vain `SUMMARY.md`:n luvut, Zensical jokaisen `.md`:n.
- `SUMMARY.md`:n `*`-luettelomerkki ja vaihtelevat sisennykset (1, 3 tai 4
  välilyöntiä); sisennetty otsikko sarakkeeseen 0 (`dedent_headings`).
- svgbob 0.7.6:n kiertotiet: `svgbob_problems` varoittaa ääkkösistä ja
  sulkeista, jotka piirtyvät väärin ilman lainausmerkkejä, ja
  `svgbob_fit_text` kasvattaa kuvaa, ettei lainattu teksti leikkaudu.
- Hakuikkunan tekstikoot, tyhjän suodatinpaneelin piilotus ja sulkunappi
  (search.js/css; ikkuna on shadow DOM:issa).
- Vaiheittainen ohje (`<walkthrough>`, `<step>`) ja yksittäinen animaatio
  (`<animation>`) Git-ohjeeseen; vaiheiden ääneenluku Azure Speechillä
  (`puhe.py`).
- Testaa tietosi -visa (`<visa>`; merkkaus ohj1:n `rakenne-2027`-haaran
  `curriculum/rakenne.md`).

## Siirron jälkeen

Lisätty tähän repoon 2026-09-18 alkaen; yksityiskohdat commit-viesteissä.

Sivusto:

- Alaviitteet ja `title`-attribuutit teeman vihjeinä (09-19). Vihjeet
  suuremmiksi ja tummassa teemassa erottuviksi (09-27); teeman tyyli myös
  skriptien lisäämille napeille, eikä napautus tai Esc jätä vihjettä auki
  (10-02); selaimen oma `title`-vihje ei tule teeman rinnalle, ja
  teemanvaihtimella on vihje myös näppäimistöllä (10-02).
- Alatunnisteeseen sivun muutoshistoria (09-23).
- Valikko kiskona 1180 px:stä alkaen, 11" iPad vaakatasossa (09-24);
  leveällä näytöllä keskitettynä tekstin kanssa (10-02).
- Hakukentän paikkamerkki "Hae" (09-25). Otsikon ¶-linkin vihje suomeksi
  (`permalink_title`, 10-04); siksi pohjassa on Zensicalin koko
  `markdown_extensions`-oletuslista.
- Sisällysluettelo: kapealla näytöllä sulkeutuu napautuksesta, seuraa
  lukukohtaa (`toc.follow`), oma vierityspalkki vain osoittimella (10-02);
  kulmanappi erottuu tummassa teemassa (10-03).
- Kirjasinvalikkoon tekstikoko 90–175 %, ja leipäteksti 10 % teeman kokoa
  suuremmaksi, koska teeman 15 px oli puhelimessa pieni (10-02).
- Asciinema-soitin yläpalkin alle (10-02).

Koodilohkot:

- `editable`-lohkot muokattaviksi (09-20).
- Kopiointinappi (09-22); `console`-lohkosta vain komennot (09-27). Napit
  eivät peitä koodia (09-26).

Merkkaus ja ääneenluku:

- mdBookin navigointiosio ja sivujen siirrot (`NEST_UNDER`) pois; alasivu on
  `SUMMARY.md`:ssä sisennetty etulinkki (09-21).
- Koko sivun ääneenluku (`[puhe] sivut`) ja nopeus (09-27); vaiheittaisen
  ohjeen äänet samaan äänivarastoon, joka on klooni eikä submodule (09-27–28).
- Bonusmerkki omaksi merkinnäksi `<i class="jyu-star"></i>`, ja mdBookin
  `bi-stars` poistui (10-04). Ääneenluku ohittaa kuvakkeiden lyhytkoodit,
  joten leikkeet eivät muutu, kun `<i class="bi …">` kirjoitetaan
  lyhytkoodiksi (10-04).

Ylläpito:

- Linkkitarkistus (`linkit/`): ulkoiset linkit ja ankkurit, myös kurssin
  TIM-sivuilta (09-18–19).
- `run.sh` päivittää `.venv`:n, kun Zensicalin versio vaihtuu (09-20) tai
  järjestelmän Python päivittyy (10-04), ja valitsee seuraavan vapaan portin,
  jos 8001 on varattu (10-02). Asennuksen eteneminen `vaihe.sh`:lla (09-25).
- Kaikkien kirjojen päivitys ja työkalujen kiinnitys kerralla (`skriptit/`,
  10-02).
- Zensical 0.0.62 → 0.0.68; 0.0.68 vaatii Python 3.11:n.

## Avoinna koeputken ajoilta

- JYU-paletti (ks. taulukko).
- ohj2:n `osa1/index.md` kuvaa teemanapin mdBookin tapaan ("vaalea, tumma,
  automaattinen"), vaikka Zensicalin nappi on kaksiasentoinen.
