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

- **`markdown_extensions` korvaa Zensicalin koko oletuslistan**
  (`zensical/config.py`) eikä täydennä sitä, oli lohko sitten pohjassa tai
  kirjan `mkdocs.yml`:ssä. Yhden rivin lisäys pudottaa pois mm.
  `pymdownx.tabbed`in, `admonition`in ja `md_in_html`in. Kaikki tarvittava on
  jo oletuslistalla.
- **Raaka HTML ja Python-Markdown.** Raa'an HTML-lohkon sisältö jäsennetään
  vain `markdown`-attribuutilla (`md_in_html`). Attribuutti ei etene
  sisempiin lohkoihin, jos uloin lohko on käsittelemätön, ja tyhjä rivi
  lopettaa lohkon. Tuntematon tagi (`<task>`, `<svg>`) päätyy kappaleen
  sisään, ja neljällä välilyönnillä sisennetty rivi on koodilohko. Nämä
  koskevat jokaista uutta muunnosta.
- **Omien värien lähde on `--md-typeset-a-color`.** Se on teeman ainoa
  korostusväri, joka on oikea molemmissa teemoissa. `--md-primary-fg-color`
  on tummalla taustalla lukukelvoton.
- **Tulostussivu (`/tulosta/`) kootaan vasta sivun latauduttua.** Sivulle
  latautuessa ajettava skripti ei näe koottuja lukuja. Uuden ominaisuuden on
  kuunneltava `jyu-print-assembled`-tapahtumaa, kuten piilorivit, korostukset
  ja nauhoitukset tekevät (`print.js`).

## Zensicalin päivitys

Kun Zensicalin versio vaihtuu, tarkista käsin:

- `overrides/partials/header.html`, `copyright.html` ja
  `javascripts/content.html` ovat kopioita teeman malleista. Vertaa ne teeman
  uusiin versioihin. `content.html` nojaa lisäksi teeman sisäiseen
  `data-md-switching`-lippuun.
- `layout.css` kumoaa `!important`illa inline-tyylit, jotka Zensicalin
  skripti kirjoittaa sivupalkille. Tiedostossa on myös kopio teeman
  hiusviivojen geometriasta. Jos valikko tai viivat hajoavat, katso tämä
  tiedosto ensimmäisenä.

## Muunnosaskel: vahti (vaihtoehto A)

`zensical serve` seuraa `docs/`:ia eikä lähdettä. Siksi `convert.py --watch`
ajaa muunnoksen aina, kun lähde muuttuu.

- **B:** `docs/` versionhallintaan uudeksi lähteeksi. Hylättiin, koska
  piilorivien ja korostusten rivinumerot pitäisi kirjoittaa ja päivittää käsin.
- **C:** Sivukohtaiset muunnokset Python-Markdown-laajennukseksi. Hylättiin,
  koska vahti osoittautui riittävän nopeaksi (noin sekunti tallennuksesta
  selaimeen). Lisäksi navigaatio, tulostussivu, PlantUML-haku ja
  `extra.tab_labels` tarvitsevat joka tapauksessa koko kirjan esiajon. Ainoa
  jäljellä oleva peruste C:lle on `docs_dir: src`, joka pitäisi linkit,
  polut ja historian koskemattomina.

`serve`in oma tiedostovahti käyttää inotifyä, joka ei saa tapahtumia
9p-liitoksen takaa (Windowsin levy WSL:ssä tai devcontainerissa). Jos
tallennus ei näy selaimessa, tarkista, että repo on Linuxin
tiedostojärjestelmässä.
