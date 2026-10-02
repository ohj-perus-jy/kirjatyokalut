"""Leipätekstin kirjasin- ja kokovalikko koekirjalla, selaimessa.

Valikon vaikutus syntyy vasta selaimessa (attribuutti, muuttuja,
localStorage, inline-skripti ennen sisältöä), joten sivu on avattava
oikeasti.
"""

import pytest

KEY = "jyu-font"
SIZE_KEY = "jyu-text-size"
PANEL = ".jyu-font__panel"
DOWN = ".jyu-font__step[data-step='-1']"
UP = ".jyu-font__step[data-step='1']"
RESET = ".jyu-font__reset"
# Leipätekstin perustaso rem-yksiköissä: teeman .75rem × 1,1 (typography.css).
BASE = 0.75 * 1.1


@pytest.fixture(scope="module")
def base_url(book, serve):
    return serve(book.site)


def open_page(browser, url, init_script=None, **context):
    """Avaa sivun ja kerää skriptivirheet. -> (sivu, virheet)."""
    page = browser.new_page(**context)
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    if init_script:
        page.add_init_script(init_script)
    page.goto(url, wait_until="load")
    return page, errors


def body_font(page) -> str | None:
    return page.evaluate("document.body.getAttribute('data-jyu-font')")


def content_font(page) -> str:
    """Artikkelin kirjasinperheen ensimmäinen nimi, lainausmerkit riisuttuna."""
    family = page.evaluate(
        "getComputedStyle(document.querySelector('.md-content__inner')).fontFamily")
    return family.split(",")[0].strip().strip('"')


def font_size(page, selector) -> float:
    """Ensimmäisen osuman laskettu kirjasinkoko pikseleinä."""
    return page.evaluate(
        "s => parseFloat(getComputedStyle(document.querySelector(s)).fontSize)", selector)


def rem(page) -> float:
    return font_size(page, "html")


def label(page) -> str:
    """Painikkeen nimi, jossa nykyiset valinnat kerrotaan. Sama nimi on
    title-attribuutissa, mutta teeman vihje pitää sitä hallussaan auki
    ollessaan (ks. hints)."""
    return page.get_attribute(".jyu-font__button", "aria-label")


def title(page) -> str | None:
    return page.get_attribute(".jyu-font__button", "title")


def active(page) -> str:
    """Kohdistetun elementin tunniste: kohdan data-font, napin data-step,
    luokka tai id."""
    return page.evaluate(
        "(e => e.dataset.font ?? e.dataset.step ?? (e.id || e.classList[0]))"
        "(document.activeElement)")


def test_without_a_choice_the_page_is_as_before(browser, base_url):
    """Oletus on Source Serif 4 perustasolla (teeman koko × 1,1) eikä bodyssä
    ole attribuuttia eikä muuttujaa: ilman valintaa sivu on täsmälleen
    entisensä, ja painikkeen vihje kertoo nykyiset valinnat."""
    page, errors = open_page(browser, base_url)
    assert body_font(page) is None
    assert page.evaluate("document.body.style.length") == 0
    assert content_font(page) == "Source Serif 4"
    assert font_size(page, ".md-content__inner") == pytest.approx(BASE * rem(page))
    assert label(page) == "Leipäteksti: Serif, 100 %"
    assert page.evaluate(f"localStorage.getItem('{KEY}')") is None
    assert page.evaluate(f"localStorage.getItem('{SIZE_KEY}')") is None
    assert page.is_hidden(PANEL)
    assert errors == []


def test_a_choice_changes_the_font_and_is_remembered(browser, base_url):
    """Valinta vaihtaa artikkelin kirjasimen, päivittää painikkeen vihjeen ja
    tallentuu selaimeen. Paneeli pysyy auki, jotta kokoa voi säätää samalla.
    Seuraavalla sivulla valinta on voimassa jo ennen fontmenu.js:n
    latautumista (header.html:n inline-skripti), joten teksti ei välähdä
    oletuskirjasimella."""
    page, errors = open_page(browser, base_url)
    page.click(".jyu-font__button")
    assert page.is_visible(PANEL)
    assert page.evaluate("document.querySelectorAll('.jyu-font__item').length") == 3
    assert page.get_attribute(".jyu-font__button", "aria-expanded") == "true"

    page.click(".jyu-font__item[data-font=literata]")
    assert page.is_visible(PANEL)
    assert body_font(page) == "literata"
    assert content_font(page) == "Literata"
    assert label(page) == "Leipäteksti: Literata, 100 %"
    assert page.evaluate(f"localStorage.getItem('{KEY}')") == "literata"
    # Otsikot ja koodi eivät vaihda kirjasinta.
    assert page.evaluate(
        "getComputedStyle(document.querySelector('.md-content__inner h1')).fontFamily"
    ).startswith('"Source Sans 3"')
    assert page.get_attribute(".jyu-font__item[data-font=literata]", "aria-selected") == "true"
    assert page.get_attribute(".jyu-font__item[data-font='']", "aria-selected") == "false"

    # Uusi sivulataus ilman fontmenu.js:ää: attribuutin on oltava silti paikallaan.
    page.route("**/fontmenu.js", lambda route: route.abort())
    page.goto(base_url, wait_until="domcontentloaded")
    assert body_font(page) == "literata"
    assert content_font(page) == "Literata"
    assert errors == []


def test_the_print_page_follows_the_choice(browser, base_url):
    """Tulostussivu liittää luvut samaan .md-content__inneriin, joten valittu
    kirjasin ja koko pätevät myös siellä ruudulla ilman omaa koodia."""
    page, errors = open_page(
        browser, f"{base_url}/tulosta/",
        init_script=f"localStorage.setItem('{KEY}', 'atkinson');"
                    f"localStorage.setItem('{SIZE_KEY}', '120')")
    assert body_font(page) == "atkinson"
    assert content_font(page) == "Atkinson Hyperlegible Next"
    assert font_size(page, ".md-content__inner") == pytest.approx(BASE * 1.2 * rem(page))
    assert label(page) == "Leipäteksti: Atkinson, 120 %"
    assert errors == []


def test_choosing_the_default_forgets_the_choice(browser, base_url):
    """Oletuksen valitseminen poistaa tallennuksen ja attribuutin: "ei
    valintaa" ja "Source Serif 4" ovat sama asia."""
    page, errors = open_page(
        browser, base_url,
        init_script=f"localStorage.setItem('{KEY}', 'atkinson')")
    assert body_font(page) == "atkinson"
    page.click(".jyu-font__button")
    page.click(".jyu-font__item[data-font='']")
    assert body_font(page) is None
    assert content_font(page) == "Source Serif 4"
    assert label(page) == "Leipäteksti: Serif, 100 %"
    assert page.evaluate(f"localStorage.getItem('{KEY}')") is None
    assert errors == []


def test_an_unknown_stored_value_is_ignored(browser, base_url):
    """Vanha tai käsin muokattu arvo ei saa jättää bodyyn attribuuttia, jolle
    ei ole kirjasinta, eikä kokoa, joka ei ole portaissa."""
    page, errors = open_page(
        browser, base_url,
        init_script=f"localStorage.setItem('{KEY}', 'comic-sans');"
                    f"localStorage.setItem('{SIZE_KEY}', '133')")
    assert body_font(page) is None
    assert page.evaluate("document.body.style.length") == 0
    assert content_font(page) == "Source Serif 4"
    assert font_size(page, ".md-content__inner") == pytest.approx(BASE * rem(page))
    assert label(page) == "Leipäteksti: Serif, 100 %"
    assert errors == []


def test_the_size_buttons_scale_the_content_only(browser, base_url):
    """+ suurentaa artikkelin tekstin seuraavaan portaaseen ja paneeli pysyy
    auki. Otsikot ja välilehtien nimet seuraavat samassa suhteessa, mutta
    valikko, yläpalkki ja paneeli itse pysyvät ennallaan."""
    page, errors = open_page(browser, f"{base_url}/osa1/01-hei/")
    outside = [".md-nav__link", ".md-header__topic", ".jyu-font__item", ".jyu-font__size"]
    before = {s: font_size(page, s) for s in outside}
    text = font_size(page, ".md-content__inner")
    heading = font_size(page, ".md-content__inner h1")
    tab = font_size(page, ".tabbed-labels > label")

    page.click(".jyu-font__button")
    page.click(UP)
    assert page.is_visible(PANEL)
    # Selain pyöristää lasketut koot, joten suhteellinen toleranssi.
    assert font_size(page, ".md-content__inner") == pytest.approx(1.1 * text, rel=1e-3)
    assert font_size(page, ".md-content__inner h1") == pytest.approx(1.1 * heading, rel=1e-3)
    assert font_size(page, ".tabbed-labels > label") == pytest.approx(1.1 * tab, rel=1e-3)
    assert {s: font_size(page, s) for s in outside} == before
    assert page.inner_text(RESET) == "110 %"
    assert page.get_attribute(RESET, "aria-disabled") == "false"
    assert label(page) == "Leipäteksti: Serif, 110 %"
    assert page.evaluate(f"localStorage.getItem('{SIZE_KEY}')") == "110"

    page.click(UP)
    page.click(UP)
    assert font_size(page, ".md-content__inner") == pytest.approx(1.35 * text, rel=1e-3)
    page.click(DOWN)
    assert font_size(page, ".md-content__inner") == pytest.approx(1.2 * text, rel=1e-3)
    assert errors == []


def test_the_size_is_remembered_before_the_script(browser, base_url):
    """Tallennettu koko on voimassa jo ennen fontmenu.js:ää (header.html:n
    inline-skripti), joten teksti ei hyppää sivun latautuessa."""
    page, errors = open_page(
        browser, base_url,
        init_script=f"localStorage.setItem('{SIZE_KEY}', '150')")
    page.route("**/fontmenu.js", lambda route: route.abort())
    page.reload(wait_until="domcontentloaded")
    assert font_size(page, ".md-content__inner") == pytest.approx(BASE * 1.5 * rem(page))
    assert errors == []


def test_the_steps_stop_at_both_ends(browser, base_url):
    """Ääripäässä nappi on aria-disabled eikä tee mitään. Ei disabled, jotta
    kohdistus pysyy napissa."""
    page, errors = open_page(browser, base_url)
    page.click(".jyu-font__button")
    page.click(DOWN)
    assert page.inner_text(RESET) == "90 %"
    assert page.get_attribute(DOWN, "aria-disabled") == "true"
    page.click(DOWN, force=True)  # Playwright ei muuten napsauta aria-disabledia.
    assert page.inner_text(RESET) == "90 %"
    assert font_size(page, ".md-content__inner") == pytest.approx(BASE * 0.9 * rem(page))

    page.evaluate(f"localStorage.setItem('{SIZE_KEY}', '175')")
    page.reload(wait_until="load")
    page.click(".jyu-font__button")
    assert page.get_attribute(UP, "aria-disabled") == "true"
    assert page.get_attribute(DOWN, "aria-disabled") == "false"
    page.focus(UP)
    page.keyboard.press("Enter")
    assert page.inner_text(RESET) == "175 %"
    assert active(page) == "1"
    assert errors == []


def test_the_number_resets_the_size_and_forgets_it(browser, base_url):
    """Prosenttiluku palauttaa oletuskoon ja poistaa tallennuksen; oletuksessa
    se on aria-disabled."""
    page, errors = open_page(
        browser, base_url,
        init_script=f"localStorage.setItem('{SIZE_KEY}', '135')")
    page.click(".jyu-font__button")
    assert page.inner_text(RESET) == "135 %"
    page.click(RESET)
    assert page.inner_text(RESET) == "100 %"
    assert page.get_attribute(RESET, "aria-disabled") == "true"
    assert page.evaluate("document.body.style.length") == 0
    assert font_size(page, ".md-content__inner") == pytest.approx(BASE * rem(page))
    assert page.evaluate(f"localStorage.getItem('{SIZE_KEY}')") is None
    assert errors == []


def test_paper_keeps_the_theme_size(browser, base_url):
    """Koko koskee vain ruutua: tulostettaessa teeman print-koko (.68rem)."""
    page, errors = open_page(
        browser, base_url,
        init_script=f"localStorage.setItem('{SIZE_KEY}', '150')")
    page.emulate_media(media="print")
    assert font_size(page, ".md-content__inner") == pytest.approx(0.68 * rem(page))
    assert errors == []


def test_the_reading_position_stays(browser, base_url):
    """Koon vaihtuessa yläpalkin alla oleva kappale pysyy paikallaan, vaikka
    sen yläpuolinen teksti kasvaa ja sivu vierii."""
    page, errors = open_page(
        browser, f"{base_url}/osa1/01-hei/",
        viewport={"width": 1280, "height": 400})
    header = page.evaluate("document.querySelector('.md-header').getBoundingClientRect().bottom")
    paragraphs = page.locator(".md-content__inner > p")
    target = paragraphs.nth(paragraphs.count() // 2)
    top = lambda: target.evaluate("e => e.getBoundingClientRect().top")
    page.evaluate(f"window.scrollBy(0, {top() - header})")
    scrolled = page.evaluate("scrollY")
    assert scrolled > 0
    assert top() == pytest.approx(header, abs=1)

    page.click(".jyu-font__button")
    for _ in range(3):
        page.click(UP)
    assert page.evaluate("scrollY") > scrolled + 50
    assert top() == pytest.approx(header, abs=2)

    page.click(RESET)
    assert page.evaluate("scrollY") == pytest.approx(scrolled, abs=2)
    assert top() == pytest.approx(header, abs=2)
    assert errors == []


def test_the_menu_works_from_the_keyboard(browser, base_url):
    """Nuoli alas avaa ja kohdistaa valittuun, nuolet liikkuvat, Enter
    valitsee ja paneeli pysyy auki. + ja − muuttavat kokoa missä tahansa
    paneelissa. Esc sulkee ja palauttaa kohdistuksen."""
    page, errors = open_page(browser, base_url)
    page.focus(".jyu-font__button")
    page.keyboard.press("ArrowDown")
    assert page.is_visible(PANEL)
    assert active(page) == ""
    page.keyboard.press("ArrowDown")
    assert active(page) == "atkinson"
    page.keyboard.press("Enter")
    assert page.is_visible(PANEL)
    assert body_font(page) == "atkinson"
    assert active(page) == "atkinson"

    page.keyboard.press("+")
    page.keyboard.press("+")
    page.keyboard.press("-")
    assert page.inner_text(RESET) == "110 %"
    assert label(page) == "Leipäteksti: Atkinson, 110 %"

    page.keyboard.press("Escape")
    assert page.is_hidden(PANEL)
    assert body_font(page) == "atkinson"
    assert active(page) == "jyu-font-button"

    page.keyboard.press("ArrowDown")
    assert page.is_visible(PANEL)
    assert active(page) == "atkinson"
    page.keyboard.press("Escape")
    assert page.is_hidden(PANEL)
    assert errors == []


def test_tab_goes_through_the_panel_and_out(browser, base_url):
    """Sarkain kulkee koon napeista valittuun kirjasimeen ja takaisin.
    Listasta eteenpäin kohdistus lähtee valikosta, ja paneeli sulkeutuu."""
    page, errors = open_page(browser, base_url)
    page.focus(".jyu-font__button")
    page.keyboard.press("ArrowDown")
    assert active(page) == ""
    order = []
    for _ in range(3):
        page.keyboard.press("Shift+Tab")
        order.append(active(page))
    assert order == ["1", "jyu-font__reset", "-1"]
    for _ in range(3):
        page.keyboard.press("Tab")
    assert active(page) == ""
    page.keyboard.press("Tab")
    assert page.is_hidden(PANEL)
    assert not page.evaluate(
        "document.querySelector('[data-md-component=jyu-font]').contains(document.activeElement)")
    assert errors == []


def hints(page) -> list[str]:
    """Näkyvien teeman vihjeiden (content.tooltips) tekstit. Teema lisää
    vihjeen bodyyn, kun painikkeella on osoitin tai kohdistus, ja poistaa sen
    250 ms niiden lähdettyä."""
    page.wait_for_timeout(500)
    return page.locator(".md-tooltip2:visible").all_inner_texts()


def test_the_hint_does_not_stay_open_after_the_mouse(browser, base_url):
    """Hiirellä suljettaessa kohdistus ei jää painikkeeseen, koska teeman
    vihje pysyisi silloin auki osoittimen lähdettyä."""
    page, errors = open_page(browser, base_url)
    page.click(".jyu-font__button")
    page.click(".jyu-font__item[data-font=atkinson]")
    page.click(".jyu-font__button")
    assert page.is_hidden(PANEL)
    page.mouse.move(10, 400)
    assert hints(page) == []
    assert title(page) == "Leipäteksti: Atkinson, 100 %"
    assert errors == []


def test_the_hint_does_not_cover_the_panel(browser, base_url):
    """Vihje tulisi painikkeen alle paneelin päälle, joten se on piilossa
    paneelin ollessa auki. Escin jälkeen se palaa, koska osoitin on yhä
    painikkeella, kertoo uudet valinnat ja on tekstinsä levyinen, jotta se
    asettuu painikkeen keskelle."""
    page, errors = open_page(browser, base_url)
    page.hover(".jyu-font__button")
    assert hints(page) == ["Leipäteksti: Serif, 100 %"]
    page.click(".jyu-font__button")
    assert page.is_visible(PANEL)
    assert hints(page) == []
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")
    page.keyboard.press("+")
    assert hints(page) == []
    page.keyboard.press("Escape")
    assert hints(page) == ["Leipäteksti: Atkinson, 110 %"]
    assert page.evaluate(
        "(tip => tip.firstElementChild.offsetWidth"
        " === parseFloat(tip.style.getPropertyValue('--md-tooltip-width')))"
        "(document.querySelector('.md-tooltip2'))")
    assert errors == []


def test_the_hint_names_the_new_choice(browser, base_url):
    """Näppäimistöllä kohdistus palaa painikkeeseen, ja vihje kertoo uuden
    valinnan, kun kohdistus seuraavan kerran tulee painikkeeseen, vaikka
    valinta tehtiin edellisen vihjeen ollessa auki. Sulkeutuessaan teema
    palauttaa titleen avautumishetken nimen, joka korjataan."""
    page, errors = open_page(browser, base_url)
    page.focus(".jyu-font__button")
    assert hints(page) == ["Leipäteksti: Serif, 100 %"]
    page.keyboard.press("ArrowDown")
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")
    page.keyboard.press("Escape")
    assert active(page) == "jyu-font-button"
    assert hints(page) == []
    page.keyboard.press("Tab")
    page.keyboard.press("Shift+Tab")
    assert active(page) == "jyu-font-button"
    assert hints(page) == ["Leipäteksti: Atkinson, 100 %"]
    page.keyboard.press("Tab")
    assert hints(page) == []
    assert title(page) == label(page) == "Leipäteksti: Atkinson, 100 %"
    assert errors == []


def test_escape_does_not_leave_the_hint_open(browser, base_url):
    """Kirjasin hiirellä, sitten Esc: kohdistus palaa painikkeeseen, mutta
    kohdistus ei pidä teeman vihjettä auki, koska osoitin on muualla ja
    valinta näkyi juuri paneelissa. Vihje näkyy vain osoittimen ollessa
    painikkeella, myös kun osoitin käy painikkeella ja lähtee, kunnes
    kohdistus lähtee painikkeesta."""
    page, errors = open_page(browser, base_url)
    page.click(".jyu-font__button")
    page.click(".jyu-font__item[data-font=literata]")
    page.keyboard.press("Escape")
    assert page.is_hidden(PANEL)
    assert active(page) == "jyu-font-button"
    assert hints(page) == []
    page.hover(".jyu-font__button")
    assert hints(page) == ["Leipäteksti: Literata, 100 %"]
    page.mouse.move(10, 400)
    assert active(page) == "jyu-font-button"
    assert hints(page) == []
    page.hover(".jyu-font__button")
    assert hints(page) == ["Leipäteksti: Literata, 100 %"]
    assert errors == []


def test_the_mouse_moves_the_focus_so_one_item_is_highlighted(browser, base_url):
    """Hiiren alla oleva kohta saa kohdistuksen, ja korostus seuraa vain
    kohdistusta: nuolella siirtyminen ei jätä toista korostusta hiiren alle."""
    page, errors = open_page(browser, base_url)
    page.click(".jyu-font__button")
    page.hover(".jyu-font__item[data-font=literata]")
    assert active(page) == "literata"
    page.keyboard.press("ArrowUp")
    highlighted = page.evaluate(
        "[...document.querySelectorAll('.jyu-font__item')]"
        ".filter(item => getComputedStyle(item).backgroundColor !== 'rgba(0, 0, 0, 0)')"
        ".map(item => item.dataset.font)")
    assert highlighted == ["atkinson"]
    assert errors == []


def test_the_fonts_are_requested_before_the_list_opens(browser, base_url):
    """Kohtien nimet näkyvät omilla kirjasimillaan. Lataus pyydetään jo kun
    osoitin tulee painikkeelle, jotta nimet eivät vaihda kirjasinta paneelin
    auettua."""
    page, errors = open_page(
        browser, base_url,
        init_script="window.requested = []; const load = FontFaceSet.prototype.load;"
        "FontFaceSet.prototype.load = function (font, text) {"
        " window.requested.push(font); return load.call(this, font, text); };")
    assert page.evaluate("window.requested") == []
    page.hover(".jyu-font__button")
    assert page.is_hidden(PANEL)
    requested = page.evaluate("window.requested")
    assert len(requested) == 3
    for family in ("Source Serif 4", "Atkinson Hyperlegible Next", "Literata"):
        # Selain jättää yksisanaisen perheen (Literata) ilman lainausmerkkejä.
        assert any(family in font for font in requested)
    assert errors == []
