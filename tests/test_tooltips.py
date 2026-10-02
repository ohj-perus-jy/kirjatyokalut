"""Nappien vihjeet koekirjalla, selaimessa (assets/js/tooltips.js).

Teema (content.tooltips) tekee vihjeen vain sivun latautuessa olemassa
oleville title-elementeille ja kopiointinapille; ajonappi ja silmänappi
lisätään myöhemmin. Vihje on auki, kun napilla on kohdistus tai osoitin, ja
napautuksen jälkeen kohdistus jäisi nappiin.
"""

import pytest

BLOCK = ".language-java:not(.noplayground):not(.ignore)"
COPY = f"{BLOCK} [data-md-type=copy]"
RUN = f"{BLOCK} [data-md-type=run]"
EYE = "[data-md-type=hidelines]"
ACTIVE = ".md-tooltip2--active"


@pytest.fixture(scope="module")
def chapter_url(book, serve) -> str:
    return f"{serve(book.site)}/osa1/01-hei/"


@pytest.fixture
def desktop(browser, chapter_url):
    page = browser.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(chapter_url, wait_until="load")
    yield page
    assert errors == []
    page.close()


@pytest.fixture
def phone(browser, chapter_url):
    """Kosketusnäyttö ilman osoitinta: teema kuuntelee silloin touchstartia
    ja touchendiä mouseenterin ja mouseleaven sijaan."""
    context = browser.new_context(
        viewport={"width": 390, "height": 800}, has_touch=True, is_mobile=True)
    page = context.new_page()
    page.goto(chapter_url, wait_until="load")
    assert page.evaluate("matchMedia('(hover)').matches") is False
    yield page
    context.close()


def tooltip_text(page) -> str | None:
    tips = page.locator(ACTIVE)
    return tips.text_content().strip() if tips.count() else None


@pytest.mark.parametrize("selector", [COPY, RUN], ids=["kopioi", "suorita"])
def test_a_tap_leaves_no_tooltip_behind(phone, selector):
    """Napautuksen jälkeen vihje häviää eikä kohdistus jää nappiin: teeman
    oma kopiointinappi ja skriptin lisäämä ajonappi."""
    phone.tap(selector)
    phone.wait_for_selector(ACTIVE, state="detached", timeout=2000)
    assert phone.evaluate("document.activeElement.matches('button')") is False


@pytest.fixture
def walkthrough(browser, book, serve):
    """Vaiheittainen ohje kosketusnäytöllä, esityksenä (leveä ruutu)."""
    context = browser.new_context(
        viewport={"width": 1000, "height": 700}, has_touch=True, is_mobile=True)
    page = context.new_page()
    page.goto(f"{serve(book.site)}/osa1/vaiheet/", wait_until="load")
    page.wait_for_selector(".jyu-walk--live .jw-tick")
    yield page
    context.close()


def test_a_tap_on_a_walkthrough_step_leaves_no_tooltip_behind(walkthrough):
    """Aikajanan vaihenappi on sivulla jo teeman käynnistyessä (walkthrough.js
    rakentaa esityksen heti), joten sillä on teeman vihje; napautuksen jälkeen
    sekään ei jää. Kohdistus näyttää vihjeen, jotta testi mittaa jotakin."""
    tick = walkthrough.locator(".jw-tick").nth(2)
    tick.focus()
    walkthrough.wait_for_selector(ACTIVE)
    assert tooltip_text(walkthrough) == "3. Kirjaudu"
    walkthrough.evaluate("document.activeElement.blur()")
    walkthrough.wait_for_selector(ACTIVE, state="detached")
    tick.tap()
    walkthrough.wait_for_selector(ACTIVE, state="detached", timeout=2000)
    assert tick.get_attribute("class") == "jw-tick jw-tick--current"
    # Kohdistus siirtyy ohjeen säiliöön, jotta nuolinäppäimet toimivat yhä.
    assert walkthrough.evaluate("document.activeElement.matches('.jyu-walk')")
    walkthrough.keyboard.press("ArrowLeft")
    assert walkthrough.locator(".jw-tick").nth(1).get_attribute("class") == "jw-tick jw-tick--current"


def test_a_touch_shows_the_tooltip(phone):
    """Sormi napin päällä näyttää vihjeen kuten teeman kopiointinapilla."""
    box = phone.locator(RUN).first.bounding_box()
    phone.touchscreen.tap(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    # tap = touchstart + touchend; vihje tulee touchstartissa ja häviää
    # vasta viiveen jälkeen, kuten teeman kopiointinapilla.
    phone.wait_for_selector(ACTIVE, timeout=1000)
    assert tooltip_text(phone) == "Suorita ohjelma"


def test_the_keyboard_keeps_the_focus_and_the_tooltip(desktop):
    """Näppäimistöllä painettu nappi pitää kohdistuksen, jotta lukija voi
    jatkaa siitä; vihje saa jäädä."""
    desktop.focus(COPY)
    desktop.keyboard.press("Enter")
    desktop.wait_for_selector(".jyu-copied--shown")
    assert desktop.evaluate("document.activeElement.matches('[data-md-type=copy]')")
    assert tooltip_text(desktop) == "Kopioi leikepöydälle"


def test_added_buttons_get_the_themes_tooltip(desktop):
    """Ajonapin vihje näyttää samalta kuin kopiointinapin: sama luokka,
    sama sijoitus napin alle, aria-describedby viittaa siihen."""
    desktop.hover(RUN)
    desktop.wait_for_selector(ACTIVE)
    assert tooltip_text(desktop) == "Suorita ohjelma"
    tip_id = desktop.get_attribute(RUN, "aria-describedby")
    assert desktop.get_attribute(f"#{tip_id}", "role") == "tooltip"
    assert desktop.get_attribute(RUN, "title") is None
    button = desktop.locator(RUN).first.bounding_box()
    tip = desktop.locator(f"#{tip_id} .md-tooltip2__inner").bounding_box()
    assert tip["y"] > button["y"] + button["height"]
    assert tip["x"] < button["x"] + button["width"] / 2 < tip["x"] + tip["width"]
    desktop.mouse.move(0, 0)
    desktop.wait_for_selector(ACTIVE, state="detached")
    assert desktop.get_attribute(RUN, "title") == "Suorita ohjelma"


def test_a_title_changed_while_open_shows_in_the_tooltip(desktop):
    """Silmänappi vaihtaa titlensä painettaessa; vihje seuraa, ja suljettaessa
    attribuuttiin jää uusi teksti eikä vanha."""
    desktop.focus(EYE)
    desktop.wait_for_selector(ACTIVE)
    assert tooltip_text(desktop) == "Näytä piilotetut rivit"
    desktop.keyboard.press("Enter")
    desktop.wait_for_function(
        "document.querySelector('.md-tooltip2--active').textContent.trim() === 'Piilota rivit'")
    assert desktop.get_attribute(EYE, "title") is None
    desktop.evaluate("document.activeElement.blur()")
    desktop.wait_for_selector(ACTIVE, state="detached")
    assert desktop.get_attribute(EYE, "title") == "Piilota rivit"


# Yläpalkin elementit, joilla on ei-tyhjä title piirtohetkellä, kuvaruuduittain.
WATCH_TITLES = """() => { window.titled = [];
    const tick = () => {
        for (const e of document.querySelectorAll('.md-header [title]'))
            if (e.getAttribute('title')) titled.push(e.getAttribute('title'));
        requestAnimationFrame(tick);
    };
    tick() }"""


def test_theme_tooltips_leave_the_browser_no_title(desktop):
    """Teema ottaa titlen pois vasta avatessaan vihjeen, kuvaruutua
    myöhemmin, ja selaimen oma title-vihje ehti välillä tulla rinnalle ja
    jäädä, myös näppäimistöllä kohdistettaessa (Chrome). Teeman ottamilla
    elementeillä ei ole ei-tyhjää titleä piirtohetkellä koskaan, ja teeman
    vihjeessä on silti oikea teksti hiirellä ja näppäimistöllä."""
    desktop.evaluate(WATCH_TITLES)
    desktop.hover(".jyu-print-button")
    desktop.wait_for_selector(ACTIVE)
    assert tooltip_text(desktop) == "Tulosta koko kirja"
    desktop.mouse.move(600, 500)
    desktop.wait_for_selector(ACTIVE, state="detached", timeout=2000)
    desktop.focus(".jyu-print-button")
    desktop.wait_for_selector(ACTIVE)
    assert tooltip_text(desktop) == "Tulosta koko kirja"
    desktop.evaluate("document.activeElement.blur()")
    desktop.wait_for_selector(ACTIVE, state="detached", timeout=2000)
    desktop.wait_for_timeout(100)
    assert desktop.evaluate("titled") == []
    assert desktop.get_attribute(".jyu-print-button", "aria-label") == "Tulosta koko kirja"


def test_an_element_named_only_by_its_title_keeps_its_name(desktop):
    """Teemanvaihtimen labeleilla ei ole muuta nimeä kuin title, joten ne
    saavat sen aria-labeliksi, kun title siirretään pois."""
    labels = desktop.eval_on_selector_all(
        "label[for^=__palette]",
        "labels => labels.map(l => [l.getAttribute('title'), l.getAttribute('aria-label')])")
    assert labels == [[None, "Vaihda tummaan teemaan"], [None, "Vaihda vaaleaan teemaan"]]


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_the_theme_toggle_shows_its_tooltip_and_ring_from_the_keyboard(browser, chapter_url, scheme):
    """Tab kohdistaa teemanvaihtimen piilotettuun radionappiin, ja teeman
    vihje on näkyvässä labelissa, joka ei aina ole kohdistetun napin vieressä
    (tummassa teemassa ei ole): vihje aukeaa näkyvään labeliin, sillä on
    kohdistusrengas, ja vihje sulkeutuu, kun kohdistus lähtee."""
    context = browser.new_context(color_scheme=scheme)
    page = context.new_page()
    page.goto(chapter_url, wait_until="load")
    visible = "[data-md-component=palette] label:not([hidden])"
    name = page.get_attribute(visible, "aria-label")
    page.focus("[data-md-component=palette] .md-option")
    page.wait_for_selector(ACTIVE)
    assert tooltip_text(page) == name
    assert page.eval_on_selector(visible, "label => getComputedStyle(label).outlineStyle") == "auto"
    page.evaluate("document.activeElement.blur()")
    page.wait_for_selector(ACTIVE, state="detached", timeout=2000)
    context.close()


def fades_like_the_theme(page, leave):
    """Vihjeen häivytys alkaa heti, kun osoitin tai kohdistus lähtee, ja vihje
    poistuu häivytyksen (250 ms) jälkeen, kuten teeman omissa vihjeissä."""
    page.wait_for_selector(ACTIVE)
    leave()
    page.wait_for_timeout(80)
    assert page.locator(ACTIVE).count() == 0
    page.wait_for_function("!document.querySelector('.md-tooltip2')", timeout=1000)


def test_added_and_theme_toggle_tooltips_fade_like_the_themes(desktop):
    """Lisätyn napin (ajonappi) ja teemanvaihtimen näppäimistövihje
    häipyvät yhtä nopeasti kuin teeman omat; aiemmin ne odottivat ensin
    250 ms ja viipyivät siksi kaksi kertaa pidempään."""
    desktop.hover(RUN)
    fades_like_the_theme(desktop, lambda: desktop.mouse.move(600, 500))
    desktop.focus("[data-md-component=palette] .md-option")
    fades_like_the_theme(desktop, lambda: desktop.evaluate("document.activeElement.blur()"))
    desktop.hover(".jyu-print-button")
    fades_like_the_theme(desktop, lambda: desktop.mouse.move(600, 500))
