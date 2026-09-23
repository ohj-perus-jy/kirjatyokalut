# Työkalujen yhtenäistäminen: valmis 2026-09-18

Tavoite: `zensical/`-työkalut (convert.py, puhe.py, assets, overrides, testit)
ovat yksi kopio tässä repossa, ja kirjat (ohj1, ohj2, jypelidocs) käyttävät
sitä git-submodulena polussa `zensical/tyokalut/`. Tavoite on saavutettu, ja
tämä tiedosto on sen historia: myöhemmät työkalumuutokset näkyvät git-lokista ja
ominaisuudet [README.md](README.md):stä. Auki ovat vain "Avoimet kysymykset".
Kirjojen tila tarkistettu viimeksi 2026-09-23.

Kopiot (tilanne 2026-09-18): **o1r** = ohj1 `rakenne-2027`, **o1d** = ohj1
`dev` = `main` (tuotanto), **o2** = ohj2 `dev` (2026-09-20 alkaen myös
`main`, tuotanto), **jy** = jypelidocs `main` (= `dev`).

Merkit: ✔ on, ✘ puuttuu, – ei koske.

## Vaihe 1 — erot umpeen käsin: VALMIS 2026-09-18

| # | Asia | o1r | o1d | o2 | jy |
|---|---|---|---|---|---|
| 1 | Testaa tietosi -visa (`convert_quizzes`, visa.css/js) | ✔ | ✔ | ✔ | ✔ |
| 2 | Oppaiden merkinnät (Kokeile, Ei toimi vielä, Kysymys) | ✔ | ✔ | ✔ | ✔ |
| 3 | Vaiheittainen ohje, animaatiot, puhe.py | ✔ | ✔ | ✔ | ✔ |
| 4 | `convert.py --strict`, `FAILED.add("plantuml")`, pages.yml | ✔ | ✔ | ✔ | ✔ |
| 5 | `svgbob_fit_text`, `svgbob_problems` | ✔ | ✔ | ✔ | ✔ |
| 6 | Valikoiden välkyntä pois (fontmenu, sitemenu, layout) | ✔ | ✔ | ✔ | ✔ |
| 7 | Hakuikkunan tyyli (search.css/js, test_search.py) | ✔ | ✔ | ✔ | ✔ |
| 8 | Sivustovalikon koodi (sitemenu.css/js, header.html) | ✔ | ✔ | ✔ | ✔ |
| 9 | Luvun avausnuoli alas/ylös kaikilla leveyksillä (layout.css) | ✔ | ✔ | ✔ | ✔ |
| 10 | Taulukon teksti leipätekstin kokoiseksi (tables.css) | ✔ | ✔ | ✔ | ✔ |
| 11 | Ajonappi: C#, `feature-`-määre, kuvatuloste (playground.js/css) | ✔ | ✔ | ✔ | ✔ |
| 12 | Kielilistat ja `ICON_MAP` ylijoukoksi, kommentit samoiksi | ✔ | ✔ | ✔ | ✔ |

`diff -rq` kopioiden välillä (2026-09-18) näyttää enää nämä:

- convert.py: `NEST_UNDER` ja `DROP_SECTIONS` (molemmat poistettu 21.9.2026),
  `NOT_PAGES`, `PLANTUML_AGENT`
- puhe.py: User-Agent; run.sh: esimerkkisivun nimi kommentissa
- mkdocs.yml: `site_name`, `site_url`, `copyright`, `repo_url`, `extra.sites`
  (ohj2:ssa ei listaa, joten valikkoa ei näy; nimi on linkki etusivulle)
- testit, jotka riippuvat edellisistä: test_convert.py (fixture o2:ssa ja
  jy:ssä), test_book.py, test_sitemenu.py (puuttuu o2:sta)
- ohj2:n `assets/plantuml/` (kirjan sisältöä)
- dokumentit: README, PERUSTELUT, KAYTTOONOTTO, PURKUSUUNNITELMA, tämä tiedosto

o1r ja o1d ovat työkaluiltaan tavulleen samat (ero vain tämä tiedosto).

## Vaiheet 2–3 — työkalut irti kirjasta: VALMIS 2026-09-18

Tehty kerran tässä repossa (päätös 2026-09-18), puhdas aloituscommit o1r:n
työkaluista, historia jäi ohj1:een.

- [x] aloituscommit: o1r:n `zensical/` ilman kirjan omia tiedostoja (`b8a10ef`)
- [x] `kirja.toml` + lataus `tomllib`illa; vakioiden nimet säilyvät (`4093bd4`)
- [x] puhe.py:n User-Agent asetuksista (`nimi`)
- [x] polut kahtia: työkalut (`TOOL`) ja kirja (`BOOK`); kirja löytyy
      `kirja.toml`ista (ajohakemisto, muuten työkalujen ylähakemisto)
- [x] PlantUML-kuvat kirjan `cache/plantuml/`:iin
- [x] `mkdocs-pohja.yml` → generoitu `nav.yml`; kirjan mkdocs.yml:ään jäävät
      `site_name`, `site_url`, `copyright`, `repo_url`, `extra.sites`
- [x] koekirjalle oma `zensical/kirja.toml` ja `mkdocs.yml`; test_sitemenu.py
      ja test_convert.py samat kaikille, test_book.py lukee kirjan poikkeukset
      asetuksista (`[testit] rikkinaiset_kuvat`)
- [x] run.sh ja setup.sh toimivat kirjan hakemistosta käsin
- [x] `SVGBOB_CHAR_WIDTH` 8,4 → 8 (`4806372`)
- [x] `svgbob_problems`: soikio `( -148)` ei varoita (`1303d5f`)
- [x] README uusiksi, vanha talteen TAUSTA.md:ksi (`84804b9`)
- [x] oma CI: testit koekirjalla joka pushilla (`b06361a`)

Todennus: ohj1, ohj2 ja jypelidocs käännettynä vanhalla rakenteella ja
uudella (työkalut `zensical/tyokalut/`:ssa, commit `4093bd4`) tuottivat
tavulleen saman `docs/`:n ja `site/`:n (213, 580 ja 259 tiedostoa).
Merkkileveyden korjauksen jälkeen ero on vain muutaman bob-kaavion leveys
(esim. 133 → 128 px); selaimessa tarkistettu, että kaikkien 24 kaavion teksti
mahtuu kuvaan.

## Vaihe 4 — kirjat submoduleen (`zensical/tyokalut/`): VALMIS 2026-09-18

- [x] jypelidocs `main` ja `dev` (`d4ae629`), julkaisu onnistui
- [x] ohj1 `rakenne-2027` (`7f5d7ca`)
- [x] ohj2 `dev` (`3f695b3`) ja `main`in pages.yml (`dc34b7e`), koska sekin
      kääntää `dev`in
- [x] ohj1 `dev` + `main` (`ed8575d`, merge `e0aeb96`)
- [x] joka kirjassa: `kirja.toml`, karsittu mkdocs.yml, kääre `run.sh`,
      pages.yml `submodules: true` ja uudet polut, vanhat kopiot pois, kirjan
      README:ssä vain kirjan oma osa
- [x] ohj2: `assets/plantuml/` → `cache/plantuml/`
- [x] ohj2:n KAYTTOONOTTO.md: "korjaukset viedään käsin molempiin" päättyi

Jokaisesta kirjasta on ennen siirtoa käännetty vertailusivusto vanhalla
rakenteella: ero on vain bob-kaavioiden leveys (korjaus `4806372`). Testit
submodulen kautta: jypelidocs 322, ohj1 `rakenne-2027` 323, ohj1 `dev` 322,
ohj2 325 läpi.

## Jatkossa

- Työkalumuutos tehdään tähän repoon (README: "Työkalujen muuttaminen") ja
  kirjat päivittävät osoittimen. Jokainen haara kulkee siis perässä, kunnes
  sen osoitin päivitetään. Osoitin päivitetään käytännössä kirjan `main`iin:
  2026-09-23 kaikkien kolmen kirjan `main` on tämän repon uusimmassa
  (`ac32f1e`), mutta `dev`-haarat ovat jäljessä (ohj1 `dev` ja `rakenne-2027`
  `f63fd1f`, ohj2 `dev` `4dad3fd`, jypelidocs `dev` `c43903d`).
- Kirjojen `git pull` ei päivitä submodulea: `git config submodule.recurse true`
  joka kloonissa; kirjan `run.sh` huomauttaa eri versiosta.
- Kirjojen devcontainer hakee submodulen ja ajaa `setup.sh`:n
  (`postCreateCommand`); muualla `run.sh` hoitaa molemmat ensimmäisellä ajolla.
- Sivustovalikko (`extra.sites`) on ohj1:ssä ja jypelidocsissa. ohj2:een sitä
  ei tule (päätös 2026-09-20): kurssin nimi on siellä linkki etusivulle.
- `dev`-haarat ja `/dev/`-esikatselu pidetään (päätös 2026-09-23), vaikka
  muutokset ja osoittimen päivitykset menevät nyt ensin `main`iin.

## Avoimet kysymykset

- Merkinnän otsikko "Kokeile käynnistää pelisi" on Jypeli-sanastoa; ohj2:ssa
  outo. Yleisempi oletus vai kirjan oma otsikko `kirja.toml`issa?
- LICENSE puuttuu tästä reposta.

## Havainnot

- jypelidocsin `dev`-työntöjen `deploy` kaatui 16.–18.9.2026 joka kerta
  (käännös onnistui); 18.9. klo 13.51 ajosta `00a7a68` alkaen se menee läpi.
- Ajonappi: palvelin ajaa Javan ilman `multifile`-kenttää (kokeiltu
  2026-09-18), joten ohj1:n playground.js kävi ohj2:een sellaisenaan.
- Testit kääntävät koekirjan repon omalla mkdocs.yml:llä (`copy_book`), joten
  test_sitemenu.py riippuu kirjan `site_name`sta ja `extra.sites`-listasta.
- Kaikkien kolmen kirjan pages.yml kääntää samalla ajolla sekä `main`in
  (juureen) että `dev`in (`/dev/`:iin); ohj2:ssa näin 2026-09-20 alkaen
  (ohj2 `f2c6594`). Kumpikin haara käännetään omalla työkaluosoittimellaan
  mutta `main`in pages.yml:n komennoilla. jypelidocsissa `--strict` kaatoi
  julkaisun 2026-09-18, koska `dev`in vanha convert.py ei tuntenut lippua;
  korjaantui, kun `dev` pikakelattiin `main`iin. Kun työkalujen käyttötapa
  (komentorivi, polut) muuttuu, jokaisen haaran, jonka pages.yml kääntää,
  pitää siirtyä samalla kertaa. Pelkkä osoittimen päivitys `main`iin ei kaada
  `dev`in käännöstä: 2026-09-23 kaikkien kirjojen julkaisu menee läpi, vaikka
  `dev`-haarat ovat jäljessä.

## Päiväkirja

| Pvm | Mitä | Commitit |
|---|---|---|
| 2026-09-18 | visa → o2, jy | ohj2 `dev`, jypelidocs `15a656c` |
| 2026-09-18 | merkinnät → o1r, o1d, o2 | ohj1 `e195fd6`, `c5201f6`; ohj2 `e25fc4a` |
| 2026-09-18 | vaiheittainen ohje + puhe.py → o2 | ohj2 `50eb16d` |
| 2026-09-18 | `--strict` → o2, jy | ohj2 `99ebba9`, jypelidocs `cf6edd1` |
| 2026-09-18 | svgbob-korjaukset → o2, jy | ohj2 `ed1c32b`, jypelidocs `520c2a0` |
| 2026-09-18 | haku + välkyntä pois → o1r (poimittu devistä) | ohj1 `0499d89`, `3e4f981` |
| 2026-09-18 | välkyntä pois → o2 (rinnakkainen istunto) | ohj2 `71e2560` |
| 2026-09-18 | sivustovalikon koodi, ajonappi, taulukot, nuoli, kielilistat → o2 | ohj2 `81d2093` |
| 2026-09-18 | visa + svgbob-korjaukset → o1d (tuotanto) | ohj1 `3167de3`, `7d39912` |
| 2026-09-18 | jypelidocsin julkaisu kaatui `--strict`iin, `dev` pikakelattu | jypelidocs `dev` = `520c2a0` |
| 2026-09-18 | kirjatyokalut-repo: aloitus, kirja.toml + polkujako + pohja, README, CI, bob-korjaukset | `b8a10ef`…`1303d5f` |
| 2026-09-18 | jypelidocs submoduleen (`main` + `dev`) | jypelidocs `d4ae629` |
| 2026-09-18 | ohj1 `rakenne-2027` submoduleen | ohj1 `7f5d7ca` |
| 2026-09-18 | ohj2 `dev` submoduleen, `main`in pages.yml | ohj2 `3f695b3`, `dc34b7e` |
| 2026-09-18 | ohj1 `dev` + `main` submoduleen | ohj1 `ed8575d`, `e0aeb96` |
| 2026-09-18 | juuren README:t: ohj1 Zensicalille (mdBook pois), jypelidocs ja ohj2 submodulen ohjeet | ohj1 `59c9b59`, `d65348b`; jypelidocs `00a7a68`; ohj2 `2887ff6` |
| 2026-09-18 | mdBook pois ohj1:n kaikista haaroista (`book.toml`, `theme/`, `highlight/`, `mermaid/`, `start.sh`, VS Coden tehtävät → Zensical, devcontainerin portti 3000, Rust-pohjan .gitignore) ja jypelidocsista (.gitignore, kommentit) | ohj1 `a560b8c`, `3866ca7`, merge `6ac6f69`; jypelidocs `49bec2c` |
| 2026-09-20 | ohj2 `main` Zensicalille, mdBook pois viimeisestäkin kirjasta | ohj2 `0c9d8de` |
| 2026-09-20 | README:hen ominaisuusluettelo; tämä tiedosto suljettu | `c92f4be` |
| 2026-09-20 | ohj2:een ei tule sivustovalikkoa (päätös) | `f63fd1f` |
| 2026-09-21 | kirjakohtaiset poikkeukset pois: mdBookin navigointiosio poistettu lähteistä (`DROP_SECTIONS` pois), tentti/ ja git/ alasivuineen omiin hakemistoihinsa lähteessä (`NEST_UNDER` pois) | `a794ce3`, `4cbc116`; ohj1 `96ce764`, `53025a5`; ohj2 `b40f12a`, `7bc0212`, `e4c5225`; jypelidocs `52b474b` |
| 2026-09-23 | tila tarkistettu: kirjojen `main` osoittimessa `ac32f1e`, `dev`-haarat jäljessä, julkaisut läpi; `dev`-haarat pidetään (päätös) | – |
