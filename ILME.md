# Ilmeen uudistus: auditointi, suunta ja läpikäynnit

Suunnitelma kirjojen yhteisen ulkoasun hiomiseksi unslop-menetelmällä
(Damir Sokolovsky, CC BY 4.0: `~/tools/unslop`). Menetelmä etsii ensin
"slopin" eli valitsemattomat oletukset ja koristeet, kirjoittaa sitten
suunnan tuotteesta itsestään ja korjaa ruudun kerros kerrallaan:
välit, väri, kuvakkeet, tekstit, kirjasimet, asettelu, yksityiskohdat,
kuvitus, liike.

Auditoitu 2.11.2026 ohj2:n rakennetusta sivustosta (Zensical 0.0.73)
kuvakaappauksin 1440, 1180 ja 390 px:n leveyksillä, vaaleana ja tummana,
sekä lasketuista tyyleistä. Kuvat: etusivu, 2.2 Luokka ja olio, 2.4 Osan
kaikki tehtävät, osan 2 etusivu, haku, kirjasinvalikko, piilotettu kisko.

## Tila

Läpikäynnit on tehty 2.11.2026 (haara `asettelu-unslop`) kahta poikkeusta
lukuun ottamatta: laatikoiden tyyppivärien yhdistäminen katsotaan
myöhemmin, ja "Made with Zensical" jää. Hiusviiva jäi 20 %:iin: 10 % hävitti
laatikon ja koodinappien reunat, ja hakuikkunan reunan testi vaatii
vähintään 20 %. Värit ja liikkeen arvot ovat `assets/css/paletti.css`:ssä.
Mockup, jonka pohjalta suunta hyväksyttiin, ja alla oleva auditointi ovat
tilanne ennen muutoksia.

## Tulos lyhyesti

**Kevyt slop, ei raskas.** Rakenne (kiinteä kisko, tekstipalsta,
sisällysluettelo), leipätekstin kirjasin ja koodilohkot on valittu
tietoisesti ja perusteltu tiedostoissaan. Mitään ei hehku, kuvakkeet ovat
yhtä sarjaa eikä sivulla ole emojeita, liukuvärejä tai hyperbolaa.

Se, mikä puuttuu, on **suunta**: kehyksen värit ovat Zensicalin
oletukset (Materialin indigo `#4051b5`, aksentti `#526cfe`), laatikot
Materialin kuusi sävyä, otsikot teeman 700-paino. `tasks.css` sanoo sen
itse: "JYU-paletti on tekemättä". Siksi menetelmän mukainen tila on
**hiontatila**: korjataan vain auditoinnin löydökset, otetaan suunta
siitä, mikä on jo valittu (Source Serif 4, JetBrains Mono, riippuva
tehtävänumero, mdBook-perintö), ja säilytetään asettelu. Uutta
asettelurakennetta ei tarvita, ja rakenteen vaihto heittäisi hukkaan
iPad-rajan ja kiskon piilotuksen mittatyön.

## Auditointi

Jokainen löydös ja sen korjaus; sijainti suluissa.

### Pinnat ja väri

- Kaksi sinistä, joita kukaan ei valinnut: primary `#4051b5` ja
  accent `#526cfe` ovat Materialin oletukset; tummassa linkki on kolmas
  sininen `#5488e8` (teema, `layout.css`). → Yksi aksentti kummassakin
  teemassa.
- Valittu valikkorivi: aksentin 10 %:n tausta, aksentin värinen teksti
  ja paino 700 — kolme korostusta samalle riville (teema +
  `typography.css`). → Pintaporras ja väri, paino 600.
- Laatikot kuudessa Materialin sävyssä (note, abstract, info, tip,
  warning, danger) ja kolmessa omassa (kokeile, ei-toimi, kysymys):
  kolme eri sinistä, kaksi punaista (`admonitions.css`). → Tietotyypit
  yhteen musteeseen, semanttiset värit vain merkitykselle.
- TIM-napin hover: kaksi värillistä hehkuvarjoa (`tasks.css`,
  `--jyu-task-btn-glow`). → Pintaporras, ei hehkua.
- Hiusviiva `--jyu-rule` on 20 % mustaa; menetelmän mitta on 6–10 %
  (`layout.css`). → Kokeiltu 10 %, palautettu 20 %:iin (ks. Tila).
- Tumman teeman pinnat 20 %:n kylläisyydellä (hue 225): tausta lukee
  sinisenä (`layout.css`, `code.css`). → Sama sävy, kylläisyys 10–12 %.
- Visan vaihtoehdot viidessä aksentin tummuusportaassa 12–45 %
  (`visa.css`). → Neutraalit portaat, aksentti vain valinnassa.
- Koodinappien hover: varjo kasvaa ja nappi nousee (`codebuttons.css`).
  → Väri- ja pintamuutos ilman siirtoa.

### Kirjasimet

- h1 ja h2 painolla 700; h2 (24,75 px) negatiivisella välistyksellä
  −0,025 em, joka kuuluu vain yli 40 px:n tekstille (teema +
  `typography.css`). → 600 ja 500, välistys 0 alle 40 px:n.
- Yläpalkin kurssin nimi 700 (teema). → 600.
- Sisällysluettelon otsikko "Sisällysluettelo" 700 (teema). → 500,
  toissijainen väri.
- Laatikon otsikkorivi 700 (teema). → 600.
- Tehtävän pisteet 700 ja +0,04 em (`tasks.css`). → 500 mono, ei
  välistystä.
- Bonusliuska: versaali, +0,06 em, 700, pilleri (`tasks.css`). → "Bonus"
  pienillä kirjaimilla, 500, tähti ja sana kullassa ilman reunusta.
- Tehtävänumero 600 (`tasks.css`). Tämä jää: se on allekirjoitus (ks.
  Suunta).

### Kuvakkeet

- Kaksi sarjaa: Lucide kaikkialla muualla, mutta alatunnisteessa
  Materialin `github`, `history` ja `flag-outline` ja yläpalkin
  teemavaihtimessa Materialin `weather-night` / `weather-sunny`
  (`copyright.html`, `mkdocs-pohja.yml`). → Lucide: `github`, `history`,
  `flag`, `moon`, `sun`.

### Välit

- Kehyksen arvot ovat teeman rem-murtolukuja, jotka eivät osu 4 px:n
  ruudukkoon: laatikon täyte 18 px ja otsikkorivin 8/18/46 px, h2:n
  alamarginaali 13,6 px, kappaleväli 11 px (`admonitions.css`,
  `typography.css`). → Kehys (valikot, laatikoiden reunat, napit,
  alatunniste) 4 px:n ruudukkoon; leipätekstin em-rytmi jää, koska se on
  typografinen järjestelmä eikä satunnaisarvo.
- Osan etusivu: sisältö lyhyt, alatunniste jää ruudun keskelle ja alle
  jää tyhjä kaista (`osa2/index`). → Pääalueelle vähimmäiskorkeus, jotta
  alatunniste on ikkunan alareunassa.

### Tekstit

- "Made with Zensical" englanniksi suomenkielisessä alatunnisteessa
  (teema, `copyright.html`). → "Tehty Zensicalilla" tai pois
  (`extra.generator: false`).
- Visan palaute "Oikein!" huutomerkillä (`visa.js`). → "Oikein".
- Muu käyttöliittymäteksti on kunnossa: ei tervehdyksiä, ei
  hypesanoja, ei pisteitä nappien perässä.

### Komponentit

- Pyöristykset eivät summaudu: koodilohko 8 px ja sen napit 3 px,
  TIM-nappi 4 px, laatikko 4 px, kirjasinvalikon nappi 8 px, visan
  vaihtoehdot 4 px. → Sisäkkäinen sääntö: sisempi = ulompi − täyte,
  vähintään 4.

### Asettelu, kuvitus, liike

- Asettelu: ei löydöksiä. Kisko 15–16 rem, palsta 816 px, luettelo
  oikealla, leveällä näytöllä keskitetty ryhmä, puhelimessa laatikko.
  Kiskon leveys ylittää menetelmän 240–280 px:n ohjeen, mutta se on
  mdBookin mitta ja iPad-raja on laskettu sen mukaan: jää.
- Kuvitus: ei koristeita poistettavaksi. Vaiheittaisen ohjeen
  IDE-kohtaukset ja luokkakaaviot ovat sisältöä, eivät kehystä.
- Liike: siirtymät on nimetty (color, background-color, transform…),
  ei `transition: all`. Opastusnuoli keinuu silmukassa, mutta se kertoo
  jotain ja poistuu ensimmäisellä painalluksella: jää. Easing-käyriä on
  kaksi (Materialin `cubic-bezier(.4,0,.2,1)` ja `ease`), kestoja viisi
  (0,05–0,5 s). → Yksi käyrä, kolme kestoa.

### Mallipohjan tarkistus

Jos kurssin nimen vaihtaisi, sopisiko ruutu mihin tahansa
Material-sivustoon? Kehys kyllä: indigo, valkoinen, Source Sans 3.
Sisältö ei: serifi, riippuvat tehtävänumerot, ajonapit, IDE-kohtaukset.
Suunnan tehtävä on tuoda kehys sisällön tasolle.

## Suunta

Viisi riviä, johdettu siitä mitä sivu tekee ja kenelle.

- **Tuote.** Jyväskylän yliopiston ohjelmointikurssien oppikirja
  verkossa: luettavaa tekstiä, ajettavia Java- ja C#-esimerkkejä ja
  TIMiin palautettavia tehtäviä ensimmäisen vuoden opiskelijalle, joka
  lukee pitkään näytöltä, usein iPadilta.
- **Luonne.** Kärsivällinen, tarkka, paperinen.
- **Maailma.** Painettu oppikirja ja ohjelmoijan editori. Paperi ja
  muste antavat kehyksen: lämpimään taittuva neutraali, yksi
  mustesininen. Editori antaa ainoan rikkaan värin: syntaksivärit
  koodilohkossa ja IDE-kohtausten valo.
- **Hetket.** (1) Koodilohko: sivun parhaiten piirretty asia, editorin
  pinta, syntaksivärit ja ajon tuloste; napit sen reunassa hiljaa.
  (2) Vaiheittaisen ohjeen IDE-kohtaus: kuvitus, jossa värit ja varjot
  saavat olla, koska se esittää oikeaa ohjelmaa.
- **Allekirjoitus.** Riippuva mono-numero marginaalissa: tehtävän
  numero `2.1` roikkuu palstan vasemmalla puolella kuten painetussa
  harjoituskirjassa. Vain tehtävissä, ei muualla.

Jos kurssilla on käytössä JYU:n virallinen väri, se korvaa alla
ehdotetun musteen aksenttina ja pysyy pois pinnoilta.

## Paletti

Yksi neutraali luiska per teema, kolme tekstiroolia, yksi aksentti.
Kontrastit laskettu (WCAG), aksentti tekstinä ja napin pohjana ≥ 7:1.

| Rooli | Vaalea | Tumma |
| --- | --- | --- |
| Sivu | `#ffffff` | `hsl(225 12% 10%)` ≈ `#17191d` |
| Kisko ja alatunniste | `#f4f3f0` | `hsl(225 12% 8%)` ≈ `#121418` |
| Korotettu pinta (valittu rivi, nappi) | `#eceae6` | `hsl(225 12% 15%)` |
| Hiusviiva | teksti 20 % | teksti 20 % |
| Ensisijainen teksti | `#000000eb` (nyk.) | `#e1e1e1` (nyk.) |
| Toissijainen teksti | `#5e554a` | `#a6a39c` |
| Vaimea teksti ja kuvakkeet | `#737373` | `#85858b` |
| Aksentti, muste | `#1f4fa0` (7,8:1 valkoisella) | `#8fb3ff` (8,7:1 sivulla) |
| Bonus, kulta | `#9a7326` (nyk.) | `#d3ab6d` (nyk.) |
| Hyvä / virhe | `#16a34a` / `#dc2626` | `#4cc38a` / `#e5484d` |
| Varoitus | `#b45309` | `#f0a040` |

Teeman muuttujat `--md-primary-fg-color`, `--md-accent-fg-color` ja
`--md-typeset-a-color` asetetaan kaikki musteeseen, jolloin teeman omat
komponentit (haku, välilehdet, kohdistusrenkaat) seuraavat ilman
erillissääntöjä. Koodilohkon tausta jää neutraaliksi: vaalea `#f5f5f5`
→ `#f6f5f2`, tumma `hsl(225 12% 16%)`.

## Läpikäynnit

Järjestyksessä, kukin koko ruudun yli ennen seuraavaa. Arvot ovat
lähtökohta; mitataan kuvakaappauksista ja korjataan. Tiedostot ovat
`assets/css/` ja `overrides/partials/`.

### 1. Välit (chrome 4 px:n ruudukkoon)

- Valikko: rivi 32, rivien väli 2, sisennetyn tason viiva 16 px
  vasemmasta; osan otsikon ylle 24, sen alle 8 (`layout.css`).
- Laatikko: täyte 16, otsikkorivi 8 / 16 / 44, kuvake 16 px vasemmasta;
  puhelimessa 12 / 12 / 36 (`admonitions.css`).
- Koodilohko: `pre > code` täyte 12 / 16 remeinä, ei em-johdettuna
  (`code.css`); nappirivi 8 px lohkon reunasta.
- Alatunniste: täyte 16 / 24, linkkirivin väli 16 (`layout.css`).
- Pääalue: `min-height: calc(100vh − 48px)` niin, että alatunniste on
  lyhyelläkin sivulla alareunassa (`layout.css`).
- Leipäteksti: ei muutoksia; em-rytmi (`typography.css`) on
  järjestelmä.

### 2. Väri

- Paletti ylle `:root`iin ja `[data-md-color-scheme=slate]`en yhdessä
  tiedostossa (`typography.css` tai uusi `paletti.css` ennen muita).
- Laatikot: reunus hiusviivaksi, tyypin väri kuvakkeessa ja otsikkorivin
  10 %:n taustassa (`admonitions.css`). Tyyppien yhdistäminen (note,
  abstract, info, kysymys → muste; tip ja kokeile → hyvä; warning →
  varoitus; danger ja ei-toimi → virhe) katsotaan myöhemmin.
- Valittu valikkorivi: korotettu pinta + musteen värinen teksti
  (`layout.css`, `typography.css`).
- TIM-nappi: muste, hover 10 % tummempi, ei hehkua; tumma teema:
  mustesininen pohja ja tumma teksti (`tasks.css`).
- Koodinapit: korotettu pinta + hiusviiva, hover tummempi pinta,
  painettu muste; ei varjoa (`codebuttons.css`).
- Visa: vaihtoehdot neutraalilla pinnalla, valittu musteella; oikein ja
  väärin semanttisilla (`visa.css`).
- Hiusviiva `--jyu-rule` jää 20 %:iin; `--jyu-edge` siitä johdettuna
  (`paletti.css`).

### 3. Kuvakkeet

- `copyright.html`: `lucide/history`, `lucide/flag`; GitHub-merkki jää
  Materialin sarjasta, koska Lucidessa ei ole tuotemerkkejä.
- `mkdocs-pohja.yml`: paletin kuvakkeet `lucide/moon` ja `lucide/sun`.
- Yksi koko: alatunnisteessa 16 px, yläpalkissa teeman 20 px; viiva 1,5.

### 4. Tekstit

- "Made with Zensical" jää toistaiseksi.
- `visa.js`: "Oikein!" → "Oikein".
- Bonusliuska: HTML:ssä on jo "Bonus"; versaali tulee pelkästä
  `text-transform`ista (`tasks.css`), joten muutos on tyyliin.

### 5. Kirjasimet

- Otsikot: h1 600 / 2,25 em / −0,02 em (37 px, raja); h2 600 / 1,5 em /
  0; h3 500 / 1,2 em / 0 (`typography.css`).
- Yläpalkin nimi 600; sisällysluettelon otsikko 500 toissijaisella
  värillä; laatikon otsikkorivi 600; valikon valittu rivi 600, muut 400
  (nyk. 500 jäi haaleaksi: mitataan uudelleen uudella värillä, 500 jää
  jos 400 ei kanna).
- Tehtävän pisteet: mono 500, `tabular-nums`, ei välistystä;
  bonus 500 pienillä kirjaimilla.
- Kaikki numerot `tabular-nums`: tehtävänumero (on), pisteet,
  tekstikoon prosentti kirjasinvalikossa.

### 6. Asettelu

- Ei rakennemuutoksia. Ainoa muutos on pääalueen vähimmäiskorkeus
  (läpikäynti 1).

### 7. Yksityiskohdat

- Pyöristykset: laatikko 8, sen otsikkorivi 7 / 7 / 0 / 0; koodilohko 8
  ja napit 4 (8 − 8 → vähintään 4); TIM-nappi 8; visan vaihtoehto 6;
  valikon rivi 8 (nyk.); kirjasinvalikon paneeli 8 ja sen rivit 4
  (`admonitions.css`, `codebuttons.css`, `tasks.css`, `visa.css`,
  `fontmenu.css`).
- Bonus ilman pilleriä: tähti + "Bonus" kullassa, 500, väli 0,35 em.
- Kohdistusrengas: 2 px muste, `outline-offset: 2px`, kaikkiin
  nappeihin samalla säännöllä.
- Tooltipit ja valikot: `--md-shadow-z3` → `0 8px 24px rgb(0 0 0 / 6%)`
  vaaleassa, tummassa pintaporras + hiusviiva.

### 8. Kuvitus

- Ei generoituja kuvia. Hetket ovat jo sivulla. Tarkistetaan vain, että
  koodilohko on sivun parhaiten piirretty asia: ajon tuloste samalle
  pinnalle yhtenäisellä pyöristyksellä, Jypelin ikkunakuva lohkon
  sisällä (`playground.css`).

### 9. Liike

- Yksi käyrä `--jyu-ease: cubic-bezier(.22, 1, .36, 1)` ja kestot 150
  (hover, painallus), 200 (valikot, vihjeet), 300 ms (kisko, sisääntulo)
  kaikkiin `.css`-tiedostoihin; `prefers-reduced-motion` jää kuten nyt.
- Koodinapin nousu hoverissa pois; painallus `scale(.97)` jää.

## Tarkistus

- Kuvakaappaukset samoista näkymistä kuin auditoinnissa; verrataan
  löydöslistaan, mikä jäi.
- `./zensical/run.sh test`: `test_layout.py`, `test_rail.py`,
  `test_theme.py`, `test_fontmenu.py` ja `test_book.py` mittaavat mittoja
  ja värejä, joten osa odotusarvoista päivittyy tietoisesti.
- Kolme kirjaa: ohj1, ohj2 ja jypelidocs rakennetaan samalla
  työkaluhaaralla ennen mergeä.

## Mitä ei tehdä

- Ei uutta asettelurakennetta, ei kiskon leveyden muutosta, ei
  tekstipalstan muutosta.
- Ei liukuvärejä, lasia, rakeisuutta tai muuta tilalle tuotua
  koristetta.
- Ei kurssin nimen, logon tai sisällön muutoksia.

## Päätökset

1. Aksentti: ehdotettu muste `#1f4fa0` / `#8fb3ff` (2.11.2026).
2. Laatikoiden tyyppien yhdistäminen neljään väriin: katsotaan myöhemmin.
3. "Made with Zensical": jää toistaiseksi.
4. Hiusviiva: 20 %, koska 10 % oli liian haalea (2.11.2026).
