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
ei tarvita. ohj1:stä ja jypelidocsista se on poistettu kokonaan; ohj2:n `main`
julkaistaan vielä mdBookilla ja `dev` Zensicalilla.

- Miksi mikin ratkaisu on tehty: [PERUSTELUT.md](PERUSTELUT.md).
- Mitä ominaisuuksia on ja mistä ne tulivat: [TAUSTA.md](TAUSTA.md).
- Yhtenäistämisen tilanne ja avoimet asiat: [YHTENAISTYS.md](YHTENAISTYS.md).

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
| `tests/` | testit ja koekirja (`tests/book/`) |
| `linkit/` | ulkoisten linkkien tarkistus (GitHub Action, lychee) |

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

Esimerkki (ohj1):

```toml
nimi = "ohj1"
ei_sivuja = ["exercises/*/starter/*.md"]

[siirrot]
"tenttiohjeet.md" = "tentti.md"
"git-ht-ohje.md" = "git.md"

[poistettavat_osiot]
"index.md" = "Navigointi tässä materiaalissa"
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

Ensimmäinen ajo asentaa `.venv`:n kirjan hakemistoon (`setup.sh`).
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

Lisäksi `zensical/kirja.toml`, `zensical/mkdocs.yml` (yllä), `.gitignore`iin
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

`convert.py` tarvitsee vain standardikirjaston (Python 3.11+, `tomllib`).
Kaaviot ovat kirjan versionhallinnassa (`cache/`), joten julkaisu ei tarvitse
svgbobia eikä PlantUML-palvelinta; `--strict` kaataa ajon, jos jokin puuttuu.
Paikallisesti `convert.py` asentaa puuttuvan `svgbob_cli`:n cargolla, kun uusi
tai muuttunut bob-kaavio sitä tarvitsee.

## Linkkitarkistus

`linkit/` on GitHub Action, joka tarkistaa kirjan `src/`:n ulkoiset linkit
lycheellä. Työnkulun pitää olla kirjan omassa `.github/workflows/`:ssa (GitHub
ei aja submodulen työnkulkuja), mutta se vain kutsuu actionia, joten action
päivittyy osoittimen mukana kuten muutkin työkalut:

```yaml
name: Check external links

on:
  push:
    branches: ["main", "dev"]
    paths: ["src/**", ".lycheeignore", ".github/workflows/links.yml", "zensical/tyokalut"]
  pull_request:
    paths: ["src/**", ".lycheeignore", ".github/workflows/links.yml", "zensical/tyokalut"]
  # Linkit rikkoutuvat ilman committejakin. Ajetaan vain oletushaarassa.
  schedule:
    - cron: "0 5 * * 1"
  workflow_dispatch:

permissions:
  contents: read

jobs:
  lychee:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          submodules: true
      - uses: ./zensical/tyokalut/linkit
```

Yhteiset asetukset ovat `linkit/lychee.toml`:ssa:

- Ajo kaatuu vain 404:stä ja 410:stä. 403 (esim. TIMin kirjautumista
  vaativat sivut), 429 ja 5xx hyväksytään, koska ne eivät kerro linkin
  kuolleen. Aikakatkaisu ja yhteysvirhe kaatavat ajon (3 uusintaa, 30 s).
- Vain ulkoiset linkit (`^file://` ohitetaan). Paikalliset polut ovat
  `{{#include}}`-liitosten takia suhteessa liittävään sivuun, mitä lychee ei
  tiedä; `--root-dir src` tekee `/`-alkuisista poluista paikallisia, jotta
  nekin ohitetaan eivätkä kaada ajoa.
- `src/SUMMARY.md` ohitetaan: sen `[nimi<url>]()`-ulkolinkki näyttää
  lycheelle tyhjältä URLilta.

Kirjan omat ohitukset (regex, yksi per rivi) ovat kirjan juuren
`.lycheeignore`ssa; lychee lisää ne yhteisten päälle.

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
