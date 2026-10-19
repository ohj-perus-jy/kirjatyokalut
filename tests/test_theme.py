"""Teeman vaihdon häivytys koekirjalla, selaimessa.

Yläpalkin teemanappi vaihtaa bodyn data-md-color-scheme-attribuutin, ja
assets/js/theme.js ajaa vaihdon selaimen näkymäsiirtymänä (View Transitions),
jolloin vanha näkymä häipyy uuden päälle. Vähemmän liikettä pyytävälle ja
ilman rajapintaa vaihto on välitön kuten Zensicalilla.
"""

import pytest

TOGGLE = "form[data-md-component=palette] label:not([hidden])"
SCHEME = "document.body.dataset.mdColorScheme"
ACTIVE = "document.documentElement.matches(':active-view-transition')"


@pytest.fixture(scope="module")
def base_url(book, serve):
    return serve(book.site)


def open_page(browser, url, motion=True):
    context = browser.new_context(viewport={"width": 1280, "height": 600},
                                  reduced_motion="no-preference" if motion else "reduce")
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(url, wait_until="load")
    assert page.evaluate(SCHEME) == "default"
    return page, errors


def test_the_button_fades_to_the_other_scheme(browser, base_url):
    """Painallus käynnistää näkymäsiirtymän; teema vaihtuu vasta, kun selain
    on ottanut vanhasta näkymästä kuvan, ja siirtymä häivyttää kuvan uuden
    teeman päältä. Toinen painallus vaihtaa takaisin."""
    page, errors = open_page(browser, base_url)
    state = page.evaluate(f"""() => {{
        document.querySelector('{TOGGLE}').click()
        return {{active: {ACTIVE}, scheme: {SCHEME}}}
    }}""")
    assert state == {"active": True, "scheme": "default"}
    page.wait_for_function(f"{SCHEME} === 'slate'")
    assert page.evaluate(ACTIVE)
    page.wait_for_function(f"!{ACTIVE}")
    assert page.evaluate(SCHEME) == "slate"
    page.click(TOGGLE)
    page.wait_for_function(f"!{ACTIVE}")
    assert page.evaluate(SCHEME) == "default"
    assert errors == []


def test_the_fade_lasts_long_enough_to_see(browser, base_url):
    """Siirtymän häivytys kestää vähintään 0,3 s: selaimen oletus (0,25 s)
    on hätäinen koko sivun värinvaihdolle."""
    page, errors = open_page(browser, base_url)
    page.click(TOGGLE)
    page.wait_for_function(f"{SCHEME} === 'slate'")
    duration = page.evaluate("""() => {
        const fades = document.getAnimations().filter(a =>
            a.effect.pseudoElement?.startsWith('::view-transition-old('))
        return fades.map(a => a.effect.getTiming().duration)
    }""")
    assert duration and min(duration) >= 300
    assert errors == []


def test_reduced_motion_switches_at_once(browser, base_url):
    """Liikkeen vähennys: ei siirtymää, teema vaihtuu heti."""
    page, errors = open_page(browser, base_url, motion=False)
    state = page.evaluate(f"""() => {{
        document.querySelector('{TOGGLE}').click()
        return {{active: {ACTIVE}, scheme: {SCHEME}}}
    }}""")
    assert state == {"active": False, "scheme": "slate"}
    assert errors == []
