# kirjatyokalut

Ohjelmointikurssien kirjojen ([ohj1](https://github.com/ohj-perus-jy/ohj1),
[ohj2](https://github.com/ohj-perus-jy/ohj2),
[jypelidocs](https://github.com/ohj-perus-jy/jypelidocs),
[containerapps](https://github.com/ohj-perus-jy/containerapps)) yhteinen
työkaluketju, joka muuntaa markdownilla kirjoitetun lähdeaineiston
[Zensical](https://zensical.org)-sivustoksi. Kirja käyttää tätä repoa
git-submodulena, jotta kaikista kirjoista saadaan yhtenäisen näköiset ja ominaisuuksiltaan samanlaiset.

Merkkauksessa on vielä mukana mdBook-murretta (`SUMMARY.md`, `{{#include}}`, `> [!VINKKI]`, `//-`-piilorivit
ym.), koska kirjat kirjoitettiin alun perin mdBookille.

- Miksi mikin ratkaisu on tehty: [PERUSTELUT.md](PERUSTELUT.md).
- Mitä työkalut tarjoavat: [Ominaisuudet](#ominaisuudet) alla.
- Mistä ominaisuudet tulivat (mdBook, ohj1, siirron jälkeen): [TAUSTA.md](TAUSTA.md).
- Mikä mdBookin merkintä on vielä käytössä, mikä on sen Zensical-vastine ja
  mitkä omat merkinnät jäävät; avoimet kysymykset: [YHTENAISTYS.md](YHTENAISTYS.md).

## Ominaisuudet

Jokainen ominaisuus on kaikkien kirjojen käytössä: kirja ottaa sen käyttöön
kirjoittamalla merkinnän `src/`:ään. Toteutus-sarakkeen funktiot ovat
`convert.py`:ssä ja tiedostot `assets/`:ssa tai `overrides/partials/`:ssa.

### Merkkaus: mitä `src/`:ään voi kirjoittaa

| Merkintä | Tulos | Toteutus |
| --- | --- | --- |
| `SUMMARY.md` | navigaatio: osat, numeroidut luvut, osan otsikko linkkinä osan etusivulle; sisennetty etulinkki on edellisen etulinkin alasivu (edellinen on hakemistonsa `index.md`) | `build_nav` |
| `{{#include tiedosto}}` | tiedoston sisältö tai valitut rivit paikalleen | `convert_includes` |
| `> [!VINKKI]` ym. | värillinen laatikko: Osaamistavoitteet, Huomautus, Vinkki, Tärkeää, Varoitus, Todo, WIP; oppaiden merkinnät Kokeile, Ei toimi vielä, Kysymys | `convert_alerts`, admonitions.css |
| `<details>`, `<summary>` | avattava osio, jonka sisällä Markdown toimii | `convert_details` |
| `<task>`, `<task-title num>`, `<points>`, `<handout>`, `<task-link>` | tehtäväkortti: numero, pisteet, tehtävänanto; Bonus-liuska, kun otsikossa on bonusmerkki | `convert_tasks`, tasks.css |
| `<i class="jyu-star"></i>` | bonusmerkki (bonustehtävä, valinnainen lisätieto); nimetään ruudunlukijalle, jos rivillä ei ole sanaa "bonus" tai "valinnais…" | `convert_bonus_marks`, tasks.css |
| `<div class="ht-reqs">` | harjoitustyön vaatimuslohko, numerointi 1.1, 1.2, … | `convert_divs`, requirements.css |
| `<visa>`, `<vaittama vastaus>`, `<kysymys>`, `<perustelu>` | Testaa tietosi -visa: valinta paljastaa vastauksen ja perustelun, vastaukset muistetaan selaimessa | `convert_quizzes`, visa.js/css |
| `### [Windows](#tab/win)` | käyttöjärjestelmävälilehdet; valinta pätee koko sivustolla ja muistetaan | `convert_tabs` |
| `<walkthrough scenes>`, `<step scene>` | vaiheittainen ohje: animoitu kohtaus askel kerrallaan, halutessa ääneen luettuna (`<walkthrough scenes audio>`, leikkeet äänivarastossa, `puhe.py`) | `convert_walkthroughs`, walkthrough.js/css |
| `<animation scenes scene>` | yksittäinen animaatio tavallisella sivulla; tahti `data-wait`, `data-type` | `convert_animations` |
| `<asciinema>` | terminaalinauhoitus soittimessa; soitin ladataan vain sivuille, joilla on nauhoitus | asciinema.js |
| ` ```mermaid `, ` ```bob `, ` ```plantuml ` | mermaid-kaavio (mm. UML-luokkakaavio) ja ascii-kaavio upotettuna SVG:nä, jonka värit seuraavat teemaa; plantuml-luokkakaavio kuvana (vanha tapa, korvataan mermaidilla); kaaviot kirjan `cache/`:ssa | `convert_mermaid`, `mermaid/render.mjs`, `convert_svgbob`, `convert_plantuml`, diagrams.css |
| `<i class="bi …">`, `<i class="fa …">` | kuvake teeman glyfinä; valikkopolun nuoli merkkinä › | `convert_icons`, `icons/`, icons.css |
| `[teksti](#käyttö)` | ankkuri ilman ääkkösiä, sama muoto kuin teeman otsikkotunnuksissa | `convert_anchors` |

### Koodilohkot

Kielet: `csharp`, `java`, `javascript` (korostetut rivit: `csharp`, `java`, `json`, `bash`).

| Merkintä | Tulos | Toteutus |
| --- | --- | --- |
| mikä tahansa koodilohko | kopiointinappi: näkyvä koodi leikepöydälle (piilorivit vain silmällä esiin otettuina), kuittaus napin vieressä; ` ```console `-lohkosta vain komennot ilman kehotetta (`$ `, `root@kontti:/app# `, pelkkä `# `) ja tulostetta, heredoc sellaisenaan | mkdocs-pohja.yml (`content.code.copy`), copy.js/css |
| ` ```csharp `, ` ```java ` | ajonappi: koodi ajetaan palvelimella, tuloste lohkon alle; Jypelin ikkuna kuvana. Ohjelma ei saa syötettä, joten syötettä lukeva lohko merkitään `,noplayground` | playground.js/css |
| `,ignore`, `,noplayground` | ei ajonappia, väritys säilyy | `convert_fences` |
| `,feature-jypeli` | ajo Jypeli-kirjaston kanssa (`csharp-jypeli`) | playground.js |
| `,editable` | lukija voi muuttaa koodia sivulla ja ajaa sen; "Peruuta muutokset" | playground.js |
| `//-` rivin alussa | piilorivi: ei näy, menee ajoon; silmänappi näyttää. Piilotilassa näkyvien rivien yhteinen sisennys on pois ja koodi alkaa vasemmasta reunasta; silmä liu'uttaa piilorivit ja sisennyksen esiin (0,3 s, ei liikettä reduced-motion-asetuksella). Etuliitteen perään ei tule välilyöntiä, se jäisi riviin | `hide_lines`, hidelines.js/css |
| `,copyhint`, `,playhint`, `,eyehint` | opastusnuoli kopiointi-, ajo- tai silmänapin alle: keinuva nuoli, joka poistuu napin ensimmäisellä painalluksella; lohkoon, jonka kohdalla toiminto esitellään. Painallus muistetaan selaimessa (localStorage `jyu-hints`), eikä sen napin nuolia näytetä enää millään sivulla. Toimii muiden määreiden kanssa (`csharp,noplayground,eyehint`); nuoli seuraa nappia, olipa rivissä mitä nappeja tahansa, ja jää pois, jos nappia ei ole | hints.js/css |
| `// HIGHLIGHT_GREEN_BEGIN` … `_END` | korostetut rivit: green, yellow, red, blue | `mark_highlights`, highlights.js/css |
| `// FILE: Nimi.java` | monitiedostolohko: tiedosto per välilehti, ajetaan yhdessä | `convert_files` |

### Sivusto: mitä lukija saa

| Ominaisuus | Toteutus |
| --- | --- |
| Valikko kiinteänä kiskona 1180 px:stä alkaen (11" iPad vaakatasossa), leveällä näytöllä keskitettynä tekstin kanssa; luvun avaus vierittää valikon kohdalleen | layout.css, nav-scroll.js |
| Nappien vihjeet (title) teeman tyyliin myös skriptien lisäämille napeille; napautuksen jälkeen vihje ei jää näkyviin | tooltips.js |
| Sisällysluettelo kapealla näytöllä alakulman napista; kohdan tai ulkopuolen napautus sulkee sen | toc.js |
| Sisällysluettelo seuraa lukukohtaa (`toc.follow`); oma vierityspalkki vain osoittimella, häivytys ylä- ja alareunassa kertoo, että listaa on lisää | mkdocs-pohja.yml, layout.css, toc.js |
| Sivustovalikko kurssin nimen vieressä (`extra.sites`) | header.html, sitemenu.js/css |
| Leipätekstin kirjasin- ja kokovalikko: Source Serif 4, Atkinson Hyperlegible Next, Literata; koko 90–175 %, lukukohta pysyy paikallaan. Perustaso 10 % teeman kokoa suurempi (--jyu-text-base) | header.html, fontmenu.js/css, typography.css, fonts.css |
| Kirjasimet sivuston omasta `assets/fonts/`-hakemistosta, ei Google Fontsista: sivu näyttää samalta ilman verkkoa ja verkoissa, joista Googleen ei pääse, eikä lukijan osoite mene Googlelle; leipätekstin kirjasin esiladataan | fonts.css, main.html, `skriptit/fontit.py` |
| Vaalea ja tumma teema käyttöjärjestelmän mukaan, vaihdin yläpalkissa | mkdocs-pohja.yml |
| Haku; hakuikkunan teksti leipätekstin portaissa, kentän paikkamerkki "Hae", sulkunappi kenttärivin päässä (puhelimella ikkuna täyttää ruudun eikä Escapea tai taustaa ole) | search.js/css |
| Tulosta: koko kirja yhdeksi PDF:ksi | `build_print_page`, print.js/css |
| Alatunniste: edellinen/seuraava, tekijät ja lisenssi, "Muokkaa", "Muutoshistoria", "Ilmoita ongelma" | copyright.html |
| Alaviitteet ja `title`-attribuutit tooltipeinä | mkdocs-pohja.yml, typography.css |
| Koko sivun ääneenluku (`kirja.toml`: `[puhe] sivut`): kaiutin yläpalkissa, soitinpalkki (nopeus 1–2×, jää muistiin), luettava kappale korostettuna; koodista, taulukosta ja kaaviosta vain ilmoitus, välilehdistä lukijan valitsema | `speech_units`, `mark_speech`, puhe.js/css, header.html, `puhe.py` |
| Kuvan klikkaus avaa sen täysikokoisena (`kirja.toml`: `kuvasuurennus`, kokeilussa ohj2:ssa); kuvan saa pois merkinnällä `{ .off-glb }`. Mermaid-kaavio avautuu 1,5-kertaisena teeman väreissä. Vaiheittaisessa ohjeessa vaiheen kuvat ovat oma galleriansa, ja animaation varakuva ei avaudu | `build_base`, `mermaid_zoom`, Zensicalin GLightbox, diagrams.css, walkthrough.js |
| Taulukoiden, koodin ja nappirivin tyyli | tables.css, code.css, codebuttons.css |

### Ylläpito

| Ominaisuus | Toteutus |
| --- | --- |
| `./zensical/run.sh`: vahti, joka muuntaa tallennetun sivun ja päivittää selaimen | `convert.py --watch` |
| `--strict`: julkaisu kaatuu puuttuvaan kaavioon tai äänivarastoon | `convert.py`, kirjan pages.yml |
| Varoitukset: puuttuva `{{#include}}`-kohde, virheellinen visa, tuntematon korostusväri, väärin piirtyvä bob-kaavio, vanhentunut tai puuttuva ääni | `convert.py` |
| Ilmoitus piirretyistä ja poistetuista kaavioista: `cache/` on versionhallinnassa, joten ne pitää committoida (`--strict` ei piirrä) | `convert.py` (`report_diagrams`) |
| Tiedostoja pois sivuista, ääneenluku, linkkitarkistuksen TIM-kansiot | `kirja.toml` |
| Ulkoisten linkkien ja ankkurien tarkistus, myös kurssin TIM-sivuilta | `linkit/` |
| Testit koekirjalla ja kirjan omalla materiaalilla | `tests/`, `./zensical/run.sh test` |
| Kirjasintiedostojen päivitys hallitusti: `python3 skriptit/fontit.py` hakee lähteiden nykyiset tiedostot (Adoben perheillä skriptiin kiinnitetty tagi), ja muutos näkyy diffissä | `skriptit/fontit.py`, `assets/fonts/`, fonts.css |

## Rakenne

```
kirja/                     kirjan repo
  src/                     materiaali (mdBookin SUMMARY.md + sivut)
  zensical/                kirjan hakemisto
    kirja.toml             kirjan asetukset työkaluille
    mkdocs.yml             kirjan omat sivustoasetukset (nimi, tekijät, repo)
    run.sh                 kääre: tyokalut/run.sh
    cache/mermaid/         kirjan mermaid-kaaviot (versionhallinnassa)
    cache/svgbob/          kirjan bob-kaaviot (versionhallinnassa)
    cache/plantuml/        kirjan plantuml-luokkakaaviot (versionhallinnassa)
    puhe/                  ääneenluvun leikkeet: erillisen repon klooni (puhe.py),
                           .gitignoressa, EI submodule
    tyokalut/              TÄMÄ REPO submodulena
    docs/ site/ nav.yml .venv/   generoitua, ei versionhallinnassa
```

Työkalut eivät tiedä, missä kirjassa ollaan: `convert.py` etsii kirjan
hakemiston `kirja.toml`ista (ajohakemisto, muuten tämän hakemiston
ylähakemisto) ja lukee materiaalin sen viereisestä `src/`:stä.

| Tiedosto | Mitä |
| --- | --- |
| `convert.py` | `../src` → `docs/` ja `nav.yml`; `--watch` vahtii, `--strict` kaatuu puuttuvaan kaavioon (julkaisu) |
| `mermaid/` | mermaid-kaavioiden piirtäjä (`render.mjs`, Node-paketti beautiful-mermaid); `convert.py` asentaa paketit `npm ci`:llä tarvittaessa. Omat korjaukset piirtäjään ovat `patches/`:ssa (patch-package, `npm ci` ajaa ne): luokkakaaviossa yliluokka aliluokkiensa keskelle ja sen perintäviivat yhteisenä runkona (yksi kolmio, sen alla 10 px:n varsi). Kaavion nimi välimuistissa on lähteen ja piirtäjän (versiot, korjaukset, `render.mjs`) sha1, joten piirtäjän muutos piirtää kirjan kaaviot uudelleen |
| `mkdocs-pohja.yml` | kirjojen yhteiset Zensical-asetukset: teema, tyylit, skriptit |
| `assets/`, `overrides/`, `icons/` | tyylit ja skriptit, teeman mallit, kuvakkeiden glyfit |
| `assets/fonts/` | kirjasintiedostot (woff2) ja niiden lisenssit (OFL.txt) perheittäin: Source-perheet Adoben julkaisuista, muut Google Fontsista; `skriptit/fontit.py` hakee ne ja kirjoittaa `assets/css/fonts.css`:n |
| `puhe.py` | ääneenluvun leikkeet (Azure Speech) äänivarastoon, myös vaiheittaisen ohjeen vaiheiden; `--teksti` näyttää luettavan ja hinta-arvion |
| `run.sh`, `setup.sh` | ajo ja asennus kirjan hakemistosta käsin; `vaihe.sh` näyttää asennuksen etenemisen |
| `requirements.txt` | kiinnitetty Zensical-versio; `requirements-dev.txt` lisää testien riippuvuudet |
| `tests/` | testit ja koekirja (`tests/book/`) |
| `linkit/` | ulkoisten linkkien tarkistus (GitHub Action, lychee) |
| `skriptit/` | kaikkien kirjojen päivitys ja työkalujen kiinnitys (`pull-all.sh`, `pin-tools.sh`), ks. [Kaikki kirjat kerralla](#kaikki-kirjat-kerralla); kirjasintiedostojen haku ja päivitys (`fontit.py`) |
| `CLAUDE.md` | kirjojen yhteiset kirjoitusohjeet Claudelle |

## Kirjan asetukset: kirja.toml

Kaikki avaimet ovat valinnaisia; tiedoston pitää silti olla olemassa, koska
siitä kirjan hakemisto tunnistetaan.

| Avain | Merkitys | convert.py |
| --- | --- | --- |
| `nimi` | kirjan lyhyt nimi verkkopyyntöjen User-Agentiin (PlantUML, puhe.py) | `BOOK_NAME` |
| `ei_sivuja` | lista fnmatch-kuvioita `.md`-tiedostoille, joista ei tehdä sivua | `NOT_PAGES` |
| `kuvasuurennus` | `true`: kuvan ja mermaid-kaavion klikkaus avaa sen suurennettuna (GLightbox); oletus pois | `IMAGE_ZOOM` |
| `[testit] rikkinaiset_kuvat` | kuvat, joiden tiedetään puuttuvan (test_book.py sallii ne) | – |
| `[linkit] tim_kansiot` | TIM-kansiot, joiden julkisten sivujen linkit tarkistetaan (ks. Linkkitarkistus) | – |
| `[linkit] tim_pois` | tarkistuksesta pois jätettävät TIM-dokumentit (polku kuten kansioissa) | – |
| `[puhe] sivut` | fnmatch-kuviot lähdepuun sivuille, jotka luetaan ääneen (koko sivu) | `SPEECH_PAGES` |
| `[puhe] repo` | äänivaraston repo, jonka `puhe.py` kloonaa ja johon se pushaa leikkeet | `SPEECH_REPO` |
| `[puhe] varasto` | varaston klooni kirjan hakemistosta (oletus `puhe`); kirjan `.gitignore`issa, ei submodule | `SPEECH_STORE` |
| `[puhe] aani` | Azuren ääni (oletus `fi-FI-HarriNeural`); vaihto tekee kaikki leikkeet uudelleen | `SPEECH_VOICE` |

Esimerkki (ohj1):

```toml
nimi = "ohj1"
ei_sivuja = ["exercises/*/starter/*.md"]

[linkit]
tim_kansiot = ["kurssit/tie/itkp102"]
tim_pois = ["kurssit/tie/itkp102/materiaali/moniste"]

[puhe]
sivut = ["tyokalut.md", "osa1/*.md"]
repo = "https://github.com/ohj-perus-jy/ohj1-puhe.git"
```

Asetukset luetaan käynnistyessä: muutoksen jälkeen `run.sh` käynnistetään
uudelleen.

## Kirjan mkdocs.yml

Tähän kirjoitetaan kirjan omat tiedot. 

```yaml
INHERIT: nav.yml

site_name: Ohjelmointi 1
site_url: https://ohjelmointi1.it.jyu.fi/     # jos sivustolla on oma osoite
copyright: >-
  Ohjelmointi 1 -oppimateriaali &copy; ...
repo_url: https://github.com/ohj-perus-jy/ohj1

# Sivustovalikko kurssin nimen vieressä; ilman listaa valikkoa ei näy ja nimi
# on pelkkä linkki etusivulle. Kohta, jonka nimi on site_name, on tämä sivusto.
extra:
  sites:
    - name: Ohjelmointi 1
      url: https://ohjelmointi1.it.jyu.fi/
    - name: Jypeli-ohjeet
      url: https://jypeli.it.jyu.fi/
```

## Käyttö kirjassa

```bash
git clone --recurse-submodules <kirjan repo>    # tai kloonin jälkeen:
git submodule update --init                     # (kirjan run.sh tekee tämän itse)

./zensical/run.sh              # muunna, vahdi ../src:ää ja tarjoile portissa 8001
                               # (varattuna seuraavassa vapaassa, run.sh kertoo)
./zensical/run.sh 8003         # aloita portista 8003
./zensical/run.sh build        # pelkkä rakennus site/-hakemistoon
./zensical/run.sh test         # testit: koekirja ja tämä kirja
./zensical/run.sh puhe         # ääneenluvun puuttuvat leikkeet varastoon ja pushaus
./zensical/run.sh puhe ../src/sivu.md   # vain annettu sivu (myös vaiheittainen ohje)
./zensical/run.sh puhe --teksti         # luettavat tekstit ja hinta-arvio, ei ääniä
```

Ensimmäinen ajo asentaa `.venv`:n kirjan hakemistoon (`setup.sh`), ja `run.sh`
päivittää sen, kun `requirements.txt`:n Zensical-versio vaihtuu tai järjestelmän
Python päivittyy (esim. 3.12 → 3.14). Windowsissa
kloonaa kirja WSL:n levylle, ei Windowsin kansioon. Windowsin kansiosta
(9p-liitos) asennus on hidasta, eikä Zensicalin `--watch` toimi kunnolla. Jos ehdottomasti kuitenkin haluat käyttää Windowsin kansiota, joudut ajamaan `./zensical/run.sh` joka kerta uudelleen muokkauksen jälkeen. 

**Muokattava puu on `src/`, ei `docs/`**: `docs/` on kertakäyttöinen kopio.

`git pull` ei päivitä submodulea itsestään. Kertaalleen kloonissa:

```bash
git config submodule.recurse true
```

## Ääneenluku

Ääneenluku on oletuksena pois päältä: ilman `kirja.toml`:n `[puhe]`-taulukkoa
mitään sivua ei lueta, kaiutinta ei näy, eikä Azurea tai äänivarastoa
tarvita.  Käyttöönotto:

1. Luo Azure-portaalissa Speech-resurssi ja vie sen avain ja alue (sivulta
   *Keys and Endpoint*) ympäristömuuttujiin. Niitä tarvitsee vain se, joka
   tekee leikkeitä; käännös ja julkaisu eivät.

   ```bash
   export AZURE_SPEECH_KEY=...
   export AZURE_SPEECH_REGION=...     # resurssin alue, esim. westeurope
   ```

2. Luo äänivarastolle GitHubiin tyhjä **julkinen** repo, esim.
   `ohj-perus-jy/<kirja>-puhe`. Yksityistä repoa julkaisu ei näe.
3. Lisää `zensical/kirja.toml`:iin luettavat sivut ja varaston osoite (ks.
   Kirjan asetukset: kirja.toml). Kaikki sivut luetaan kuviolla
   `sivut = ["*"]`.

   ```toml
   [puhe]
   sivut = ["tyokalut.md", "osa1/*.md"]
   repo = "https://github.com/ohj-perus-jy/<kirja>-puhe.git"
   ```

4. Lisää kirjan `.gitignore`en rivi `zensical/puhe/`.
5. Tarkista luettava teksti ja hinta-arvio: `./zensical/run.sh puhe --teksti`.
   Kuviin kuvaava vaihtoehtoinen teksti, koska se luetaan ("Kuva: …").
6. Tee leikkeet: `./zensical/run.sh puhe`. Se kloonaa varaston kansioon
   `zensical/puhe/`, tekee leikkeet ja pushaa ne varastoon.
7. Käynnistä `./zensical/run.sh` uudelleen (asetukset luetaan käynnistyessä):
   valituilla sivuilla on nyt kaiutin yläpalkissa.
8. Lisää `pages.yml`:ään työkalujen checkoutin perään:

   ```yaml
         - uses: actions/checkout@v7
           with:
             repository: ohj-perus-jy/<kirja>-puhe
             path: zensical/puhe
             fetch-depth: 1
   ```

9. Committaa ja pushaa `kirja.toml`, `.gitignore` ja `pages.yml` vasta, kun
   leikkeet ovat varastossa (vaihe 6).

Leikkeet, myös vaiheittaisten ohjeiden, ovat erillisessä repossa
(`[puhe] repo`). Julkaisu (`pages.yml`) hakee sen omalla checkout-askeleellaan
kansioon `zensical/puhe/`.
Korjauksen jälkeen `puhe` tekee vain muuttuneiden kappaleiden leikkeet, ja
käännös varoittaa, jos jokin puuttuu. Sanan, jonka ääni sanoo väärin (C# "see
risuaita"), korjaus tulee `convert.py`:n `SPEECH_SAYINGS`iin.

Huomaa, että äänivarasto *ei* ole submodule.

Vaiheittainen ohje luetaan ääneen vain, jos sen
tagissa on `audio` (`<walkthrough scenes audio>`).

**Älä poista kansiota `zensical/puhe/`** ennen kuin olet varmistanut, että
leikkeet on pushattu (`git -C zensical/puhe status -sb`): pushaamaton leike
on maksettu Azurelle, eikä sitä ole muualla.

## Työkalujen muuttaminen

`zensical/tyokalut/` on tavallinen git-repo kirjan sisällä, joten muutos
tehdään paikan päällä sisältötyön lomassa:

```bash
cd zensical/tyokalut
git switch main && git pull          # submodule on oletuksena irrallisessa HEADissa
# ... muutos, ./run.sh test ...
git commit -am "..." && git push
cd ../..
git add zensical/tyokalut            # kirja kiinnittää uuden version
git commit -m "Työkalut: ..."
```

Uusi tyyli tai skripti lisätään `assets/`:iin ja `mkdocs-pohja.yml`:n listaan,
ei kirjan `mkdocs.yml`:ään.

Muut kirjat ja haarat saavat muutoksen päivittämällä osoittimen:

```bash
git -C zensical/tyokalut pull origin main
git add zensical/tyokalut && git commit -m "Työkalut: ..."
```

Jos kirjan osoittimen työntää ilman, että työkalucommit on työnnetty, kirjan
julkaisu kaatuu checkoutiin. Se on tarkoitus: unohdus näkyy heti.

Jos kirjan `pages.yml` kääntää useita haaroja (`main` ja `dev`), jokaisen
haaran pitää toimia samalla `pages.yml`:llä: rakenteen muutos viedään kaikkiin
käännettäviin haaroihin samalla kertaa.

### Kaikki kirjat kerralla

Kun kirjat ja tämä repo ovat kloonattuina samaan hakemistoon, `skriptit/`
hoitaa ne kaikki kerralla. Skriptit linkitetään tuohon yhteiseen hakemistoon,
koska ne käsittelevät hakemistoa, jossa niitä kutsutaan:

```bash
ln -s kirjatyokalut/skriptit/pull-all.sh kirjatyokalut/skriptit/pin-tools.sh .
./pull-all.sh                  # kaikki repot ajan tasalle, työkalut mainiin
./pin-tools.sh [kirja ...]     # kirjaan kiinnitetään työkalujen main (commit, ei pushia)
```

`pull-all.sh` kertoo, missä kirjassa kiinnitetty työkaluversio on eri kuin
main. `pin-tools.sh` tekee siitä kirjan nykyiseen haaraan commitin, jonka
viestiin tulevat työkalujen committien otsikot.

## Käyttöönotto uudessa kirjassa

Tarvitset:

- kirjan repon GitHubissa ja sen juuressa materiaalin mdBookin muodossa:
  `src/SUMMARY.md` ja sivut (pienin toimiva kirja: `tests/book/`)
- Linuxin tai WSL:n, jossa on git ja Python 3.11+
- valinnaisesti cargon, jolla `convert.py` asentaa bob-kaavioiden piirtäjän,
  ja Noden (npm), jolla se asentaa mermaid-kaavioiden piirtäjän

Tee kirjan juuressa:

1. Lisää työkalut submoduleksi:

   ```bash
   git submodule add https://github.com/ohj-perus-jy/kirjatyokalut.git zensical/tyokalut
   ```

2. Luo `zensical/kirja.toml` ([Kirjan asetukset](#kirjan-asetukset-kirjatoml)).
   Pelkkä nimi riittää alkuun:

   ```toml
   nimi = "ohj1"
   ```

3. Luo `zensical/mkdocs.yml` ([Kirjan mkdocs.yml](#kirjan-mkdocsyml)).
4. Luo `zensical/run.sh` ja tee siitä ajettava (`chmod +x zensical/run.sh`):

   ```bash
   #!/usr/bin/env bash
   set -euo pipefail
   cd "$(dirname "$0")"
   [[ -f tyokalut/run.sh ]] || git submodule update --init tyokalut
   # "+" = tyokalut/ on eri versiossa kuin kirja odottaa (git pull ei päivitä sitä).
   if git submodule status tyokalut | grep -q '^+'; then
       echo "huom: zensical/tyokalut on eri versiossa kuin kirja odottaa;" \
            "päivitä: git submodule update (tai committaa uusi versio)" >&2
   fi
   exec tyokalut/run.sh "$@"
   ```

5. Lisää `.gitignore`en:

   ```
   zensical/.venv*/
   zensical/docs/
   zensical/site/
   zensical/nav.yml
   zensical/.cache/
   zensical/.convert.lock
   zensical/puhe/
   ```

6. Lisää kirjan juuren `CLAUDE.md`:hen rivi `@zensical/tyokalut/CLAUDE.md`.
7. Kokeile: `./zensical/run.sh` ja avaa <http://localhost:8001>. Ensimmäinen
   ajo asentaa Zensicalin ja voi kysyä sudo-salasanaa.
8. Luo `.github/workflows/pages.yml`:

   ```yaml
   name: Deploy site to Pages
   on:
     push:
       branches: ["main"]
     workflow_dispatch:
   permissions:
     contents: read
     pages: write
     id-token: write
   concurrency:
     group: "pages"
     cancel-in-progress: false
   jobs:
     zensical:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v7
           with:
             submodules: true
         - uses: actions/setup-python@v7
           with:
             python-version: "3.11"
         - run: pip install -r zensical/tyokalut/requirements.txt
         - working-directory: zensical
           run: |
             python3 tyokalut/convert.py --strict
             zensical build
         - uses: actions/upload-pages-artifact@v5
           with:
             path: zensical/site
     deploy:
       needs: zensical
       runs-on: ubuntu-latest
       environment:
         name: github-pages
         url: ${{ steps.deployment.outputs.page_url }}
       steps:
         - id: deployment
           uses: actions/deploy-pages@v5
   ```

9. GitHubissa: *Settings* › *Pages* › *Source*: *GitHub Actions*. Oma domain
   asetetaan samassa näkymässä.
10. Committaa ja pushaa:

    ```bash
    git add .gitmodules .gitignore CLAUDE.md zensical .github
    git commit -m "Zensical-työkalut käyttöön"
    git push
    ```

Jos julkaiset myös `dev`-haaran `/dev/`:iin (malli: ohj1:n `pages.yml`), lisää
`dev` kohtaan *Settings* › *Environments* › *github-pages* › *Deployment
branches*. Ääneenluku otetaan käyttöön erikseen, ks. [Ääneenluku](#ääneenluku).

## Linkkitarkistus

`linkit/` on GitHub Action, joka tarkistaa lycheellä kirjan `src/`:n ulkoiset
linkit ankkureineen. Työnkulun pitää olla kirjan omassa
`.github/workflows/`:ssa (GitHub ei aja submodulen työnkulkuja), mutta se vain
kutsuu actionia, joten tarkistus päivittyy osoittimen mukana. Malliksi käy
ohj1:n `links.yml`; olennaiset askeleet:

```yaml
      - uses: actions/checkout@v7
        with:
          submodules: true
      - uses: ./zensical/tyokalut/linkit
```

Laukaisimen `paths`-listaan kuuluu myös `zensical/tyokalut`, ja viikoittainen
`schedule` löytää linkit, jotka rikkoutuvat ilman committeja.

Syötteellä `tim: true` action tarkistaa kirjan sijaan kurssin TIM-sivujen
linkit (esim. TIMin aikataulusta kirjaan): `linkit/tim_sivut.py` listaa
kirja.toml:n `[linkit]`-kansioiden julkiset dokumentit, ja lychee tarkistaa
niiden linkit. Se ajetaan omana työnään vain ajastettuna ja käsin, koska
TIM-sivut muuttuvat gitin ulkopuolella eikä TIMin virhe saa kaataa kirjan
pushia. Kaatuneesta ajastetusta ajosta GitHub lähettää sähköpostin sille, joka
viimeksi muutti `schedule`-riviä.

Kirjautumista vaativat sivut ja lisäosien (esim. koodilaatikon) sisällä olevat
linkit jäävät tarkistamatta. Jos sivun otsikko näkyy vain kirjautuneelle, sen
ankkuri ohitetaan kirjan `.lycheeignore`ssa.

Yhteiset asetukset ja ohitukset ovat `linkit/lychee.toml`:ssa, kirjan omat
ohitukset (regex, yksi per rivi) kirjan juuren `.lycheeignore`ssa. Ajo kaatuu
vain 404:stä, 410:stä, aikakatkaisusta ja yhteysvirheestä; 403, 429 ja 5xx
eivät kerro linkin kuolleen. Paikallisia linkkejä ei tarkisteta, koska
`{{#include}}`-liitosten polut ovat suhteessa liittävään sivuun, mitä lychee ei
tiedä. Absoluuttiset linkit kirjojen omiin sivustoihin tarkistetaan tuotantoa
vasten: sivu, joka julkaistaan samassa työnnössä, näkyy 404:nä, kunnes julkaisu
on valmis. Aja tarkistus silloin uudelleen.

## Testit

```bash
./zensical/run.sh test                        # kaikki
./zensical/run.sh test tests/test_convert.py  # pelkät muunnokset, alle 1 s
./zensical/run.sh test --nobuild              # käytä kirjan olemassa olevaa site/:ä
```

Mitään ei jäljitellä: testit ajavat `convert.py`:n ja `zensical build`in
oikeasti ja avaavat sivun oikeassa selaimessa (Playwright). Koekirja
(`tests/book/`: `src/` ja `zensical/` kuten oikeassa kirjassa) kopioidaan
väliaikaishakemistoon työkalujen kanssa samaan rakenteeseen kuin kirjan
repossa. `tests/test_book.py` kääntää sen kirjan, jonka submodulena työkalut
ovat, ja ohittaa ominaisuudet, joita kirja ei käytä.

Tässä repossa yksinään (`./run.sh test`) ajetaan vain koekirjan testit;
`test_book.py` ohitetaan. Sama ajo on GitHub Actionsissa joka pushilla
(`.github/workflows/testit.yml`).

`tests/test_convert.py` kiinnittää kirjan asetukset fixturella
(`page_config`), joten tulos ei riipu siitä, minkä kirjan `kirja.toml` on
luettu.
