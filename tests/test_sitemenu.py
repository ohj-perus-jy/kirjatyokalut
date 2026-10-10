"""Sivustovalikko kurssin nimen vieressä koekirjalla, selaimessa.

Lista on mallissa (mkdocs.yml: extra.sites), mutta avaaminen, sulkeminen ja
näppäimistö syntyvät vasta selaimessa.
"""

import pytest

JYPELI = "https://jypeli.it.jyu.fi/"


@pytest.fixture(scope="module")
def base_url(book, serve):
    return serve(book.site)


def open_page(browser, url, **options):
    """Avaa sivun ja kerää skriptivirheet. -> (sivu, virheet)."""
    page = browser.new_page(**options)
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(url, wait_until="load")
    return page, errors


def items(page) -> list[dict]:
    return page.evaluate(
        """[...document.querySelectorAll('.jyu-sites__item')].map(a => ({
            name: a.textContent.trim(),
            href: a.href,
            current: a.hasAttribute('aria-current'),
        }))""")


def test_the_menu_lists_this_site_and_jypeli(browser, base_url):
    """Oma sivusto on merkitty ja vie omalle etusivulle (ei tuotanto-osoitteeseen,
    jotta /dev/ ja localhost pysyvät itsessään); Jypeli vie ulos. Alasivulla
    oman sivuston linkki on sama kuin kurssin nimen."""
    page, errors = open_page(browser, f"{base_url}/osa1/")
    assert page.is_hidden(".jyu-sites__list")
    assert page.get_attribute(".jyu-sites__button", "aria-expanded") == "false"
    home = page.evaluate("document.querySelector('.jyu-sites .md-ellipsis a').href")
    assert home == f"{base_url}/"
    assert items(page) == [
        {"name": "Ohjelmointi 1", "href": home, "current": True},
        {"name": "Jypeli-ohjeet", "href": JYPELI, "current": False},
    ]
    assert errors == []


def popup(page) -> dict:
    """Painikkeen ponnahdusattribuutit ja listan roolit."""
    return page.evaluate(
        """(() => { const b = document.querySelector('.jyu-sites__button');
            const target = document.getElementById(b.getAttribute('aria-controls'));
            return { haspopup: b.getAttribute('aria-haspopup'),
                     expanded: b.getAttribute('aria-expanded'),
                     role: target && target.getAttribute('role'),
                     items: target && [...target.querySelectorAll('li, a')]
                         .map(e => e.getAttribute('role')) } })()""")


def test_the_button_tells_it_opens_a_menu(browser, base_url):
    """Ruudunlukija kertoo, että painike avaa valikon, vasta aria-haspopupista.
    Lista on ARIA:n valikkopainike (menu/menuitem) kuten kirjasinvalikon
    paneeli on dialogi: yläpalkin painikkeet kertovat ponnahduksensa samalla
    tavalla. Teema poistaa aria-haspopupin ja aria-controlsin vihjeensä
    sulkeutuessa, myös sivun alussa, ja tooltips.js palauttaa ne."""
    page, errors = open_page(browser, base_url)
    expected = {"haspopup": "true", "expanded": "false", "role": "menu",
                "items": ["none", "menuitem", "none", "menuitem"]}
    assert popup(page) == expected
    page.hover(".jyu-sites__button")
    assert hints(page) == ["Vaihda sivustoa"]
    page.mouse.move(10, 400)
    assert hints(page) == []
    assert popup(page) == expected
    assert errors == []


def test_the_button_opens_and_an_outside_click_closes(browser, base_url):
    page, errors = open_page(browser, base_url)
    page.click(".jyu-sites__button")
    assert page.is_visible(".jyu-sites__list")
    assert page.get_attribute(".jyu-sites__button", "aria-expanded") == "true"
    # Lista ei saa leikkautua nimen ellipsikseen: kohta on oikeasti osuttavissa.
    page.hover(".jyu-sites__item >> nth=1")
    assert page.evaluate(
        "document.querySelector('.jyu-sites__item:hover') !== null")

    page.click(".md-content")
    assert page.is_hidden(".jyu-sites__list")
    assert page.get_attribute(".jyu-sites__button", "aria-expanded") == "false"

    page.click(".jyu-sites__button")
    page.click(".jyu-sites__button")
    assert page.is_hidden(".jyu-sites__list")
    assert errors == []


def test_the_menu_works_from_the_keyboard(browser, base_url):
    """Nuoli alas avaa ja kohdistaa ensimmäiseen, nuolet kiertävät, Esc sulkee
    ja palauttaa kohdistuksen; kohdistuksen poistuminen sulkee."""
    page, errors = open_page(browser, base_url)
    focused = "document.activeElement.textContent.trim()"
    page.focus(".jyu-sites__button")
    page.keyboard.press("ArrowDown")
    assert page.is_visible(".jyu-sites__list")
    assert page.evaluate(focused) == "Ohjelmointi 1"
    page.keyboard.press("ArrowDown")
    assert page.evaluate(focused) == "Jypeli-ohjeet"
    page.keyboard.press("ArrowDown")
    assert page.evaluate(focused) == "Ohjelmointi 1"
    page.keyboard.press("Escape")
    assert page.is_hidden(".jyu-sites__list")
    assert page.evaluate("document.activeElement.id") == "jyu-sites-button"

    page.keyboard.press("Enter")
    assert page.is_visible(".jyu-sites__list")
    page.keyboard.press("Tab")
    page.keyboard.press("Tab")
    page.keyboard.press("Tab")
    assert page.is_hidden(".jyu-sites__list")
    assert errors == []


def hints(page) -> list[str]:
    """Näkyvien teeman vihjeiden (content.tooltips) tekstit. Teema lisää
    vihjeen bodyyn, kun painikkeella on osoitin tai kohdistus, ja poistaa sen
    250 ms niiden lähdettyä."""
    page.wait_for_timeout(500)
    return page.locator(".md-tooltip2:visible").all_inner_texts()


def test_the_hint_does_not_cover_the_list(browser, base_url):
    """Painettu painike pitää kohdistuksen, joten vihje jäisi listan päälle.
    Listan ollessa auki vihje on piilossa ja palaa, kun lista suljetaan
    näppäimistöllä."""
    page, errors = open_page(browser, base_url)
    page.hover(".jyu-sites__button")
    assert hints(page) == ["Vaihda sivustoa"]
    page.click(".jyu-sites__button")
    assert page.is_visible(".jyu-sites__list")
    assert hints(page) == []
    page.keyboard.press("Escape")
    assert page.is_hidden(".jyu-sites__list")
    assert hints(page) == ["Vaihda sivustoa"]
    assert errors == []


def test_the_hint_does_not_stay_open_after_the_mouse(browser, base_url):
    """Hiirellä suljettaessa kohdistus ei jää painikkeeseen, koska vihje
    pysyisi silloin auki osoittimen lähdettyä."""
    page, errors = open_page(browser, base_url)
    page.click(".jyu-sites__button")
    page.click(".jyu-sites__button")
    assert page.is_hidden(".jyu-sites__list")
    page.mouse.move(10, 400)
    assert hints(page) == []

    page.click(".jyu-sites__button")
    page.click(".md-content")
    page.mouse.move(10, 400)
    assert hints(page) == []
    assert errors == []


def test_choosing_jypeli_leaves_the_site(browser, base_url):
    """Kohta on tavallinen linkki: sama välilehti, ei skriptiä välissä."""
    page, errors = open_page(browser, base_url)
    page.route(JYPELI + "**", lambda route: route.fulfill(
        status=200, content_type="text/html", body="<title>Jypeli</title>"))
    page.click(".jyu-sites__button")
    page.click(".jyu-sites__item >> nth=1")
    page.wait_for_url(JYPELI)
    assert page.title() == "Jypeli"
    assert errors == []


def test_the_menu_fits_a_phone(browser, base_url):
    """Painike mahtuu nimen viereen eikä lista tuo vaakavieritystä."""
    page, errors = open_page(
        browser, base_url, viewport={"width": 390, "height": 800})
    page.click(".jyu-sites__button")
    box = page.evaluate(
        """(() => {
            const r = document.querySelector('.jyu-sites__list').getBoundingClientRect();
            return {left: r.left, right: r.right};
        })()""")
    assert 0 <= box["left"] and box["right"] <= 390
    assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
    assert errors == []


@pytest.mark.parametrize("width, shown", [(1400, True), (800, False)])
def test_a_scrolled_page_hides_the_menu_only_on_a_narrow_screen(browser, base_url, width, shown):
    """Vieritetyllä sivulla teema merkitsee otsikon tilaan --active. Kapealla
    näytöllä nimi ja valikko väistyvät silloin sivun otsikon tieltä; työpöydällä
    ne pysyvät, eikä piilotussääntö saa vaikuttaa siellä painikkeeseen lainkaan."""
    page, errors = open_page(
        browser, base_url, viewport={"width": width, "height": 800})
    page.evaluate("document.querySelector('.md-header__title')"
                  ".classList.add('md-header__title--active')")
    button = "getComputedStyle(document.querySelector('.jyu-sites__button'))"
    if shown:
        assert page.evaluate(f"{button}.transitionProperty") != "visibility"
        page.wait_for_timeout(300)  # piilotuksen viive on 0,15 s
        assert page.evaluate(f"{button}.visibility") == "visible"
    else:
        page.wait_for_function(f"{button}.visibility === 'hidden'")
    assert errors == []
