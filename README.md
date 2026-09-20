# kirjatyokalut

Ohjelmointikurssien kirjojen ([ohj1](https://github.com/ohj-perus-jy/ohj1),
[ohj2](https://github.com/ohj-perus-jy/ohj2),
[jypelidocs](https://github.com/ohj-perus-jy/jypelidocs)) yhteinen
työkaluketju: mdBook-murteella kirjoitettu `src/` muunnetaan
[Zensical](https://zensical.org)-sivustoksi. Kirja käyttää tätä repoa
git-submodulena, joten jokainen kirja ja haara kiinnittää oman versionsa, ja
korjaus tehdään yhteen paikkaan.

Merkkaus on mdBookin (`SUMMARY.md`, `{{#include}}`, `> [!VINKKI]`, `//-`-piilorivit
ym.), koska kirjat kirjoitettiin alun perin mdBookille, mutta mdBookia itseään
ei tarvita: se on poistettu kaikista kirjoista (viimeisenä ohj2:sta 2026-09-20).

- Miksi mikin ratkaisu on tehty: [PERUSTELUT.md](PERUSTELUT.md).
- Mitä työkalut tarjoavat: [Ominaisuudet](#ominaisuudet) alla.
- Mistä ominaisuudet tulivat (koeputken vanha README): [TAUSTA.md](TAUSTA.md).
- Miten työkalut yhtenäistettiin (valmis 2026-09-18) ja avoimet kysymykset:
  [YHTENAISTYS.md](YHTENAISTYS.md).

## Ominaisuudet

Jokainen ominaisuus on kaikkien kirjojen käytössä: kirja ottaa sen käyttöön
kirjoittamalla merkinnän `src/`:ään. Toteutus-sarakkeen funktiot ovat
`convert.py`:ssä ja tiedostot `assets/`:ssa tai `overrides/partials/`:ssa.

### Merkkaus: mitä `src/`:ään voi kirjoittaa

| Merkintä | Tulos | Toteutus |
| --- | --- | --- |
| `SUMMARY.md` | navigaatio: osat, numeroidut luvut, osan otsikko linkkinä osan etusivulle | `build_nav` |
| `{{#include tiedosto}}` | tiedoston sisältö tai valitut rivit paikalleen | `convert_includes` |
| `> [!VINKKI]` ym. | värillinen laatikko: Osaamistavoitteet, Huomautus, Vinkki, Tärkeää, Varoitus, Todo, WIP; oppaiden merkinnät Kokeile, Ei toimi vielä, Kysymys | `convert_alerts`, admonitions.css |
| `<details>`, `<summary>` | avattava osio, jonka sisällä Markdown toimii | `convert_details` |
| `<task>`, `<task-title num>`, `<points>`, `<handout>`, `<task-link>` | tehtäväkortti: numero, pisteet, tehtävänanto; bonusmerkki | `convert_tasks`, `convert_bonus_marks`, tasks.css |
| `<div class="ht-reqs">` | harjoitustyön vaatimuslohko, numerointi 1.1, 1.2, … | `convert_divs`, requirements.css |
| `<visa>`, `<vaittama vastaus>`, `<kysymys>`, `<perustelu>` | Testaa tietosi -visa: valinta paljastaa vastauksen ja perustelun, vastaukset muistetaan selaimessa | `convert_quizzes`, visa.js/css |
| `### [Windows](#tab/win)` | käyttöjärjestelmävälilehdet; valinta pätee koko sivustolla ja muistetaan | `convert_tabs` |
| `<walkthrough scenes>`, `<step scene>` | vaiheittainen ohje: animoitu kohtaus askel kerrallaan, halutessa ääneen luettuna (`puhe.py`) | `convert_walkthroughs`, walkthrough.js/css |
| `<animation scenes scene>` | yksittäinen animaatio tavallisella sivulla; tahti `data-wait`, `data-type` | `convert_animations` |
| `<asciinema>` | terminaalinauhoitus soittimessa; soitin ladataan vain sivuille, joilla on nauhoitus | asciinema.js |
| ` ```plantuml `, ` ```bob `, ` ```mermaid ` | luokkakaavio kuvana, ascii-kaavio upotettuna SVG:nä, mermaid sellaisenaan; kaaviot kirjan `cache/`:ssa | `convert_plantuml`, `convert_svgbob`, diagrams.css |
| `<i class="bi …">`, `<i class="fa …">` | kuvake teeman glyfinä; valikkopolun nuoli merkkinä › | `convert_icons`, `icons/`, icons.css |
| `[teksti](#käyttö)` | ankkuri ilman ääkkösiä, sama muoto kuin teeman otsikkotunnuksissa | `convert_anchors` |

### Koodilohkot

Kielet: `csharp`, `java`, `javascript` (korostetut rivit: `csharp`, `java`).

| Merkintä | Tulos | Toteutus |
| --- | --- | --- |
| ` ```csharp ` | ajonappi: koodi ajetaan palvelimella, tuloste lohkon alle; Jypelin ikkuna kuvana | playground.js/css |
| `,ignore`, `,noplayground` | ei ajonappia, väritys säilyy | `convert_fences` |
| `,feature-jypeli` | ajo Jypeli-kirjaston kanssa (`csharp-jypeli`) | playground.js |
| `,editable` | lukija voi muuttaa koodia sivulla ja ajaa sen; "Peruuta muutokset" | playground.js |
| `//-` rivin alussa | piilorivi: ei näy, menee ajoon; silmänappi näyttää | `hide_lines`, hidelines.js/css |
| `// HIGHLIGHT_GREEN_BEGIN` … `_END` | korostetut rivit: green, yellow, red, blue | `mark_highlights`, highlights.js/css |
| `// FILE: Nimi.java` | monitiedostolohko: tiedosto per välilehti, ajetaan yhdessä | `convert_files` |

### Sivusto: mitä lukija saa

| Ominaisuus | Toteutus |
| --- | --- |
| Valikko kiinteänä kiskona, luvun avaus vierittää valikon kohdalleen | layout.css, nav-scroll.js |
| Sivustovalikko kurssin nimen vieressä (`extra.sites`) | header.html, sitemenu.js/css |
| Leipätekstin kirjasinvalikko: Source Serif 4, Atkinson Hyperlegible Next, Literata | header.html, fontmenu.js/css, typography.css |
| Vaalea ja tumma teema käyttöjärjestelmän mukaan, vaihdin yläpalkissa | mkdocs-pohja.yml |
| Haku; hakuikkunan teksti leipätekstin portaissa | search.js/css |
| Tulosta: koko kirja yhdeksi PDF:ksi | `build_print_page`, print.js/css |
| Alatunniste: edellinen/seuraava, tekijät ja lisenssi, "Ehdota muutosta", "Ilmoita ongelmasta" | copyright.html |
| Alaviitteet ja `title`-attribuutit tooltipeinä | mkdocs-pohja.yml |
| Taulukoiden, koodin ja nappirivin tyyli | tables.css, code.css, codebuttons.css |

### Ylläpito

| Ominaisuus | Toteutus |
| --- | --- |
| `./zensical/run.sh`: vahti, joka muuntaa tallennetun sivun ja päivittää selaimen | `convert.py --watch` |
| `--strict`: julkaisu kaatuu puuttuvaan kaavioon | `convert.py`, kirjan pages.yml |
| Varoitukset: puuttuva `{{#include}}`-kohde, virheellinen visa, tuntematon korostusväri, väärin piirtyvä bob-kaavio, vanhentunut ääni | `convert.py` |
| Sivu toisen alasivuksi, tiedostoja pois sivuista, osioita pois | `kirja.toml` |
| Ulkoisten linkkien ja ankkurien tarkistus, myös kurssin TIM-sivuilta | `linkit/` |
| Testit koekirjalla ja kirjan omalla materiaalilla | `tests/`, `./zensical/run.sh test` |

## Rakenne

```
kirja/                     kirjan repo
  src/                     materiaali (mdBookin SUMMARY.md + sivut)
  zensical/                kirjan hakemisto
    kirja.toml             kirjan asetukset työkaluille
    mkdocs.yml             kirjan omat sivustoasetukset (nimi, tekijät, repo)
    run.sh                 kääre: tyokalut/run.sh
    cache/svgbob/          kirjan bob-kaaviot (versionhallinnassa)
    cache/plantuml/        kirjan luokkakaaviot (versionhallinnassa)
    tyokalut/              TÄMÄ REPO submodulena
    docs/ site/ nav.yml .venv/   generoitua, ei versionhallinnassa
```

Työkalut eivät tiedä, missä kirjassa ollaan: `convert.py` etsii kirjan
hakemiston `kirja.toml`ista (ajohakemisto, muuten tämän hakemiston
ylähakemisto) ja lukee materiaalin sen viereisestä `src/`:stä.

| Tiedosto | Mitä |
| --- | --- |
| `convert.py` | `../src` → `docs/` ja `nav.yml`; `--watch` vahtii, `--strict` kaatuu puuttuvaan kaavioon (julkaisu) |
| `mkdocs-pohja.yml` | kirjojen yhteiset Zensical-asetukset: teema, tyylit, skriptit |
| `assets/`, `overrides/`, `icons/` | tyylit ja skriptit, teeman mallit, kuvakkeiden glyfit |
| `puhe.py` | vaiheittaisen ohjeen äänet (Azure Speech) |
| `run.sh`, `setup.sh` | ajo ja asennus kirjan hakemistosta käsin |
| `requirements.txt` | kiinnitetty Zensical-versio; `requirements-dev.txt` lisää testien riippuvuudet |
| `tests/` | testit ja koekirja (`tests/book/`) |
| `linkit/` | ulkoisten linkkien tarkistus (GitHub Action, lychee) |
| `CLAUDE.md` | kirjojen yhteiset kirjoitusohjeet Claudelle |

## Kirjan asetukset: kirja.toml

Kaikki avaimet ovat valinnaisia; tiedoston pitää silti olla olemassa, koska
siitä kirjan hakemisto tunnistetaan.

| Avain | Merkitys | convert.py |
| --- | --- | --- |
| `nimi` | kirjan lyhyt nimi verkkopyyntöjen User-Agentiin (PlantUML, puhe.py) | `BOOK_NAME` |
| `ei_sivuja` | lista fnmatch-kuvioita `.md`-tiedostoille, joista ei tehdä sivua | `NOT_PAGES` |
| `[siirrot]` | etulinkki toisen alle: `"tenttiohjeet.md" = "tentti.md"` | `NEST_UNDER` |
| `[poistettavat_osiot]` | sivulta pois jätettävä osio: `"index.md" = "Osion otsikko"` | `DROP_SECTIONS` |
| `[testit] rikkinaiset_kuvat` | kuvat, joiden tiedetään puuttuvan (test_book.py sallii ne) | – |
| `[linkit] tim_kansiot` | TIM-kansiot, joiden julkisten sivujen linkit tarkistetaan (ks. Linkkitarkistus) | – |
| `[linkit] tim_pois` | tarkistuksesta pois jätettävät TIM-dokumentit (polku kuten kansioissa) | – |

Esimerkki (ohj1):

```toml
nimi = "ohj1"
ei_sivuja = ["exercises/*/starter/*.md"]

[siirrot]
"tenttiohjeet.md" = "tentti.md"
"git-ht-ohje.md" = "git.md"

[poistettavat_osiot]
"index.md" = "Navigointi tässä materiaalissa"

[linkit]
tim_kansiot = ["kurssit/tie/itkp102"]
tim_pois = ["kurssit/tie/itkp102/materiaali/moniste"]
```

Asetukset luetaan käynnistyessä: muutoksen jälkeen `run.sh` käynnistetään
uudelleen.

## Kirjan mkdocs.yml

Kirjan tiedostossa on vain kirjan omat rivit. Yhteiset asetukset
(`mkdocs-pohja.yml`) ja navigaatio tulevat `nav.yml`:stä, jonka `convert.py`
kirjoittaa joka ajolla; kirjan oma arvo voittaa pohjan.

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

Uusi tyyli tai skripti lisätään `assets/`:iin ja `mkdocs-pohja.yml`:n listaan,
ei kirjan tiedostoon.

## Käyttö kirjassa

```bash
git clone --recurse-submodules <kirjan repo>    # tai kloonin jälkeen:
git submodule update --init                     # (kirjan run.sh tekee tämän itse)

./zensical/run.sh              # muunna, vahdi ../src:ää ja tarjoile portissa 8001
./zensical/run.sh 8003         # eri portti
./zensical/run.sh build        # pelkkä rakennus site/-hakemistoon
./zensical/run.sh test         # testit: koekirja ja tämä kirja
./zensical/run.sh puhe ../src/sivu.md   # vaiheittaisen ohjeen äänet
```

Ensimmäinen ajo asentaa `.venv`:n kirjan hakemistoon (`setup.sh`). Kun
`requirements.txt`:n Zensical-versio vaihtuu, olemassa oleva `.venv` ei päivity
itsestään: aja `zensical/tyokalut/setup.sh`.
**Muokattava puu on `src/`, ei `docs/`**: `docs/` on kertakäyttöinen kopio.

`git pull` ei päivitä submodulea itsestään. Kertaalleen kloonissa:

```bash
git config submodule.recurse true
```

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

## Käyttöönotto uudessa kirjassa

```bash
git submodule add https://github.com/ohj-perus-jy/kirjatyokalut.git zensical/tyokalut
```

Lisäksi `zensical/kirja.toml`, `zensical/mkdocs.yml` (yllä), kirjan juuren
`CLAUDE.md`:hen rivi `@zensical/tyokalut/CLAUDE.md`, `.gitignore`iin
`zensical/.venv*/`, `zensical/docs/`, `zensical/site/`, `zensical/nav.yml`,
`zensical/.cache/`, `zensical/.convert.lock`, ja kääre `zensical/run.sh`:

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

Julkaisu (`.github/workflows/pages.yml`): checkoutiin `submodules: true`,
ja käännös kirjan hakemistossa:

```yaml
      - uses: actions/checkout@v4
        with:
          submodules: true
      # ...
      - run: pip install -r zensical/tyokalut/requirements.txt
      - working-directory: zensical
        run: |
          python3 tyokalut/convert.py --strict
          zensical build
```

`convert.py` tarvitsee vain standardikirjaston (Python 3.11+, `tomllib`), ja
kaaviot tulevat kirjan `cache/`:sta, joten julkaisu ei tarvitse svgbobia eikä
PlantUML-palvelinta. Paikallisesti `convert.py` asentaa puuttuvan
`svgbob_cli`:n cargolla, kun uusi tai muuttunut bob-kaavio sitä tarvitsee.

## Linkkitarkistus

`linkit/` on GitHub Action, joka tarkistaa lycheellä kirjan `src/`:n ulkoiset
linkit ankkureineen. Työnkulun pitää olla kirjan omassa
`.github/workflows/`:ssa (GitHub ei aja submodulen työnkulkuja), mutta se vain
kutsuu actionia, joten tarkistus päivittyy osoittimen mukana. Malliksi käy
ohj1:n `links.yml`; olennaiset askeleet:

```yaml
      - uses: actions/checkout@v4
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
tiedä.

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
