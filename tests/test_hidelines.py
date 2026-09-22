"""Piilorivit koekirjalla (README.md kohta 2).

convert.py riisuu etuliitteen ja kirjoittaa rivinumerot aidan attribuutiksi
(test_convert.py); selain piilottaa rivit ja lisää silmänapin. Jälkimmäinen
näkyy vasta selaimessa. Koekirjan lohkossa piilorivit ovat 1 ja 3.
"""

import pytest

BLOCK = "div.highlight[data-hidden]"
EYE = "[data-md-type=hidelines]"
COPY = "[data-md-type=copy]"


@pytest.fixture(scope="session")
def chapter_url(book, serve) -> str:
    return f"{serve(book.site)}/osa1/01-hei/"


@pytest.fixture
def page(browser, chapter_url):
    """Oma sivu joka testille: silmänappi jättää jälkensä sivulle."""
    opened = browser.new_page()
    errors: list[str] = []
    opened.on("pageerror", lambda error: errors.append(str(error)))
    opened.goto(chapter_url, wait_until="load")
    yield opened
    assert errors == []
    opened.close()


def test_hidden_lines_are_in_the_page_but_not_visible(page):
    """Rivi on HTML:ssä tallessa (ajonappi lähettää sen); vain näkyminen on
    kiinni luokasta."""
    assert page.get_attribute(BLOCK, "data-hidden") == "1 3"
    assert page.inner_text(BLOCK).strip() == 'IO.println("Hei, maailma!");'
    assert page.eval_on_selector(BLOCK, "block => block.textContent") == (
        'void main() {\nIO.println("Hei, maailma!");\n}\n')


def test_the_marked_lines_are_the_hidden_ones(page):
    """Numerot osoittavat Pygmentsin rivispaneihin: rivi 1 ja 3, ei muita."""
    assert page.eval_on_selector_all(
        f"{BLOCK} code > span",
        "lines => lines.map(line => line.classList.contains('boring'))") == [
        True, False, True]


def test_the_eye_shows_and_hides_them(page):
    """Ensimmäinen painallus näyttää piilorivit, toinen piilottaa."""
    page.click(f"{BLOCK} {EYE}")
    assert page.inner_text(BLOCK).startswith("void main() {")
    assert page.get_attribute(f"{BLOCK} {EYE}", "title") == "Piilota rivit"
    assert page.get_attribute(f"{BLOCK} {EYE}", "aria-pressed") == "true"

    page.click(f"{BLOCK} {EYE}")
    assert "void main() {" not in page.inner_text(BLOCK)
    assert page.get_attribute(f"{BLOCK} {EYE}", "title") == "Näytä piilotetut rivit"
    assert page.get_attribute(f"{BLOCK} {EYE}", "aria-pressed") == "false"


def test_only_blocks_with_hidden_lines_get_an_eye(page):
    """Koekirjan neljästä koodilohkosta vain yhdessä on piilorivejä."""
    assert page.eval_on_selector_all(EYE, "buttons => buttons.length") == 1


def test_all_buttons_share_one_row(page):
    """Teeman kopiointinappi, ajonappi ja silmä ovat samassa nappirivissä, siinä
    järjestyksessä kuin mdBookissa. Teema tekee rivinsä vasta DOMContentLoaded-
    tapahtumassa, joten omat napit odottavat sitä (hidelines.js: afterTheme)."""
    assert page.eval_on_selector_all(f"{BLOCK} nav.md-code__nav", "navs => navs.length") == 1
    assert page.eval_on_selector_all(
        f"{BLOCK} nav.md-code__nav button",
        "buttons => buttons.map(button => button.dataset.mdType)") == [
        "copy", "run", "hidelines"]


def test_copy_takes_hidden_lines_only_when_shown(page):
    """Kopiointinappi kopioi näkyvän koodin: piilorivit tulevat mukaan vasta,
    kun lukija on ottanut ne esiin silmällä. Rivi 1 on korostettu, joten
    kopioinnin ajaksi vaihtuva display (highlights.css) ei saa paljastaa sitä."""
    page.context.grant_permissions(["clipboard-read", "clipboard-write"])
    page.click(f"{BLOCK} {COPY}")
    assert page.evaluate("navigator.clipboard.readText()") == (
        'IO.println("Hei, maailma!");')

    page.click(f"{BLOCK} {EYE}")
    page.click(f"{BLOCK} {COPY}")
    assert page.evaluate("navigator.clipboard.readText()") == (
        'void main() {\nIO.println("Hei, maailma!");\n}')


def test_copy_is_acknowledged_beside_the_button(page):
    """Kuittaus tulee nappirivin alkuun, kopiointinapin vasemmalle puolelle,
    eikä teeman ilmoitukseen sivun alakulmassa (copy.js)."""
    page.context.grant_permissions(["clipboard-read", "clipboard-write"])
    page.click(f"{BLOCK} {COPY}")
    # Kuittaus tulee vasta leikepöydän luvattua (async), joten sitä odotetaan.
    note = page.locator(f"{BLOCK} nav.md-code__nav > .jyu-copied--shown")
    note.wait_for()
    assert note.evaluate("note => note.previousElementSibling") is None
    assert note.inner_text() == "Kopioitu leikepöydälle"
    assert page.get_attribute(".md-dialog", "data-md-state") is None
    assert page.get_attribute(f"{BLOCK} {COPY}", "data-clipboard-target") is None
