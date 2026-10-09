"""Kirjasimet sivuston omasta assets/fonts/-hakemistosta (fonts.css) koekirjalla.

Sivu avataan selaimessa, joka ei saa poistua sivustolta: jos jokin kirjasin
tulisi vielä Google Fontsista, se jäisi lataamatta ja testi huomaisi sen
document.fonts-rajapinnasta. Oikean kirjan sivusto tarkistetaan erikseen
(tests/test_book.py), koska kirjan oma theme.font toisi Google Fontsin takaisin.
"""

import re

import pytest

from conftest import GOOGLE_FONTS, google_font_references

PRELOAD = "link[rel=preload][as=font]"


@pytest.fixture(scope="module")
def base_url(book, serve):
    return serve(book.site)


def loaded_families(page) -> set[str]:
    """Ladattujen kirjasinten perheet ilman lainausmerkkejä."""
    return {family.strip("\"'") for family in page.evaluate(
        "[...document.fonts].filter(f => f.status === 'loaded').map(f => f.family)")}


def test_the_site_does_not_refer_to_google_fonts(book):
    """theme.font: false jättää teeman linkin pois, ja typography.css ei enää
    @importtaa: rakennetussa sivustossa ei ole osoitteita fonts.googleapis.com
    eikä fonts.gstatic.com."""
    assert google_font_references(book.site) == []


def test_the_fonts_load_without_leaving_the_site(browser, base_url):
    """Leipäteksti, otsikot ja koodi saavat kirjasimensa, vaikka selain ei pääse
    sivuston ulkopuolelle, eikä sivu edes yritä hakea kirjasinta sieltä.
    Kirjasinvalikon vaihtoehdot latautuvat samoin, kun ne valitaan."""
    context = browser.new_context()
    outside: list[str] = []
    requested: list[str] = []

    def guard(route):
        url = route.request.url
        if url.startswith(base_url):
            requested.append(url)
            route.continue_()
        else:
            outside.append(url)
            route.abort()

    context.route("**/*", guard)
    page = context.new_page()
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(f"{base_url}/osa1/01-hei/", wait_until="load")
    page.evaluate("document.fonts.ready")
    assert {"Source Serif 4", "Source Sans 3", "JetBrains Mono"} <= loaded_families(page)
    # Oikeat kirjasimet myös käytössä, ei varakirjasin.
    for selector, family in ((".md-content__inner p", "Source Serif 4"),
                             (".md-content__inner h1", "Source Sans 3"),
                             (".md-content__inner pre code", "JetBrains Mono")):
        assert page.evaluate(
            "s => getComputedStyle(document.querySelector(s)).fontFamily", selector
        ).startswith(f'"{family}"')

    page.click(".jyu-font__button")
    page.click(".jyu-font__item[data-font=literata]")
    page.evaluate("document.fonts.ready")
    assert "Literata" in loaded_families(page)
    page.click(".jyu-font__item[data-font=atkinson]")
    page.evaluate("document.fonts.ready")
    assert "Atkinson Hyperlegible Next" in loaded_families(page)

    # Koekirjan kuvasuurennus hakee GLightboxin tyylin unpkg.comista (Zensicalin
    # laajennus), joten ulkopuolisia pyyntöjä voi olla; kirjasimia ei.
    assert [url for url in outside
            if GOOGLE_FONTS.search(url) or url.endswith((".woff2", ".woff", ".ttf"))] == []
    assert errors == []
    fonts = [url for url in requested if url.endswith(".woff2")]
    assert fonts and all(url.startswith(f"{base_url}/assets/fonts/") for url in fonts)
    context.close()


def test_the_body_font_is_preloaded_once(browser, base_url):
    """overrides/main.html esilataa leipätekstin tiedoston. Tiedosto on olemassa,
    ja se haetaan vain kerran: ilman crossorigin-attribuuttia selain hakisi sen
    toisen kerran, kun fonts.css ottaa sen käyttöön."""
    context = browser.new_context()
    fonts: list[tuple[str, int]] = []
    context.on("response", lambda response: response.url.endswith(".woff2")
               and fonts.append((response.url, response.status)))
    page = context.new_page()
    page.goto(base_url, wait_until="load")
    page.evaluate("document.fonts.ready")
    preloaded = page.get_attribute(PRELOAD, "href")
    assert preloaded and preloaded.endswith("/source-serif-4/normal.woff2")
    assert page.get_attribute(PRELOAD, "crossorigin") is not None
    assert page.evaluate("f => document.fonts.check(f)", '1em "Source Serif 4"')
    assert [status for url, status in fonts
            if url.endswith("/source-serif-4/normal.woff2")] == [200]
    context.close()


def test_every_family_ships_its_license(book):
    """OFL vaatii lisenssin jokaisen kopion mukaan: perheen OFL.txt on
    sivustolla tiedostojen vieressä ja nimeää OFL 1.1:n. Adoben Source-perheet
    ovat alkuperäisversioita (varattu nimi "Source"), joten niiden lisenssi
    on Adoben oma; jokainen fonts.css:n tiedosto on olemassa, eikä
    hakemistoissa ole muuta."""
    site = book.site
    css = (site / "assets" / "css" / "fonts.css").read_text(encoding="utf-8")
    sources = re.findall(r'url\("\.\./fonts/([^"]+)"\)', css)
    assert len(sources) == 4 + 12
    fonts = site / "assets" / "fonts"
    for source in sources:
        assert (fonts / source).read_bytes()[:4] == b"wOF2", source
    families = sorted(path.name for path in fonts.iterdir() if path.is_dir())
    assert families == ["atkinson-hyperlegible-next", "jetbrains-mono", "literata",
                        "source-sans-3", "source-serif-4"]
    for family in families:
        license_text = (fonts / family / "OFL.txt").read_text(encoding="utf-8")
        assert "SIL Open Font License, Version 1.1" in license_text
        if family.startswith("source-"):
            assert "Reserved Font Name" in license_text and "Adobe" in license_text
        files = sorted(path.name for path in (fonts / family).iterdir())
        assert files == sorted(["OFL.txt"] + [
            source.split("/")[1] for source in sources if source.startswith(family + "/")])
