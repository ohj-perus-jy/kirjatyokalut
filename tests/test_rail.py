"""Päävalikon piilotuspainike koekirjalla, selaimessa.

Painike on mallissa (overrides/partials/header.html), mutta piilotus,
tallennus ja näppäin syntyvät vasta selaimessa (assets/js/rail.js,
assets/css/layout.css). Vain työpöydällä eli kiskon leveyksillä.
"""

import pytest
from test_layout import pixel, same

KEY = "jyu-rail"
BUTTON = ".jyu-rail-button"
RAIL = ".md-sidebar--primary"
CONTENT = ".md-content__inner"
TITLE = ".jyu-sites .md-ellipsis a"
DESKTOP = {"width": 1280, "height": 600}
NARROW = {"width": 1000, "height": 600}
HIDE_ON_LOAD = f"localStorage.setItem('{KEY}', 'hidden')"
# Hakuikkunan shadow-juuri (tests/test_search.py).
SHADOW = "[...document.body.children].find(el => el.shadowRoot).shadowRoot"


@pytest.fixture(scope="module")
def base_url(book, serve):
    return serve(book.site)


def open_page(browser, url, viewport=DESKTOP, init_script=None, motion=False):
    """Avaa sivun omassa kontekstissa ja kerää skriptivirheet. -> (sivu, virheet).
    Ilman liikettä, jotta mitat ovat lopulliset heti painalluksen jälkeen;
    häivytys testataan erikseen (motion=True)."""
    context = browser.new_context(viewport=viewport,
                                  reduced_motion="no-preference" if motion else "reduce")
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    if init_script:
        page.add_init_script(init_script)
    page.goto(url, wait_until="load")
    return page, errors


def hidden(page) -> bool:
    return page.evaluate("document.documentElement.getAttribute('data-jyu-rail')") == "hidden"


def stored(page) -> str | None:
    return page.evaluate(f"localStorage.getItem('{KEY}')")


def hints(page) -> list[str]:
    """Näkyvien teeman vihjeiden tekstit (ks. test_sitemenu.hints)."""
    page.wait_for_timeout(500)
    return page.locator(".md-tooltip2:visible").all_inner_texts()


def test_the_button_hides_the_rail_and_moves_the_text_over(browser, base_url):
    """Painallus piilottaa kiskon: teksti siirtyy sen paikalle, kurssin nimi
    jää yläpalkkiin ja painike kertoo tilan. Toinen painallus palauttaa."""
    page, errors = open_page(browser, f"{base_url}/osa1/")
    assert page.is_visible(RAIL)
    assert page.get_attribute(BUTTON, "aria-expanded") == "true"
    before = page.locator(CONTENT).bounding_box()["x"]

    page.click(BUTTON)
    assert hidden(page)
    assert page.is_hidden(RAIL)
    assert page.locator(CONTENT).bounding_box()["x"] < before
    assert page.is_visible(TITLE)
    assert page.is_visible(BUTTON)
    assert page.get_attribute(BUTTON, "aria-expanded") == "false"
    assert stored(page) == "hidden"

    page.click(BUTTON)
    assert not hidden(page)
    assert page.is_visible(RAIL)
    assert page.locator(CONTENT).bounding_box()["x"] == before
    assert page.get_attribute(BUTTON, "aria-expanded") == "true"
    assert stored(page) is None
    assert errors == []


PLACES = """() => {
    const box = s => document.querySelector(s).getBoundingClientRect()
    const content = box('.md-content__inner')
    return { button: box('.jyu-rail-button').left, title: box('.jyu-sites').left,
             toc: box('.md-sidebar--secondary').left, footer: box('.md-footer').right,
             content_left: content.left, content_right: content.right,
             plate: parseFloat(getComputedStyle(document.querySelector('.md-footer')).marginLeft) }
}"""


def test_the_rest_of_the_page_stays_put(browser, base_url):
    """Leveällä näytöllä teksti levenee kiskon paikalle; sisällysluettelo,
    levyn oikea reuna, alatunniste ja yläpalkki painikkeineen ja kurssin
    nimineen eivät liiku eikä sivu kapene."""
    page, errors = open_page(browser, f"{base_url}/osa1/", viewport={"width": 1920, "height": 700})
    before = page.evaluate(PLACES)
    rail = page.locator(RAIL).bounding_box()
    page.click(BUTTON)
    after = page.evaluate(PLACES)
    for key in ("button", "title", "toc", "footer", "content_right"):
        assert after[key] == before[key], key
    assert after["content_left"] == before["content_left"] - rail["width"]
    assert after["plate"] == pytest.approx(rail["x"] + 0.9, abs=0.05)
    # Levyn vasemmalla puolella on sivun pohjaa ikkunan reunaan asti eikä
    # kiskon reunaviivaa: kiskon paikka, sen entinen reuna ja levyn
    # ulkopuolinen reuna ovat tekstipalstan väriset. y heti yläpalkin alla.
    y = page.locator(".md-header").bounding_box()["height"] + 4
    content = pixel(page, after["content_left"] + 4, y)
    for x in (2, rail["x"] + 5, rail["x"] + rail["width"], rail["x"] + rail["width"] + 1):
        assert same(pixel(page, x, y), content), x
    assert errors == []


def test_the_change_fades_unless_motion_is_reduced(browser, base_url):
    """Kisko häipyy ja levyn reuna liukuu kiskon paikalle (rekisteröidyt
    muuttujat bodyllä); vähemmän liikettä pyytävälle tila vaihtuu kerralla."""
    page, errors = open_page(browser, base_url, motion=True)
    page.click(BUTTON)
    # Muut siirtymät (painikkeen hover, kiskon vierityspalkki) eivät kuulu tähän.
    running = page.evaluate("""document.getAnimations().map(a =>
        `${a.effect.target.localName}:${a.transitionProperty}`)""")
    assert {"body:--jyu-levy-left", "body:--jyu-levy-edge", "body:--jyu-levy-hair",
            "body:--jyu-left-bg", "div:opacity", "div:transform",
            "div:visibility"} <= set(running)
    page.wait_for_timeout(400)
    assert page.is_hidden(RAIL)
    assert errors == []

    still, errors = open_page(browser, base_url)
    still.click(BUTTON)
    assert still.evaluate("document.getAnimations().length") == 0
    assert errors == []


def test_the_hint_names_the_action(browser, base_url):
    """Vihje kertoo, mitä painallus tekee, ja vaihtuu tilan mukana. Hiirellä
    painettu painike ei pidä vihjettä auki osoittimen lähdettyä."""
    page, errors = open_page(browser, base_url)
    page.hover(BUTTON)
    assert hints(page) == ["Piilota valikko"]
    page.click(BUTTON)
    page.mouse.move(600, 400)
    assert hints(page) == []
    page.hover(BUTTON)
    assert hints(page) == ["Näytä valikko"]
    assert page.get_attribute(BUTTON, "aria-label") == "Näytä valikko"
    assert errors == []


def test_the_choice_holds_on_the_next_page(browser, base_url):
    """Tallennettu piilotus on voimassa heti sivun auetessa: attribuutti
    asetetaan ennen sisältöä, joten kisko ei välähdä."""
    page, errors = open_page(browser, f"{base_url}/osa1/", init_script=HIDE_ON_LOAD)
    assert hidden(page)
    assert page.is_hidden(RAIL)
    assert page.get_attribute(BUTTON, "aria-expanded") == "false"
    assert page.get_attribute(BUTTON, "aria-label") == "Näytä valikko"
    page.click(".md-footer__link--next")
    page.wait_for_load_state("load")
    assert hidden(page)
    assert page.is_hidden(RAIL)
    assert errors == []


def test_b_toggles_the_rail_but_not_while_typing(browser, base_url):
    """b-näppäin kytkee kiskon kuten Ctrl+K avaa haun; hakukentässä (shadow
    DOM, ks. test_search) kirjoitettu b ei vaikuta."""
    page, errors = open_page(browser, base_url)
    page.keyboard.press("b")
    assert hidden(page)
    page.keyboard.press("b")
    assert not hidden(page)
    page.keyboard.press("Control+k")
    page.wait_for_function(f"{SHADOW}.activeElement?.localName === 'input'")
    page.keyboard.type("b")
    assert not hidden(page)
    assert errors == []


def test_the_active_chapter_is_in_view_when_the_rail_returns(browser, base_url):
    """Piilotettuna avatun sivun kisko ei ole vierinyt lukukohtaan (teema
    vierittää vain sivun latautuessa), joten kiskon palatessa avoin luku
    vieritetään näkyviin. Matala ikkuna, jotta lista ei mahdu kerralla."""
    page, errors = open_page(browser, f"{base_url}/osa2/03-sisallytys/",
                             viewport={"width": 1280, "height": 260},
                             init_script=HIDE_ON_LOAD)
    page.click(BUTTON)
    assert page.evaluate("""() => {
        const wrap = document.querySelector('.md-sidebar--primary .md-sidebar__scrollwrap');
        const active = wrap.querySelector('.md-nav__link--active');
        const area = wrap.getBoundingClientRect(), box = active.getBoundingClientRect();
        return wrap.scrollHeight > wrap.clientHeight
            && box.top >= area.top && box.bottom <= area.bottom }""")
    assert errors == []


def test_narrow_screens_keep_the_drawer(browser, base_url):
    """Kapealla näytöllä valikko on teeman laatikko: painike on piilossa,
    hampurilainen avaa laatikon, ja tallennettu piilotus ei vaikuta."""
    page, errors = open_page(browser, base_url, viewport=NARROW, init_script=HIDE_ON_LOAD)
    assert page.is_hidden(BUTTON)
    assert page.is_visible(".md-header__button[for='__drawer']")
    page.click(".md-header__button[for='__drawer']")
    assert page.is_visible(f"{RAIL} .md-nav__link")
    assert errors == []


def test_the_header_has_no_logo(browser, base_url):
    """Yläpalkissa kurssin nimi on kotilinkki, eikä kirjakuvaketta ole;
    kapean näytön laatikon otsikossa kuvake on yhä."""
    page, errors = open_page(browser, base_url)
    assert page.locator(".md-header .md-logo").count() == 0
    assert page.locator(f"{RAIL} .md-nav__title .md-logo").count() == 1
    assert errors == []
