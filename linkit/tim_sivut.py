"""Kirjan TIM-kansioiden julkiset sivut lycheen syötteeksi, yksi URL riville.

    python3 tim_sivut.py [kirja.toml] > tim-sivut.txt

Kansiot ja pois jätettävät sivut ovat kirja.toml:n [linkit]-osiossa.
TIMin getItems näyttää kirjautumatta vain julkiset dokumentit.
"""

import json
import sys
import tomllib
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterator
from pathlib import Path

TIM = "https://tim.jyu.fi"

# Oletuksena kirja.toml, jonka alla työkalut ovat (zensical/tyokalut/linkit).
CONFIG = Path(__file__).resolve().parent.parent.parent / "kirja.toml"


def items(folder: str, agent: str = "kirja-linkit") -> list[dict]:
    url = f"{TIM}/getItems?folder={urllib.parse.quote(folder)}"
    request = urllib.request.Request(url, headers={"User-Agent": agent})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def documents(folder: str, fetch: Callable[[str], list[dict]]) -> Iterator[str]:
    """Kansion dokumenttien polut alikansioineen."""
    for item in fetch(folder):
        if item["isFolder"]:
            yield from documents(item["path"], fetch)
        else:
            yield item["path"]


def pages(config: dict, fetch: Callable[[str], list[dict]]) -> list[str]:
    linkit = config.get("linkit", {})
    skip = set(linkit.get("tim_pois", []))
    return [f"{TIM}/view/{path}"
            for folder in linkit.get("tim_kansiot", [])
            for path in documents(folder, fetch) if path not in skip]


def main(argv: list[str]) -> int:
    path = Path(argv[1]) if len(argv) > 1 else CONFIG
    config = tomllib.loads(path.read_text(encoding="utf-8"))
    agent = f"{config.get('nimi', 'kirja')}-linkit"
    urls = pages(config, lambda folder: items(folder, agent))
    if not urls:
        print(f"{path}: [linkit] tim_kansiot ei tuota yhtään sivua", file=sys.stderr)
        return 1
    print("\n".join(urls))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
