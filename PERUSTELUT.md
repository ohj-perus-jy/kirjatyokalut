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
  (`zensical/config.py`: `DEFAULT_MARKDOWN_EXTENSIONS`) eikä täydennä sitä,
  oli lohko sitten pohjassa tai kirjan `mkdocs.yml`:ssä. Siksi
  `mkdocs-pohja.yml`:ssä on koko oletuslista, johon on lisätty vain `toc`:n
  `permalink_title` (otsikon ¶-linkin vihje suomeksi). Uusi laajennus
  lisätään pohjan listaan. Kirjan oma `markdown_extensions` pudottaisi pois
  mm. `pymdownx.tabbed`in, `admonition`in ja `md_in_html`in.
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
- **Napin vihje tulee `title`-attribuutista.** `tooltips.js` tekee
  jokaisesta `button[title]`-napista teeman tyylisen vihjeen, myös skriptin
  myöhemmin lisäämästä, eikä selaimen oma vihje tule sen rinnalle. Omaa
  vihjettä ei siis tehdä. Valikon avaava nappi (`aria-expanded`) hoitaa
  kohdistuksensa itse kuten `sitemenu.js` ja `fontmenu.js`.

## Zensicalin päivitys

Kun Zensicalin versio vaihtuu, tarkista käsin:

- `overrides/partials/header.html`, `copyright.html` ja
  `javascripts/content.html` ovat kopioita teeman malleista. Vertaa ne teeman
  uusiin versioihin. `content.html` nojaa lisäksi teeman sisäiseen
  `data-md-switching`-lippuun.
- `mkdocs-pohja.yml`:n `markdown_extensions` on kopio oletuslistasta (ks.
  Ansat). Vertaa sitä uuteen `DEFAULT_MARKDOWN_EXTENSIONS`iin, ettei
  uusi tai muuttunut oletus jää pois.
- `search.css` käyttää teeman minifioituja luokkanimiä, ja `tooltips.js`
  jäljittelee teeman vihjettä (`.md-tooltip2`, elementit, joille teema tekee
  vihjeen). Muutokset tulevat esiin testeissä `test_search.py` ja
  `test_tooltips.py`.
- `layout.css` kumoaa `!important`illa inline-tyylit, jotka Zensicalin
  skripti kirjoittaa sivupalkille. Tiedostossa on myös kopio teeman
  hiusviivojen geometriasta. Jos valikko tai viivat hajoavat, katso tämä
  tiedosto ensimmäisenä.
- `mkdocs-pohja.yml`:n `theme.font: false` nojaa siihen, että `base.html`
  jättää silloin pois sekä Google Fontsin linkin että muuttujat
  `--md-text-font` ja `--md-code-font` (0.0.68: `{% block fonts %}`, rivit
  70–80), jotka `assets/css/fonts.css` asettaa. Tarkista uudesta
  `base.html`:stä, että ehto on yhä `config.theme.font != false` ja että
  teeman CSS johtaa `--md-text-font-family`n yhä muuttujasta
  `--md-text-font`. `overrides/main.html` korvaa teeman `main.html`:n, joka
  on ollut pelkkä `{% extends "base.html" %}`; jos siihen tulee sisältöä, se
  on tuotava omaan kopioon. `tests/test_fonts.py` huomaa, jos kirjasimet
  eivät enää lataudu sivustolta.

## Kirjasimet

Kirjasintiedostot (Source Serif 4, Source Sans 3, JetBrains Mono, Literata,
Atkinson Hyperlegible Next) ovat repossa `assets/fonts/`-hakemistossa ja
tulevat sivustolle sen omasta osoitteesta (`assets/css/fonts.css`), eivät
Google Fontsista. `skriptit/fontit.py` hakee ne ja kirjoittaa `fonts.css`:n.

- **Ei ulkoista riippuvuutta.** Kirja näyttää samalta ilman yhteyttä Googleen:
  vahdissa ilman verkkoa, verkoissa ja selaimissa, joista Google Fonts on
  estetty. Aiemmin kirjasimet vaihtuivat silloin hiljaa varakirjasimiin.
- **Nopeampi ensimmäinen lataus.** Googlen reitti oli kolme peräkkäistä
  pyyntöä kahteen vieraaseen osoitteeseen (`typography.css` → Googlen CSS →
  tiedosto). Selainten välimuisti on sivustokohtainen, joten muiden
  sivustojen lataamista Google-kirjasimista ei ollut hyötyä. Nyt tiedosto
  tulee samasta osoitteesta kuin sivu, ja leipätekstin tiedosto esiladataan
  (`overrides/main.html`).
- **Tiedostot vaihtuvat vain commitilla.** Google päivittää kirjasimia omaan
  tahtiinsa, jolloin ulkoasu ja mitat saattoivat muuttua ilman muutosta
  tässä repossa; svgbob-kaaviot nojaavat JetBrains Monon merkkileveyteen
  (`diagrams.css`). Päivitys tehdään ajamalla `skriptit/fontit.py` (Adoben
  perheillä ensin tagin vaihto skriptiin), ja muutos näkyy diffissä. Testit
  ajetaan samoilla tiedostoilla kuin julkaisu.
- **Tietosuoja.** Google Fontsin rajapinta saa jokaisesta sivulatauksesta
  lukijan IP-osoitteen, selaimen tiedot ja sivun osoitteen (Googlen oma
  FAQ). Omalta palvelimelta ladattaessa Google ei saa mitään, eikä kolmatta
  osapuolta tarvitse mainita tietosuojaselosteessa.
- **Kaksi lähdettä lisenssin takia.** Kaikki viisi perhettä ovat SIL OFL 1.1
  -lisensoituja. OFL sallii jakelun ohjelmiston mukana, kun
  tekijänoikeusilmoitus ja lisenssi kulkevat mukana: perheen `OFL.txt` on
  tiedostojen vieressä ja kopioituu sivustolle (`tests/test_fonts.py`
  tarkistaa).
  Google Fontsin palvelemat tiedostot on pilkottu merkistöittäin, mikä on
  OFL:n mielessä muokkaus (OFL-FAQ 2.6). Muokattu versio ei saa käyttää
  tekijän varaamaa nimeä (Reserved Font Name), ja CSS:n `font-family` on
  nimi, "jolla kirjasin määritellään dokumentissa" (OFL-FAQ 5.3). Adobe on
  varannut nimen "Source" sekä Source Sans 3:lle että Source Serif 4:lle,
  joten ne haetaan Adoben omista julkaisuista (github.com/adobe-fonts)
  muuttuvina woff2-tiedostoina, jotka Adobe on itse pakannut: ne ovat
  alkuperäisversioita, ja nimi saa pysyä (OFL-FAQ 2.2.1). Tiedostot ovat
  cff2-pohjaisia, koska Adoben ttf-pohjaisista puuttuvat vihjetaulut ja
  Chromium Linuxilla asettaa niiden merkit epätasaisin välein; vihjeiden
  lisääminen itse tekisi tiedostosta muokatun version (`skriptit/fontit.py`).
  Literatalla, Atkinson Hyperlegible Nextillä ja JetBrains Monolla ei ole
  varattua nimeä, joten niille kelpaavat Googlen pilkotut tiedostot, jotka
  ovat samat kuin sivuilla tähänkin asti. Google valitsee tiedoston selaimen mukaan: Chrome
  ja Firefox saavat samat tiedostot, Safari omansa; repossa on Chromen
  versio kaikille.
- **Koko.** Adoben tiedostot sisältävät koko merkistön: Source Serif 4:n
  pysty on 416 KiB ja Source Sans 3:n 160 KiB, kun Googlen latin-osat olivat
  120 ja 28 KiB. Tavallisen sivun ensimmäinen lataus kasvaa noin 430 KiB,
  minkä jälkeen selain käyttää välimuistia. Googlen perheet ovat 12
  tiedostoa, joista lukija lataa vain käyttämänsä. Hylätyt vaihtoehdot:
  Googlen Source-tiedostot omalla nimellä (vaatisi tiedostojen sisäisten
  nimien muuttamisen eli oman muokatun version, OFL-FAQ 3.1) ja Googlen
  kaikki merkistöt vetoamalla OFL-FAQ:n "Functional Equivalenceen" (2.7),
  jota FAQ itse pitää epäkäytännöllisenä.

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

## Ääneenluku

Koko sivun ääneenluku jakautuu neljään tiedostoon: `convert.py` paloittelee ja
merkitsee, `puhe.py` tekee leikkeet, `puhe.js` soittaa, ja kirjan
`pages.yml` hakee leikkeet julkaisuun.

- **Merkit ovat Markdownissa.** `convert.py` paloittelee sivun lopullisen
  Markdownin ja kirjoittaa jokaiseen lohkoon näkymättömän merkin. Paloittelu
  jäljittelee Python-Markdownin lohkojäsennystä vain sen verran, että merkki
  osuu oikeaan lohkoon. `tests/test_puhe.py` renderöi siksi jokaisen sivun
  oikealla jäsentimellä merkeillä ja ilman niitä ja vaatii tuloksilta samaa
  HTML:ää ja sisällysluetteloa. Hylätyt vaihtoehdot:
  - Paloittelu selaimessa: sama tekstin muokkaus olisi pitänyt kirjoittaa
    kahdesti.
  - Rakennuksen jälkeinen HTML-ajo: se ei toimisi `zensical serve`n kanssa.
  - Python-Markdown-laajennus: `convert.py` ajetaan ilman `.venv`:iä.
- **Leike on kappale, ja sen nimi on tiiviste lähetettävästä pyynnöstä**
  (`speech_clip`). Korjaus syntetisoi uudelleen vain muuttuneen kappaleen, ja
  sama teksti eri sivuilla on yksi tiedosto. Äänen tai muodon vaihto vaihtaa
  nimet itsestään, joten luetteloa ei tarvita: leike on olemassa tai ei.
- **Merkinnän vaihto ei saa muuttaa luettavaa tekstiä.** Kun lähde
  kirjoitetaan uusin merkinnöin (YHTENAISTYS.md), jokainen muuttunut
  kappale olisi uusi leike, joka maksetaan Azurelle uudelleen. Siksi
  esimerkiksi kuvakkeen lyhytkoodi ohitetaan samoin kuin valmis SVG-kuvake
  (`SPEECH_ICON_RE`).
- **Leikkeet ovat erillisessä repossa (`[puhe] repo`).** Koko kirja on
  arviolta 100 Mt, ja jokainen korjaus jättäisi kirjan historiaan vanhan
  version. Saman repon orpo haara tulisi silti jokaiseen `git clone`en.
  Myös vaiheittaisen ohjeen vaiheet ovat samanlaisia leikkeitä samassa
  varastossa. Ne olivat aluksi lähdepuussa sivun vieressä, ja ohj1:n
  historiaan oli kertynyt niitä kahdessa commitissa jo 6 Mt.
- **Varasto on klooni, ei submodule.** Submodule kiinnittäisi kirjaan
  varaston tietyn version, ja jokaisen `puhe`-ajon jälkeen kirjaan pitäisi
  committaa uusi osoitin; unohdus kaataisi julkaisun puuttuviin leikkeisiin
  (`--strict`). Leike ei vanhene, koska sen nimi on tiiviste sisällöstä,
  joten varaston uusin versio käy kirjan jokaiselle haaralle ja versiolle.
  Siksi kirja ei viittaa varastoon lainkaan: se on `.gitignore`ssa, ja
  `pages.yml` hakee sen omalla checkout-askeleellaan.
- **Välilehti valitaan toistohetkellä.** Kaikkien välilehtien kappaleet
  syntetisoidaan, ja soitin lukee sen, jonka lukija on valinnut. Ilmoitukset
  ("N välilehteä otsikoilla …", "Luetaan välilehti X") pitävät otsikon
  perusmuodossa, jottei mielivaltaisia otsikoita tarvitse taivuttaa.
- **Koodia, taulukoita ja kaavioita ei lueta, vaan niistä ilmoitetaan.**
  Suomenkielinen ääni lukee C#:ta huonosti, eikä taulukko aukea kuulijalle
  riveittäin.
- **Merkki tulee vain lohkoon, jonka leike on varastossa.** Sivu toimii
  ilman ääniä, ja käännös varoittaa puuttuvista. `--strict` kaatuu vain, jos
  koko varasto puuttuu.
