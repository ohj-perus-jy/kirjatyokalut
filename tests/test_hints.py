"""Opastusnuolet koodilohkon nappeihin (README.md: copyhint, playhint,
eyehint) koekirjan C#-sivulla (osa1/csharp.md).

Aidan määre tulee luokaksi lohkon diviin (convert.py: fence_info), ja
hints.js lisää nuolen määreen nimeämään nappiin. Nuoli on napin lapsi, joten
se on napin kohdalla riippumatta siitä, mitä muita nappeja rivissä on.
Painallus jää localStorageen ("jyu-hints"), joten jokainen testi saa oman
selainkontekstin.
"""

import pytest

HINTED = "div.highlight.copyhint.playhint.eyehint"
MISSING = "div.highlight.noplayground.playhint"
HINT = ".jyu-hint"
BUTTONS = {"copy": "copyhint", "run": "playhint", "hidelines": "eyehint"}


KEY = "jyu-hints"


@pytest.fixture
def url(book, serve) -> str:
    return f"{serve(book.site)}/osa1/csharp/"


@pytest.fixture
def page(browser, url):
    context = browser.new_context()
    opened = context.new_page()
    errors: list[str] = []
    opened.on("pageerror", lambda error: errors.append(str(error)))
    opened.goto(url, wait_until="load")
    yield opened
    assert errors == []
    context.close()


def test_each_attribute_puts_an_arrow_under_its_button(page):
    """Yhdessä lohkossa kaikki kolme määrettä: jokaisessa napissa oma nuoli,
    napin nimi ja vihje ennallaan (nuoli on aria-hidden)."""
    block = page.locator(HINTED)
    assert block.count() == 1
    for type_ in BUTTONS:
        button = block.locator(f"[data-md-type={type_}]")
        assert button.locator(f":scope > {HINT}").count() == 1, type_
        assert button.locator(HINT).get_attribute("aria-hidden") == "true"
        # Nuoli on napin alla keskellä, ei sen päällä.
        box = button.bounding_box()
        arrow = button.locator(HINT).bounding_box()
        assert arrow["y"] >= box["y"] + box["height"], type_
        assert box["x"] < arrow["x"] + arrow["width"] / 2 < box["x"] + box["width"], type_
    assert block.locator("[data-md-type=hidelines]").get_attribute(
        "aria-label") == "Näytä piilotetut rivit"


def test_other_blocks_have_no_arrows(page):
    assert page.locator(f"div.highlight:not({HINTED}) {HINT}").count() == 0


def test_missing_button_gets_no_arrow(page):
    """noplayground-lohkossa ei ole ajonappia, joten playhint ei tee mitään
    eikä nuoli jää ilman nappia leijumaan."""
    block = page.locator(MISSING)
    assert block.count() == 1
    assert block.locator("[data-md-type=run]").count() == 0
    assert block.locator(HINT).count() == 0


def test_the_first_press_removes_only_that_arrow(page):
    """Opastus on tehnyt tehtävänsä, kun lukija painaa nappia: sen nuoli
    poistuu eikä palaa, mutta muiden nappien nuolet jäävät."""
    page.context.grant_permissions(["clipboard-read", "clipboard-write"])
    block = page.locator(HINTED)
    block.locator("[data-md-type=hidelines]").click()
    assert block.locator(f"[data-md-type=hidelines] {HINT}").count() == 0
    assert block.inner_text().startswith("public class Hei")
    assert block.locator(HINT).count() == 2

    block.locator("[data-md-type=hidelines]").click()
    assert block.locator(f"[data-md-type=hidelines] {HINT}").count() == 0

    block.locator("[data-md-type=copy]").click()
    assert block.locator(f"[data-md-type=copy] {HINT}").count() == 0
    assert block.locator(HINT).count() == 1


def test_a_press_is_remembered_across_pages(page, url):
    """Painettu napin tyyppi jää localStorageen, eikä sen nuolta näytetä
    uudella latauksella; muiden tyyppien nuolet tulevat yhä."""
    page.locator(f"{HINTED} [data-md-type=hidelines]").click()
    assert page.evaluate(f"JSON.parse(localStorage.getItem('{KEY}'))") == ["hidelines"]

    page.goto(url, wait_until="load")
    block = page.locator(HINTED)
    assert block.locator(f"[data-md-type=hidelines] {HINT}").count() == 0
    assert block.locator(f"[data-md-type=copy] {HINT}").count() == 1
    assert block.locator(f"[data-md-type=run] {HINT}").count() == 1


def test_any_button_of_the_type_teaches_it(page, url):
    """Myös nuolettoman lohkon silmä opettaa silmän: painallus siinä poistaa
    opastetun lohkon nuolen ja jää muistiin."""
    page.locator("div.highlight.language-csharp:not(.eyehint) [data-md-type=hidelines]").first.click()
    assert page.locator(f"{HINTED} [data-md-type=hidelines] {HINT}").count() == 0
    assert page.evaluate(f"JSON.parse(localStorage.getItem('{KEY}'))") == ["hidelines"]


def test_a_broken_memory_is_ignored(browser, url):
    """Vieras arvo avaimessa ei kaada skriptiä: nuolet tulevat kuin muistia
    ei olisi."""
    context = browser.new_context()
    opened = context.new_page()
    errors: list[str] = []
    opened.on("pageerror", lambda error: errors.append(str(error)))
    opened.goto(url, wait_until="load")
    opened.evaluate(f"localStorage.setItem('{KEY}', '{{bad')")
    opened.goto(url, wait_until="load")
    assert opened.locator(f"{HINTED} {HINT}").count() == 3
    assert errors == []
    context.close()
