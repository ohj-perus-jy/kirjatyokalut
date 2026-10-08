#!/usr/bin/env python3
"""Kirjasintiedostot Google Fontsista työkalujen omaan assets/fonts/-hakemistoon.

    python3 skriptit/fontit.py

Hakee Google Fontsin CSS-rajapinnasta samat tiedostot, jotka se palvelisi
selaimelle (woff2-kelpoinen User-Agent, muuttuvat kirjasimet), säilyttää
latin- ja latin-ext-merkistöt, tallentaa tiedostot perheittäin
assets/fonts/<perhe>/<tyyli>-<merkistö>.woff2 ja jokaisen perheen OFL.txt:n
google/fonts-reposta sekä kirjoittaa assets/css/fonts.css:n @font-face-säännöt
paikallisilla poluilla. Miksi tiedostot ovat repossa: PERUSTELUT.md, Kirjasimet.

Skripti on deterministinen: ilman muutoksia Googlen päässä se ei muuta mitään.
Kun Google päivittää perheen (polun /v15/-osa vaihtuu), ajo tuo uudet
tiedostot ja fonts.css:n muutoksen committiin, jolloin ulkoasun muutos
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

# Perhe, css2-rajapinnan akselit (samat kuin aiemmin typography.css:n
# @importissa ja mkdocs-pohja.yml:n theme.font-asetuksessa) ja perheen
# hakemisto google/fonts-repossa (OFL.txt). Teema käyttää Source Sans 3:sta
# painoja 400, 500 ja 700 ja omat tyylit 400–700, joten 300 jää pois.
FAMILIES = [
    ("Source Sans 3", "ital,wght@0,400..700;1,400..700", "sourcesans3"),
    ("Source Serif 4", "ital,opsz,wght@0,8..60,400..700;1,8..60,400..700", "sourceserif4"),
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
LICENSE_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/{}/OFL.txt"

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


def main() -> int:
    query = "&".join(f"family={family.replace(' ', '+')}:{axes}"
                     for family, axes, _ in FAMILIES)
    css = fetch(f"{CSS_API}?{query}&display=swap").decode("utf-8")

    rules: list[str] = []
    versions: dict[str, str] = {}
    wanted: set[Path] = set()
    changed = 0
    for match in BLOCK.finditer(css):
        subset, body = match["subset"], match["body"]
        if subset not in SUBSETS:
            continue
        family = re.search(r"font-family: '([^']+)';", body)[1]
        style = STYLE.search(body)[1]
        url = SRC.search(body)["url"]
        versions.setdefault(family, VERSION.search(url)[1])
        relative = f"{slug(family)}/{style}-{subset}.woff2"
        target = FONTS / relative
        wanted.add(target)
        data = fetch(url)
        if data[:4] != b"wOF2":
            sys.exit(f"{url}: ei ole woff2-tiedosto")
        if write_if_changed(target, data):
            changed += 1
            print(f"haettu {relative} ({len(data) // 1024} KiB)")
        local = SRC.sub(f'src: url("../fonts/{relative}") format("woff2");', body)
        rules.append(f"/* {subset} */\n@font-face {{\n{local}\n}}")

    families = {family for family, _, _ in FAMILIES}
    if set(versions) != families:
        sys.exit(f"rajapinta ei antanut kaikkia perheitä: {sorted(families - set(versions))}")

    for family, _, directory in FAMILIES:
        target = FONTS / slug(family) / "OFL.txt"
        wanted.add(target)
        if write_if_changed(target, fetch(LICENSE_URL.format(directory))):
            changed += 1
            print(f"haettu {target.relative_to(TOOL)}")

    for stale in sorted(FONTS.rglob("*")):
        if stale.is_file() and stale not in wanted:
            stale.unlink()
            print(f"poistettu {stale.relative_to(TOOL)}")

    listed = textwrap.fill(
        "Google Fontsin versiot: "
        + ", ".join(f"{family} {versions[family]}" for family, _, _ in FAMILIES) + ".",
        width=76, initial_indent=" * ", subsequent_indent=" * ")
    header = f"""/* Kirjasimet sivuston omasta assets/fonts/-hakemistosta.
 *
 * GENEROITU: skriptit/fontit.py kirjoittaa tämän tiedoston, älä muokkaa käsin.
 * Tiedostot ja säännöt ovat samat, jotka Google Fonts palvelisi (perheet,
 * akselit ja merkistöt skriptissä); vain polut ovat paikallisia.
{listed}
 *
 * Miksi omat tiedostot eikä Google Fonts: PERUSTELUT.md, Kirjasimet.
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
    text = header + "\n\n".join(rules) + f"\n\n:root {{\n{variables}\n}}\n"
    if write_if_changed(CSS, text.encode("utf-8")):
        changed += 1
        print(f"kirjoitettu {CSS.relative_to(TOOL)}")
    print(f"{len(rules)} sääntöä, {len(wanted)} tiedostoa, {changed} muuttunut")
    return 0


if __name__ == "__main__":
    sys.exit(main())
