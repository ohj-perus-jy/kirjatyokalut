#!/usr/bin/env python3
"""Kirjasintiedostot työkalujen omaan assets/fonts/-hakemistoon.

    python3 skriptit/fontit.py

Kaksi lähdettä, ks. PERUSTELUT.md, Kirjasimet:

- Source Sans 3 ja Source Serif 4 haetaan Adoben omista julkaisuista
  (github.com/adobe-fonts, ADOBE) muuttuvina woff2-tiedostoina, koko merkistö
  yhdessä tiedostossa tyyliä kohden. Perheillä on OFL:n varattu nimi "Source",
  jota saa käyttää vain alkuperäisversiolle; Adoben itse pakkaamat tiedostot
  ovat sellaisia, Google Fontsin pilkkomat eivät.
- Literata, Atkinson Hyperlegible Next ja JetBrains Mono haetaan Google
  Fontsin CSS-rajapinnasta (GOOGLE) samoina tiedostoina, jotka se palvelisi
  selaimelle (woff2-kelpoinen User-Agent, muuttuvat kirjasimet), merkistöt
  latin ja latin-ext. Perheillä ei ole varattua nimeä, joten pilkotut
  tiedostot saavat pitää nimensä.

Tiedostot tallennetaan perheittäin assets/fonts/<perhe>/ ja jokaisen perheen
lisenssi sen viereen OFL.txt:ksi (Adoben LICENSE.md, google/fonts-repon
OFL.txt). Lopuksi kirjoitetaan assets/css/fonts.css:n @font-face-säännöt
paikallisilla poluilla.

Skripti on deterministinen: ilman muutoksia lähteissä se ei muuta mitään.
Adoben versio on kiinnitetty tagiin (ADOBE); päivitys on tagin vaihto tähän
tiedostoon ja ajo. Googlen perheen päivitys näkyy polun /v15/-osan vaihtona.
Kummassakin tapauksessa muutos tulee committiin, jolloin ulkoasun muutos
näkyy diffissä eikä tule sivustolle huomaamatta. Ei riippuvuuksia Pythonin
vakiokirjaston lisäksi.
"""

import re
import sys
import textwrap
import urllib.request
from pathlib import Path

TOOL = Path(__file__).resolve().parent.parent
FONTS = TOOL / "assets" / "fonts"
CSS = TOOL / "assets" / "css" / "fonts.css"

RAW = "https://raw.githubusercontent.com"

# Adoben julkaisut: perhe, repo ja tagi, tiedostot tyyleittäin (ttf-pohjainen
# woff2: cff2-pohjainen olisi hieman pienempi, mutta ttf toimii kaikissa
# selaimissa) ja muuttuvan kirjasimen painoalue (fvar-taulun wght).
ADOBE = [
    ("Source Sans 3", "source-sans", "3.052R", {
        "normal": "WOFF2/VF/SourceSans3VF-Upright.ttf.woff2",
        "italic": "WOFF2/VF/SourceSans3VF-Italic.ttf.woff2"}, "200 900"),
    ("Source Serif 4", "source-serif", "4.005R", {
        "normal": "WOFF2/VAR/SourceSerif4Variable-Roman.ttf.woff2",
        "italic": "WOFF2/VAR/SourceSerif4Variable-Italic.ttf.woff2"}, "200 900"),
]

# Google Fonts: perhe, css2-rajapinnan akselit (samat kuin aiemmin
# typography.css:n @importissa) ja perheen hakemisto google/fonts-repossa.
GOOGLE = [
    ("Literata", "ital,opsz,wght@0,7..72,400..700;1,7..72,400..700", "literata"),
    ("Atkinson Hyperlegible Next", "ital,wght@0,400..700;1,400..700",
     "atkinsonhyperlegiblenext"),
    ("JetBrains Mono", "ital,wght@0,400..700;1,400..700", "jetbrainsmono"),
]
SUBSETS = ("latin", "latin-ext")

# Muuttujat, jotka Zensicalin base.html asettaisi theme.font-asetuksesta;
# theme.font: false jättää ne pois (mkdocs-pohja.yml).
THEME_FONTS = {"--md-text-font": "Source Sans 3", "--md-code-font": "JetBrains Mono"}

CSS_API = "https://fonts.googleapis.com/css2"

# Google valitsee tiedostomuodon User-Agentista: Chrome ja Firefox saavat
# samat woff2-tiedostot, Safari omansa. Tästä tulee kaikille Chromen versio.
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")

BLOCK = re.compile(r"/\* (?P<subset>[\w-]+) \*/\n@font-face \{\n(?P<body>.*?)\n\}", re.S)
SRC = re.compile(r"src: url\((?P<url>[^)]+)\) format\('woff2'\);")
STYLE = re.compile(r"font-style: (\w+);")
VERSION = re.compile(r"/s/[^/]+/(v\d+)/")


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def slug(family: str) -> str:
    return family.lower().replace(" ", "-")


def write_if_changed(path: Path, data: bytes) -> bool:
    if path.is_file() and path.read_bytes() == data:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return True


class Store:
    """assets/fonts/: kirjoitetut tiedostot ja ajon lopuksi poistettavat."""

    def __init__(self):
        self.wanted: set[Path] = set()
        self.changed = 0

    def font(self, relative: str, url: str) -> None:
        data = fetch(url)
        if data[:4] != b"wOF2":
            sys.exit(f"{url}: ei ole woff2-tiedosto")
        if self.put(FONTS / relative, data):
            print(f"haettu {relative} ({len(data) // 1024} KiB)")

    def license(self, family: str, url: str) -> None:
        target = FONTS / slug(family) / "OFL.txt"
        if self.put(target, fetch(url)):
            print(f"haettu {target.relative_to(TOOL)}")

    def put(self, target: Path, data: bytes) -> bool:
        self.wanted.add(target)
        if write_if_changed(target, data):
            self.changed += 1
            return True
        return False

    def prune(self) -> None:
        for stale in sorted(FONTS.rglob("*")):
            if stale.is_file() and stale not in self.wanted:
                stale.unlink()
                print(f"poistettu {stale.relative_to(TOOL)}")


def adobe_rules(store: Store) -> tuple[list[str], list[str]]:
    """Adoben perheet. -> (@font-face-säännöt, versiot otsikkoon)."""
    rules, versions = [], []
    for family, repo, tag, files, weights in ADOBE:
        base = f"{RAW}/adobe-fonts/{repo}/{tag}"
        for style, path in files.items():
            relative = f"{slug(family)}/{style}.woff2"
            store.font(relative, f"{base}/{path}")
            rules.append(f"/* {family} {tag}: {path} */\n@font-face {{\n"
                         f"  font-family: '{family}';\n"
                         f"  font-style: {style};\n"
                         f"  font-weight: {weights};\n"
                         f"  font-display: swap;\n"
                         f'  src: url("../fonts/{relative}") format("woff2");\n}}')
        store.license(family, f"{base}/LICENSE.md")
        versions.append(f"{family} {tag} (Adobe)")
    return rules, versions


def google_rules(store: Store) -> tuple[list[str], list[str]]:
    """Google Fontsin perheet. -> (@font-face-säännöt, versiot otsikkoon)."""
    query = "&".join(f"family={family.replace(' ', '+')}:{axes}" for family, axes, _ in GOOGLE)
    css = fetch(f"{CSS_API}?{query}&display=swap").decode("utf-8")
    rules, seen = [], {}
    for match in BLOCK.finditer(css):
        subset, body = match["subset"], match["body"]
        if subset not in SUBSETS:
            continue
        family = re.search(r"font-family: '([^']+)';", body)[1]
        style = STYLE.search(body)[1]
        url = SRC.search(body)["url"]
        seen.setdefault(family, VERSION.search(url)[1])
        relative = f"{slug(family)}/{style}-{subset}.woff2"
        store.font(relative, url)
        local = SRC.sub(f'src: url("../fonts/{relative}") format("woff2");', body)
        rules.append(f"/* {subset} */\n@font-face {{\n{local}\n}}")
    missing = [family for family, _, _ in GOOGLE if family not in seen]
    if missing:
        sys.exit(f"rajapinta ei antanut kaikkia perheitä: {missing}")
    for family, _, directory in GOOGLE:
        store.license(family, f"{RAW}/google/fonts/main/ofl/{directory}/OFL.txt")
    return rules, [f"{family} {seen[family]} (Google Fonts)" for family, _, _ in GOOGLE]


def main() -> int:
    store = Store()
    adobe, adobe_versions = adobe_rules(store)
    google, google_versions = google_rules(store)
    store.prune()

    listed = textwrap.fill(
        "Versiot: " + ", ".join(adobe_versions + google_versions) + ".",
        width=76, initial_indent=" * ", subsequent_indent=" * ")
    header = f"""/* Kirjasimet sivuston omasta assets/fonts/-hakemistosta.
 *
 * GENEROITU: skriptit/fontit.py kirjoittaa tämän tiedoston, älä muokkaa käsin.
 * Source Sans 3 ja Source Serif 4 ovat Adoben omat muuttuvat tiedostot
 * (koko merkistö), muut Google Fontsin palvelemat tiedostot merkistöittäin
 * (latin, latin-ext); miksi näin, ks. skriptin alku ja PERUSTELUT.md.
{listed}
 *
 * Kaikki perheet ovat SIL OFL 1.1 -lisensoituja; lisenssi on perheen
 * hakemistossa (OFL.txt) ja kopioituu sivustolle tiedostojen mukana.
 *
 * Otsikoiden, valikon ja koodin kirjasin annetaan teeman muuttujissa, jotka
 * Zensicalin base.html jättää pois, kun mkdocs-pohja.yml asettaa
 * theme.font: false. Source Sans 3 on leipätekstin Source Serif 4:n
 * sisarkirjasin, joten mittasuhteet täsmäävät. Leipäteksti ja
 * kirjasinvalikon vaihtoehdot ovat typography.css:ssä. Esilataus:
 * overrides/main.html. */

"""
    variables = "\n".join(f"  {name}: \"{value}\";" for name, value in THEME_FONTS.items())
    text = header + "\n\n".join(adobe + google) + f"\n\n:root {{\n{variables}\n}}\n"
    if write_if_changed(CSS, text.encode("utf-8")):
        store.changed += 1
        print(f"kirjoitettu {CSS.relative_to(TOOL)}")
    print(f"{len(adobe) + len(google)} sääntöä, {len(store.wanted)} tiedostoa, "
          f"{store.changed} muuttunut")
    return 0


if __name__ == "__main__":
    sys.exit(main())
