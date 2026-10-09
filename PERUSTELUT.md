# Perustelut

Kunkin ratkaisun perustelu on siinä tiedostossa, jota ratkaisu koskee:
`convert.py`:n funktioiden docstringeissä sekä tyylien, skriptien ja mallien
alkukommenteissa. Tähän on koottu vain se, mikä ei selviä yhdestä
tiedostosta. Mittaukset ja kehityshistoria ovat tämän tiedoston pitkässä
versiossa: `git show d5c7f42:PERUSTELUT.md`.

## Periaate

Lähtökohta on Zensicalin oletusteema sellaisenaan. Jokainen lisäys tehdään
vasta, kun tarve on todettu, ja perustellaan sen omassa tiedostossa.
`convert.py` muuntaa vain syntaksin, jota Zensical ei ymmärrä (mdBook-murre).
Ulkoasu tulee teemalta.

## Ansat

- **`markdown_extensions` korvaa Zensicalin koko oletuslistan** eikä
  täydennä sitä, oli lohko sitten pohjassa tai kirjan `mkdocs.yml`:ssä. Uusi
  laajennus lisätään `mkdocs-pohja.yml`:n listaan; kirjan oma lista
  pudottaisi oletukset pois.
- **Raaka HTML ja Python-Markdown.** Raa'an HTML-lohkon sisältö jäsennetään
  vain `markdown`-attribuutilla (`md_in_html`). Attribuutti ei etene
  sisempiin lohkoihin, jos uloin lohko on käsittelemätön, ja tyhjä rivi
  lopettaa lohkon. Tuntematon tagi (`<task>`, `<svg>`) päätyy kappaleen
  sisään, ja neljällä välilyönnillä sisennetty rivi on koodilohko. Nämä
  koskevat jokaista uutta muunnosta.
- **Omien värien lähde on `--md-typeset-a-color`.** Se on teeman ainoa
  korostusväri, joka on oikea molemmissa teemoissa. `--md-primary-fg-color`
  on tummalla taustalla lukukelvoton.
- **Tulostussivu kootaan vasta sivun latauduttua.** Uuden ominaisuuden on
  kuunneltava `jyu-print-assembled`-tapahtumaa (`print.js`).
- **Napin vihje tulee `title`-attribuutista** (`tooltips.js`). Omaa vihjettä
  ei tehdä.

## Zensicalin päivitys

Kun Zensicalin versio vaihtuu, tarkista käsin:

- `overrides/partials/header.html`, `copyright.html` ja
  `javascripts/content.html` ovat kopioita teeman malleista. Vertaa ne teeman
  uusiin versioihin. `content.html` nojaa lisäksi teeman sisäiseen
  `data-md-switching`-lippuun.
- `mkdocs-pohja.yml`:n `markdown_extensions` on kopio oletuslistasta (ks.
  Ansat). Vertaa sitä uuteen `DEFAULT_MARKDOWN_EXTENSIONS`iin.
- `search.css` käyttää teeman minifioituja luokkanimiä, ja `tooltips.js`
  jäljittelee teeman vihjettä. Muutokset tulevat esiin testeissä
  `test_search.py` ja `test_tooltips.py`.
- `layout.css` kumoaa `!important`illa inline-tyylit, jotka Zensicalin
  skripti kirjoittaa sivupalkille, ja kopioi teeman hiusviivojen geometrian.
  Jos valikko tai viivat hajoavat, katso tämä tiedosto ensimmäisenä.
- `theme.font: false` nojaa siihen, että `base.html` jättää silloin pois
  Google Fontsin linkin ja muuttujat `--md-text-font` ja `--md-code-font`
  (`{% block fonts %}`), jotka `fonts.css` asettaa. `overrides/main.html`
  korvaa teeman `main.html`:n, joka on ollut pelkkä `{% extends "base.html" %}`.
  `tests/test_fonts.py` huomaa, jos kirjasimet eivät enää lataudu.

## Kirjasimet

Kirjasintiedostot ovat repossa (`assets/fonts/`), eivät Google Fontsissa:
kirja näyttää samalta ilman yhteyttä Googleen, latautuu nopeammin, ja
lukijan osoite ei mene Googlelle. Source-perheet haetaan Adobelta ja muut
Googlesta OFL:n varatun nimen takia; perustelu on `skriptit/fontit.py`:n
alussa. Hinta: Adoben koko merkistön tiedostot kasvattavat ensimmäistä
latausta noin 430 KiB.

## Muunnosaskel: vahti

`zensical serve` seuraa `docs/`:ia eikä lähdettä, joten `convert.py --watch`
ajaa muunnoksen aina, kun lähde muuttuu. Hylätyt: `docs/` versionhallintaan
lähteeksi (piilorivien ja korostusten rivinumerot käsin) ja sivukohtaiset
muunnokset Python-Markdown-laajennukseksi (navigaatio, tulostussivu ja
kaaviot tarvitsevat joka tapauksessa koko kirjan esiajon, ja vahti on
riittävän nopea).

## Ääneenluku

Koko sivun ääneenluku jakautuu neljään tiedostoon: `convert.py` paloittelee ja
merkitsee, `puhe.py` tekee leikkeet, `puhe.js` soittaa, ja kirjan
`pages.yml` hakee leikkeet julkaisuun.

- **Merkit ovat Markdownissa.** `convert.py` paloittelee sivun lopullisen
  Markdownin ja kirjoittaa jokaiseen lohkoon näkymättömän merkin. Paloittelu
  jäljittelee Python-Markdownin lohkojäsennystä vain sen verran, että merkki
  osuu oikeaan lohkoon; `tests/test_puhe.py` vaatii, että sivu renderöityy
  merkeillä ja ilman niitä samaksi. Hylätyt: paloittelu selaimessa (sama
  tekstin muokkaus kahdesti), HTML-ajo rakennuksen jälkeen (ei toimi
  `zensical serve`n kanssa) ja Python-Markdown-laajennus (`convert.py` ajetaan
  ilman `.venv`:iä).
- **Merkinnän vaihto ei saa muuttaa luettavaa tekstiä.** Leikkeen nimi on
  tiiviste tekstistä, joten jokainen muuttunut kappale on uusi leike, joka
  maksetaan Azurelle uudelleen. Siksi esimerkiksi kuvakkeen lyhytkoodi
  ohitetaan samoin kuin valmis SVG-kuvake (`SPEECH_ICON_RE`).
- **Varasto on erillisen repon klooni, ei submodule.** Leikkeet kasvattaisivat
  kirjan repon historiaa jokaisella korjauksella, ja orpo haara tulisi silti
  jokaiseen kloonin. Submodule kiinnittäisi kirjaan varaston version, ja
  unohtunut osoittimen päivitys kaataisi julkaisun (`--strict`). Koska leike
  ei vanhene, varaston uusin versio käy kirjan jokaiselle haaralle.

