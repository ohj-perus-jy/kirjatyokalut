# Kirjojen yhteiset ohjeet

Tämä repo on kirjojen (ohj1, ohj2, jypelidocs) submodule `zensical/tyokalut`.
Kirjan oma `CLAUDE.md` tuo nämä ohjeet rivillä `@zensical/tyokalut/CLAUDE.md`.

## Kirjoitusasu

- Valikkopolut kirjoitetaan ›-merkillä ja valikkojen nimet kursiivilla:
  `*Tests* › *Run All Tests from Solution*`. Älä käytä merkintää
  `<i class="bi bi-chevron-right"></i>` äläkä nuolta →.
- Rajakohtailmaukset, kuten lukuvälit kirjoitetaan ndash-viivalla, ei yhdysviivalla. Esim. "1–3" eikä "1-3".
- Ajatusviiva on mdash ("—"), ei yksi eikä kaksi yhdysviivaa.
- Valikkopolut kirjoitetaan kursiivilla. Kohtien väliin tulee välilyönti ja
  chevron, esimerkiksi *File* › *New* › *Project*.

## Ääneenluku

- Sivut, jotka luetaan ääneen, ovat kirjan `zensical/kirja.toml`:ssa
  (`[puhe] sivut`). Niillä kuvaan kirjoitetaan kuvaava vaihtoehtoinen teksti
  (`![Rider, jossa Run-nappi korostettuna](...)`), koska se luetaan
  ("Kuva: …").
- Koodilohkon ympärille tulee tyhjä rivi. Muuten Python-Markdown liimaa
  aidan jälkeisen tekstin edelliseen kappaleeseen, eikä korostus osu siihen
  oikein.
- Luettavan tekstin voi tarkistaa komennolla `./zensical/run.sh puhe --teksti`,
  joka ei tee ääniä eikä maksa.

## Äänivarasto `zensical/puhe/`

- Kansio on ääneenluvun leikkeiden repon (`kirja.toml`: `[puhe] repo`)
  klooni, **ei submodule**. Se kuuluu kirjan `.gitignore`en, ja `pages.yml`
  hakee sen omalla checkout-askeleellaan (ks. README, Ääneenluku).
- Älä poista kansiota äläkä sen tiedostoja: leikkeet on maksettu Azurelle.
  Jos kansio on vahingossa kirjan repossa gitlinkinä, korjaus on
  `git rm --cached zensical/puhe` (poistaa vain viittauksen) ja rivi
  `zensical/puhe/` `.gitignore`en.
- Leikkeiden tila tarkistetaan varaston omasta reposta:
  `git -C zensical/puhe status -sb`.
