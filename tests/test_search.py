"""Hakuikkuna koekirjalla, selaimessa.

Zensicalin hakuikkuna on shadow DOM:issa, johon sivun CSS ei ulotu, joten
assets/js/search.js liittää assets/css/search.css:n sinne itse. Tarkistetaan
selaimessa, että liitos toimii, tulosten teksti on sivun muun tekstin kokoista,
suodatinpaneelia ei ole ja sulkunappi sulkee ikkunan myös puhelimen
kokoisella näytöllä. Luokkanimet ovat Zensicalin minifioituja (search.css);
jos ne vaihtuvat versiossa, nämä testit kertovat.
"""

import pytest

# Hakuikkunan shadow-juuri: bodyn ainoa lapsi, jolla on avoin shadow DOM.
SHADOW = "[...document.body.children].find(el => el.shadowRoot).shadowRoot"


@pytest.fixture(scope="module")
def base_url(book, serve):
    return serve(book.site)


def open_search(browser, url, query, viewport=(1600, 900)):
    """Avaa sivun, haun ja odota tuloksia. -> (sivu, skriptivirheet).

    Oletusleveys 1600 px, jolloin sivun rem on 22 px (teema: 137,5 % kun
    näyttö on vähintään 100 em): silloin kiinteät pikselikoot erottuisivat
    remillä annetuista. Kapealla näytöllä haun avaa yläpalkin kuvake
    (header.html: label), leveällä teeman oma nappi.
    """
    width, height = viewport
    page = browser.new_page(viewport={"width": width, "height": height})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(url, wait_until="load")
    page.click("label[for=__search]" if width <= 740 else ".md-search__button")
    # Ikkuna kohdistaa kentän vasta avauduttuaan; sitä ennen kirjoitus hukkuu.
    page.wait_for_function(f"{SHADOW}.activeElement?.tagName === 'INPUT'")
    page.keyboard.type(query)
    page.wait_for_function(f"{SHADOW}.querySelectorAll('.b li').length > 0")
    return page, errors


def font_size(page, selector, root=SHADOW) -> float:
    return page.evaluate(
        f"parseFloat(getComputedStyle({root}.querySelector('{selector}')).fontSize)")


def is_shown(page, selector) -> bool:
    """Näkyykö elementti eli onko sillä laatikko (display: none -> ei)."""
    return page.evaluate(
        f"{SHADOW}.querySelector('{selector}').getClientRects().length > 0")


def test_the_stylesheet_is_attached_and_the_text_is_page_sized(browser, base_url):
    """search.css on shadow-juuressa, ja tuloksen otsikko, ote ja hakukenttä
    ovat vähintään leipätekstin ja valikon kokoisia; polku on meta-tekstiä eli
    pienempää mutta silti valikon kokoluokkaa."""
    page, errors = open_search(browser, base_url, "maailma")
    assert page.evaluate(
        f"!!{SHADOW}.querySelector('link[href*=\"assets/css/search.css\"]')")

    body = font_size(page, ".md-content__inner p", root="document")
    nav = font_size(page, ".md-nav__link", root="document")
    assert body > 16 and nav > 15  # rem on 22 px, ei 20 px

    assert font_size(page, ".x") >= body       # tuloksen otsikko
    assert font_size(page, ".s input") >= body  # hakukenttä
    assert font_size(page, ".u") >= nav         # ote
    assert font_size(page, ".n") >= 0.9 * nav   # polku
    assert errors == []
    page.close()


def test_the_filter_panel_and_its_button_are_gone(browser, base_url):
    """Kenttärivillä näkyvät vain hakukuvake, kenttä ja oma sulkunappi;
    suodatinpaneelia ei näy vaikka sen tila olisi avoin."""
    page, errors = open_search(browser, base_url, "maailma")
    buttons = page.evaluate(
        f"[...{SHADOW}.querySelectorAll('.k button')]"
        ".map(b => [b.className, b.getClientRects().length > 0])")
    assert buttons == [["r", True], ["r", False], ["r jyu-close", True]]
    assert not is_shown(page, ".a")
    assert errors == []
    page.close()


@pytest.mark.parametrize("viewport", [(390, 844), (1600, 900)])
def test_the_close_button_closes_the_window(browser, base_url, viewport):
    """Puhelimella ikkuna täyttää koko ruudun, eikä Escapea tai napautettavaa
    taustaa ole: sulkunappi on ikkunan oikeassa yläkulmassa ja sulkee sen.
    Nappi ei jää kohdistetuksi näkymättömiin, ja ikkuna aukeaa uudestaan
    nappeineen."""
    page, errors = open_search(browser, base_url, "maailma", viewport)
    # Ikkuna aukeaa skaalaten (transition); mitat vasta sen päätyttyä.
    page.wait_for_function(
        f"getComputedStyle({SHADOW}.querySelector('.l')).transform === 'none'")
    window, button = page.evaluate(
        f"['.l', '.jyu-close'].map(s => {SHADOW}.querySelector(s).getBoundingClientRect().toJSON())")
    if viewport[0] <= 740:
        assert (window["width"], window["height"]) == viewport
    assert button["right"] > window["right"] - 20
    assert button["top"] < window["top"] + 20
    assert page.evaluate(f"{SHADOW}.querySelector('.jyu-close').ariaLabel") == "Sulje haku"

    page.evaluate(f"{SHADOW}.querySelector('.jyu-close').click()")
    page.wait_for_function(f"{SHADOW}.querySelector('.l').classList.contains('d')")
    page.wait_for_function(f"{SHADOW}.activeElement === null")

    page.click("label[for=__search]" if viewport[0] <= 740 else ".md-search__button")
    page.wait_for_function(f"{SHADOW}.activeElement?.tagName === 'INPUT'")
    assert not page.evaluate(f"{SHADOW}.querySelector('.l').classList.contains('d')")
    assert page.evaluate(f"{SHADOW}.querySelectorAll('.jyu-close').length") == 1
    assert errors == []
    page.close()


def test_the_field_placeholder_is_finnish(browser, base_url):
    """Zensicalin kentässä lukee kiinteästi "Search"; search.js vaihtaa sen.
    Vaihto pysyy, kun ikkuna piirretään tuloksineen uudelleen ja kun se
    suljetaan ja avataan uudestaan."""
    page, errors = open_search(browser, base_url, "maailma")
    placeholder = f"{SHADOW}.querySelector('.s input').placeholder"
    assert page.evaluate(placeholder) == "Hae"

    page.keyboard.press("Escape")
    page.click(".md-search__button")
    page.wait_for_function(f"{SHADOW}.activeElement?.tagName === 'INPUT'")
    assert page.evaluate(placeholder) == "Hae"
    assert errors == []
    page.close()


def test_the_rules_do_not_leak_into_the_page(browser, base_url):
    """Sama tiedosto on ladattu sivulle, mutta :host-alkuiset säännöt eivät
    osu sivun elementteihin: yksikirjaimiset luokat ovat vapaita."""
    page, errors = open_search(browser, base_url, "maailma")
    display = page.evaluate(
        "() => { const el = document.createElement('div'); el.className = 'a x';"
        " document.body.append(el); return getComputedStyle(el).display; }")
    assert display == "block"
    assert errors == []
    page.close()


def test_arrow_keys_leave_only_the_selected_result_highlighted(browser, base_url):
    """Zensical korostaa sekä valitun että hiiren alla olevan tuloksen ja
    vierittää listaa nuolilla liikuttaessa, jolloin paikallaan olevan hiiren
    korostus hyppisi rivien mukana. Nuolinäppäin sammuttaa hiiren korostuksen,
    ja hiiren liike palauttaa sen."""
    page, errors = open_search(browser, base_url, "a")
    results = f"[...{SHADOW}.querySelectorAll('.b .i')]"
    assert page.evaluate(f"{results}.length") >= 3
    highlighted = (
        f"{results}.map((a, i) => [i, getComputedStyle(a, '::before').opacity])"
        ".filter(([, opacity]) => opacity === '1').map(([i]) => i)")

    # Hiiri kolmannen tuloksen päälle: valittu (1.) ja hiiren alla oleva.
    box = page.evaluate(
        f"(({{x, y, width, height}}) => [x + width / 2, y + height / 2])"
        f"({results}[2].getBoundingClientRect())")
    page.mouse.move(*box)
    page.wait_for_function(f"{highlighted}.join() === '0,2'")

    page.keyboard.press("ArrowDown")
    page.wait_for_function(f"{highlighted}.join() === '1'")

    page.mouse.move(box[0] + 5, box[1] + 5)
    page.wait_for_function(f"{highlighted}.length === 2")
    assert errors == []
    page.close()
