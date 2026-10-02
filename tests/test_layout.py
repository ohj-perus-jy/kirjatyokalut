"""Sivun asettelu koekirjalla (assets/css/layout.css).

Asettelu näkyy vasta selaimessa, ja teeman JavaScript mittaa sen, joten sivu
avataan oikeasti. Matala ikkuna, jotta luvun otsikon voi vierittää yläreunaan.
"""

import pytest

TOC = ".md-sidebar--secondary"


@pytest.fixture(scope="session")
def chapter_url(book, serve) -> str:
    return f"{serve(book.site)}/osa1/01-hei/"


@pytest.fixture
def page(browser, chapter_url):
    context = browser.new_context(viewport={"width": 1280, "height": 600})
    page = context.new_page()
    page.goto(chapter_url, wait_until="load")
    yield page
    context.close()


def test_contents_link_highlights_its_own_heading(page):
    """Sisällysluettelon linkistä avattu otsikko korostuu itse eikä edellinen
    kohta: teema mittaa korostuksen rajan .md-main__inner-marginaalista."""
    link = page.locator(f"{TOC} a.md-nav__link").nth(2)
    href = link.get_attribute("href")
    link.click()
    page.wait_for_function(
        f"document.getElementById('{href[1:]}').getBoundingClientRect().top < 100")
    page.wait_for_selector(f"{TOC} a.md-nav__link--active[href='{href}']", timeout=2000)


def test_contents_stays_put_when_scrolling(page):
    """Sisällysluettelo ei liiku sisällön mukana ensimmäisiä vierityspikseleitä."""
    title = page.locator(f"{TOC} .md-nav__title")
    start = title.bounding_box()["y"]
    page.evaluate("scrollTo(0, 40)")
    assert title.bounding_box()["y"] == pytest.approx(start, abs=1)


# Luvun avausnuolen kulma asteina chevron-rightistä: 90 alas, -90 ylös, 0 oikealle.
ARROW_ANGLE = """item => {
    const icon = item.querySelector(":scope > .md-nav__container .md-nav__icon")
    const transform = getComputedStyle(icon, "::after").transform
    if (transform === "none")
        return 0
    const [a, b] = transform.match(/matrix\\(([^)]*)\\)/)[1].split(",").map(Number)
    return Math.round(Math.atan2(b, a) * 180 / Math.PI)
}"""


@pytest.mark.parametrize("width", [400, 1280], ids=["puhelin", "työpöytä"])
def test_chapter_arrow_points_where_the_list_moves(browser, chapter_url, width):
    """Avausnuoli osoittaa alas suljettuna ja ylös avattuna myös kapean näytön
    laatikossa: teeman oletus on oikealle ja avattuna alas, mutta alaluvut
    aukeavat paikalleen kaikilla leveyksillä."""
    context = browser.new_context(viewport={"width": width, "height": 700})
    page = context.new_page()
    page.goto(chapter_url, wait_until="load")
    if width < 1220:
        page.click(".md-header__button[for=__drawer]")
    chapters = ".md-sidebar--primary .md-nav--primary > .md-nav__list > .md-nav__item--nested"
    current = page.locator(f"{chapters}.md-nav__item--active")
    other = page.locator(f"{chapters}:not(.md-nav__item--active)").first
    assert current.evaluate(ARROW_ANGLE) == -90
    assert other.evaluate(ARROW_ANGLE) == 90
    other.locator(":scope > .md-nav__container > label.md-nav__link").click()
    page.wait_for_function(f"item => ({ARROW_ANGLE})(item) === -90",
                           arg=other.element_handle(), timeout=2000)
    context.close()


@pytest.mark.parametrize("width, rail", [(1179, None), (1180, 260), (1219, 260), (1220, 300)])
def test_rail_fits_an_11_inch_ipad_in_landscape(browser, chapter_url, width, rail):
    """Kisko näkyy 1180 px:stä (11 tuuman iPad vaakatasossa) alkaen, alle
    teeman oman 1220 px:n rajan kapeampana (13rem); sitä kapeammalla laatikko."""
    context = browser.new_context(viewport={"width": width, "height": 700})
    page = context.new_page()
    page.goto(chapter_url, wait_until="load")
    menu = page.locator(".md-header__button[for=__drawer]")
    box = page.locator(".md-sidebar--primary").bounding_box()
    if rail is None:
        assert menu.is_visible()
        assert box["x"] + box["width"] <= 0
    else:
        assert not menu.is_visible()
        assert (box["x"], box["width"]) == (0, rail)
        content = page.locator(".md-content__inner").bounding_box()
        assert content["x"] > rail
    context.close()


EDGES = """() => {
    const box = s => document.querySelector(s).getBoundingClientRect()
    const rem = parseFloat(getComputedStyle(document.documentElement).fontSize)
    const right = box('.md-header').right  // ikkunan oikea reuna ilman vierityspalkkia
    const rail = box('.md-sidebar--primary'), grid = box('.md-main__inner')
    return {
        left: rail.left, right: right - grid.right,
        gap: (grid.left - rail.right) / rem,
        logo: box('.md-header__button.md-logo').left - rail.left,
        search: box('.md-search').right - box('.md-sidebar--secondary .md-nav__list').right,
        footer: [box('.md-footer').left - rail.left, box('.md-footer').right - grid.right],
    }
}"""


@pytest.mark.parametrize("width, centred", [(1600, False), (1920, True), (2800, True)])
def test_wide_screen_centres_the_rail_with_the_text(browser, chapter_url, width, centred):
    """Kun kisko, rako ja ruudukko (61rem) mahtuvat ja tilaa jää yli, ne
    keskitetään yhdessä: tyhjä tila jakautuu tasan kiskon vasemmalle ja
    sisällysluettelon oikealle puolelle eikä jää valikon ja tekstin väliin.
    Logo ja haku siirtyvät mukana, ja alatunniste päättyy ruudukon reunaan.
    Kapeammalla kisko on reunassa kuten ennen."""
    context = browser.new_context(viewport={"width": width, "height": 700})
    page = context.new_page()
    page.goto(chapter_url, wait_until="load")
    edges = page.evaluate(EDGES)
    if centred:
        assert edges["left"] > 50
        assert edges["left"] == pytest.approx(edges["right"], abs=1)
        assert edges["gap"] == pytest.approx(0.8, abs=0.01)
        assert edges["search"] == pytest.approx(0, abs=1)
        assert edges["footer"] == pytest.approx([0, 0], abs=1)
    else:
        assert edges["left"] == 0
    assert 0 < edges["logo"] < 30
    context.close()


def test_drawer_scrollbar_stays_between_the_rounded_corners(browser, chapter_url):
    """Kapean näytön laatikon vierityspalkin raita alkaa ja päättyy kulmien
    pyöristyksen sisäpuolella, mutta vieritysalue on yhä koko laatikon korkuinen."""
    context = browser.new_context(viewport={"width": 1100, "height": 500})
    page = context.new_page()
    page.goto(chapter_url, wait_until="load")
    page.click(".md-header__button[for=__drawer]")
    box, rail, radius, track = page.evaluate("""() => {
        const drawer = document.querySelector(".md-sidebar--primary")
        const rail = drawer.querySelector(".md-sidebar__scrollwrap")
        const track = getComputedStyle(rail, "::-webkit-scrollbar-track")
        const rect = element => element.getBoundingClientRect().toJSON()
        return [rect(drawer), rect(rail), getComputedStyle(drawer).borderTopLeftRadius,
                [track.marginTop, track.marginBottom]]
    }""")
    assert radius != "0px"
    assert track == [radius, radius]
    assert (rail["top"], rail["bottom"]) == (box["top"], box["bottom"])
    context.close()


# Alatunnisteen linkit (overrides/partials/copyright.html).
FOOTER_LINKS = ".jyu-footer-links a"
REPO = "https://github.com/ohj-perus-jy/kirjatyokalut"


def test_footer_links_lead_to_the_page_on_github(page):
    """Muokkaus ja muutoshistoria avaavat luvun lähdetiedoston ../src:ssä,
    ongelmailmoitus issue-lomakkeen sivun polulla."""
    links = page.locator(FOOTER_LINKS)
    assert [text.strip() for text in links.all_inner_texts()] == [
        "Muokkaa", "Muutoshistoria", "Ilmoita ongelma"]
    assert links.evaluate_all("links => links.map(link => link.href)") == [
        f"{REPO}/edit/main/src/osa1/01-hei.md",
        f"{REPO}/commits/main/src/osa1/01-hei.md",
        f"{REPO}/issues/new?template=ilmoita-ongelmasta.yml&url=osa1/01-hei.md"]


@pytest.mark.parametrize("width", [360, 390])
def test_footer_links_fit_on_one_row_on_a_phone(browser, chapter_url, width):
    """Linkit ovat samalla rivillä kapeimmallakin yleisellä puhelimella (360 px).
    Puhelimen vierityspalkki on sisällön päällä, joten is_mobile: työpöydän
    palkki veisi rivistä 15 px, ja väljyyttä on vain 8 px."""
    context = browser.new_context(viewport={"width": width, "height": 700},
                                  is_mobile=True, has_touch=True)
    page = context.new_page()
    page.goto(chapter_url, wait_until="load")
    tops = page.locator(FOOTER_LINKS).evaluate_all(
        "links => links.map(link => Math.round(link.getBoundingClientRect().top))")
    assert len(tops) == 3
    assert len(set(tops)) == 1
    context.close()


def test_phone_contents_closes_when_a_link_is_tapped(browser, chapter_url):
    """Kapealla näytöllä sisällysluettelo on alakulman napista avautuva
    laatikko (teeman #__toc-valintaruutu). Kohdan napautus vie otsikkoon ja
    sulkee laatikon; teema itse jättäisi sen auki (assets/js/toc.js)."""
    context = browser.new_context(viewport={"width": 400, "height": 700})
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(chapter_url, wait_until="load")
    box_opacity = f"getComputedStyle(document.querySelector('{TOC} .md-sidebar__inner')).opacity"
    assert page.evaluate(box_opacity) == "0"
    page.click(f"{TOC} .md-sidebar-button")
    page.wait_for_function(f"{box_opacity} === '1'")
    link = page.locator(f"{TOC} a.md-nav__link").nth(2)
    href = link.get_attribute("href")
    link.click()
    page.wait_for_function(
        f"document.getElementById('{href[1:]}').getBoundingClientRect().top < 100")
    assert not page.is_checked("#__toc")
    page.wait_for_function(f"{box_opacity} === '0'")
    assert errors == []
    context.close()


def test_phone_contents_closes_when_tapped_outside(browser, chapter_url):
    """Laatikon ulkopuolen napautus sulkee sen; laatikon oman listan napautus
    kohtien ohi ei (assets/js/toc.js)."""
    context = browser.new_context(viewport={"width": 400, "height": 700})
    page = context.new_page()
    page.goto(chapter_url, wait_until="load")
    page.click(f"{TOC} .md-sidebar-button")
    assert page.is_checked("#__toc")
    # Laatikko liukuu auki; mitataan vasta perillä.
    page.wait_for_function(
        f"getComputedStyle(document.querySelector('{TOC} .md-sidebar__inner')).opacity === '1'")
    box = page.locator(f"{TOC} .md-sidebar__inner").bounding_box()
    page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] - 2)
    assert page.is_checked("#__toc")
    page.mouse.click(20, 300)
    assert not page.is_checked("#__toc")
    context.close()
