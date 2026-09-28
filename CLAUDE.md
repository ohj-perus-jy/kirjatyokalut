# Kirjojen yhteiset ohjeet

Tämä repo on kirjojen (ohj1, ohj2, jypelidocs) submodule `zensical/tyokalut`.
Kirjan oma `CLAUDE.md` tuo nämä ohjeet rivillä `@zensical/tyokalut/CLAUDE.md`.

## Kirjoitusasu

- Valikkopolut kirjoitetaan ›-merkillä ja valikkojen nimet kursiivilla:
  `*Tests* › *Run All Tests from Solution*`. Älä käytä merkintää
  `<i class="bi bi-chevron-right"></i>` äläkä nuolta →.
- Rajakohtailmaukset, kuten lukuvälit kirjoitetaan pitkällä viivalla, ei yhdysviivalla. Esim. "1–3" eikä "1-3".
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
