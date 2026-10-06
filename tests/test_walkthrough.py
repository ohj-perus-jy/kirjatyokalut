"""Vaiheittainen ohje koekirjalla (assets/js/walkthrough.js).

Koesivu osa1/vaiheet.md on SUMMARY.md:n ulkopuolella, jotta muiden testien
laskemat luvut eivät muutu: kuusi vaihetta kolmessa luvussa, kohtaukset
tiedostossa osa1/images/vaiheet.js. Luvun Kuvat vaiheissa on kuvia, jotka
avautuvat suurina (koekirjan kirja.toml: kuvasuurennus). Esitys syntyy vasta
selaimessa, joten sivu avataan oikeasti, ja jokainen testi saa oman
selainkontekstin, koska osoite ja esityksen tila muuttuvat.
"""

import pytest

LIVE = ".jyu-walk--live .jw-win"
DESKTOP = {"width": 1280, "height": 900}
PHONE = {"width": 390, "height": 844}

# Näkyvät luvut (h2:n tunniste) ja vaiheet (h3:n tunniste) järjestyksessä.
SHOWN = """root => [...root.querySelectorAll(':scope > h2, :scope > .jyu-step')]
  .filter(element => getComputedStyle(element).display !== 'none')
  .map(element => element.querySelector('h3')?.id ?? element.id)"""

EVERYTHING = ["alku", "avaa-sivu", "anna-komento", "loppu", "kirjaudu",
              "kuvat", "katso-kuvakaappaus", "tallenna-tiedosto", "vertaa-tulosta"]

# Piirrosalustan leveys näyttämön leveyteen verrattuna.
CANVAS_PER_STAGE = """() => document.querySelector('.jw-canvas').getBoundingClientRect().width
  / document.querySelector('.jw-stage').clientWidth"""


@pytest.fixture(scope="session")
def walk_url(book, serve) -> str:
    return f"{serve(book.site)}/osa1/vaiheet/"


@pytest.fixture
def opened(browser, walk_url):
    """opened(ankkuri, reduced_motion, block, viewport, ready) -> (sivu, virheet).
    ready: odota, että esitys on piirretty."""
    contexts = []

    def open_page(fragment="", reduced_motion="no-preference", block=None,
                  viewport=DESKTOP, ready=True, init=None):
        context = browser.new_context(reduced_motion=reduced_motion, viewport=viewport,
                                      has_touch=viewport is PHONE)
        contexts.append(context)
        if init:
            context.add_init_script(init)
        page = context.new_page()
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("console", lambda message: message.type == "error"
                and errors.append(f"{message.text} {message.location['url']}".strip()))
        if block:
            page.route(block, lambda route: route.abort())
        page.goto(walk_url + fragment, wait_until="load")
        if ready:
            page.wait_for_selector(LIVE)
        return page, errors

    yield open_page
    for context in contexts:
        context.close()


def shown(page) -> list[str]:
    return page.eval_on_selector(".jyu-walk", SHOWN)


def test_one_step_is_shown_at_a_time(opened):
    """Luvun otsikot ja muut vaiheet piiloon; luvuista napit, vaiheista aikajana."""
    page, errors = opened()
    assert shown(page) == ["avaa-sivu"]
    assert page.inner_text(".jw-count") == "Vaihe 1 / 6"
    assert page.eval_on_selector_all(
        ".jw-pill", "buttons => buttons.map(b => b.textContent)") == ["Alku", "Loppu", "Kuvat"]
    assert page.locator(".jw-tick").count() == 6
    assert page.is_disabled(".jw-prev")
    assert not page.is_disabled(".jw-next")
    assert not page.is_visible(".jw-zoom")
    assert page.evaluate(CANVAS_PER_STAGE) == pytest.approx(1, abs=0.01)
    assert errors == []


def test_the_walkthrough_opens_waiting_for_the_play_button(opened):
    """Sivun avautuessa vaihe on alussaan ja näyttämöllä on iso toistonappi,
    josta animaatio lähtee; kulman kuvakkeet toimivat napin päällä. Seuraava
    ottaa napin pois, ja tekstistä palatessa esitys odottaa taas. Jaettu osoite
    avaa vaiheensa samoin."""
    page, errors = opened()
    typed = "document.querySelector('.koe-teksti').textContent"
    assert page.is_visible(".jw-play")
    assert page.evaluate(typed) == ""
    assert page.locator(".jw-ring").count() == 0
    page.click(".jw-full")
    assert "jyu-walk--full" in page.get_attribute(".jyu-walk", "class")
    assert page.is_visible(".jw-play")
    page.click(".jw-full")
    page.click(".jw-play")
    assert not page.is_visible(".jw-play")
    page.wait_for_function(f"{typed} === 'Hei'")
    page.wait_for_selector(".jw-ring")
    page.click(".jw-mode")
    page.click(".jw-mode")
    assert page.is_visible(".jw-play")
    assert page.evaluate(typed) == ""
    page.click(".jw-next")
    assert not page.is_visible(".jw-play")
    other, other_errors = opened("#kirjaudu")
    assert shown(other) == ["kirjaudu"]
    assert other.is_visible(".jw-play")
    assert other.locator(".koe-lopuksi.jw-hidden").count() == 1
    assert other_errors == []
    assert errors == []


def test_markdown_inside_a_step_is_converted(opened):
    """markdown="1": vaiheen sisällä käännetään kuten muualla aidat,
    alertit (myös niiden luettelo ja aita), luettelo, näppäimet, linkit ja
    kuvat."""
    page, errors = opened()
    page.click(".jw-mode")
    assert page.locator(".jyu-step pre code").count() == 2
    assert page.locator(".jyu-step .admonition").count() == 2
    assert page.locator(".jyu-step .admonition ol > li").count() == 2
    assert page.locator(".jyu-step .admonition li pre code").count() == 1
    assert page.locator(".jyu-step ul > li > code").count() == 2
    assert page.locator(".jyu-step kbd").count() == 2
    assert page.locator(".jyu-step p a[href='#avaa-sivu']").count() == 1
    assert page.locator(".jyu-step a[href='../01-hei/']").count() == 1
    assert page.locator(".jyu-step img").count() == 2
    assert errors == []


def test_next_animates_the_step(opened):
    """Komennot kirjoittuvat merkki kerrallaan; tuloste ja seuraavan komennon
    rivi näkyvät vasta edellisen komennon jälkeen."""
    page, errors = opened()
    page.click(".jw-next")
    assert shown(page) == ["anna-komento"]
    commands = page.locator(".jw-terminal [data-type]")
    assert commands.count() == 2
    assert not commands.nth(1).is_visible()
    page.wait_for_function(
        "document.querySelectorAll('.jw-terminal [data-type]')[1].textContent === 'git status'")
    page.wait_for_function("!document.querySelector('.jw-terminal .jw-hidden')")
    assert "new file:   a.txt" in page.inner_text(".jw-terminal")
    assert errors == []


def test_previous_shows_the_finished_step_at_once(opened):
    """Taaksepäin ei animoida: teksti, klikkauksen luokka ja kehys ovat heti paikallaan."""
    page, errors = opened()
    page.click(".jw-next")
    page.click(".jw-prev")
    assert shown(page) == ["avaa-sivu"]
    assert page.inner_text(".koe-teksti") == "Hei"
    assert "jw-on" in page.get_attribute(".koe-nappi", "class")
    assert page.locator(".jw-ring").count() == 1
    assert errors == []


def test_reduced_motion_shows_the_finished_step(opened):
    """prefers-reduced-motion: vaihe on heti valmiina ilman toistonappia, ja
    Seuraavakin näyttää vaiheen valmiina."""
    page, errors = opened(reduced_motion="reduce")
    assert not page.is_visible(".jw-play")
    assert page.inner_text(".koe-teksti") == "Hei"
    assert page.locator(".jw-ring").count() == 1
    page.click(".jw-next")
    assert "$ git status" in page.inner_text(".jw-terminal")
    assert page.locator(".jw-terminal .jw-hidden").count() == 0
    assert errors == []


def test_hidden_element_is_gone_when_the_step_is_finished(opened):
    """data-hide: elementti tulee näkyviin ja poistuu kohdassaan (aikajanan
    merkki toistaa vaiheen alusta), ja valmiissa vaiheessa se on poissa myös
    suoraan piirrettynä; kursori katoaa, kun klikattavaa ei jää."""
    page, errors = opened()
    page.click(".jw-tick >> nth=2")
    page.wait_for_function(
        "!document.querySelector('.koe-ikkuna').classList.contains('jw-hidden')")
    page.wait_for_function(
        "document.querySelector('.koe-ikkuna').classList.contains('jw-gone')")
    page.wait_for_function("!document.querySelector('.koe-lopuksi.jw-hidden')")
    assert not page.is_visible(".jw-cursor")
    other, other_errors = opened("#kirjaudu", reduced_motion="reduce")
    assert "jw-gone" in other.get_attribute(".koe-ikkuna", "class")
    assert other.is_visible(".koe-lopuksi")
    assert not other.is_visible(".jw-cursor")
    assert other_errors == []
    assert errors == []


def test_scroll_moves_the_content_up(opened):
    """data-scroll: pitkä sisältö vierittyy kohdassaan; valmiissa vaiheessa
    vieritys on heti paikallaan."""
    page, errors = opened()
    scrolled = "getComputedStyle(document.querySelector('.koe-vieritys')).transform"
    page.click(".jw-tick >> nth=2")
    assert page.evaluate(scrolled) == "none"
    page.wait_for_function(f"{scrolled} === 'matrix(1, 0, 0, 1, 0, -40)'")
    other, other_errors = opened("#kirjaudu", reduced_motion="reduce")
    assert other.evaluate(scrolled) == "matrix(1, 0, 0, 1, 0, -40)"
    assert other_errors == []
    assert errors == []


def test_arrow_keys_change_the_step(opened):
    """Nuolet toimivat, kun kohdistus on ohjeessa (klikkaus kohtaukseen)."""
    page, errors = opened()
    page.click(".jw-stage")
    page.keyboard.press("ArrowRight")
    assert shown(page) == ["anna-komento"]
    page.keyboard.press("ArrowLeft")
    assert shown(page) == ["avaa-sivu"]
    assert errors == []


def test_swipe_changes_the_step(opened):
    """Vaakapyyhkäisy kosketuksella: vasemmalle seuraava, oikealle edellinen;
    lyhyt liike ei ole pyyhkäisy."""
    page, errors = opened()

    def swipe(dx):
        page.dispatch_event(".jw-stage", "pointerdown",
                            {"pointerType": "touch", "clientX": 500, "clientY": 300})
        page.dispatch_event(".jw-stage", "pointerup",
                            {"pointerType": "touch", "clientX": 500 + dx, "clientY": 310})

    swipe(-120)
    assert shown(page) == ["anna-komento"]
    swipe(-20)
    assert shown(page) == ["anna-komento"]
    swipe(120)
    assert shown(page) == ["avaa-sivu"]
    assert errors == []


def test_the_address_follows_the_step(opened):
    """Vaiheen otsikon tunniste tulee osoitteeseen, ja sama osoite avaa sen
    vaiheen; luvun tunniste avaa luvun ensimmäisen vaiheen."""
    page, errors = opened()
    page.click(".jw-next")
    assert page.evaluate("location.hash") == "#anna-komento"
    page.evaluate("location.hash = '#kirjaudu'")
    page.wait_for_function("document.querySelector('.jw-count').textContent === 'Vaihe 3 / 6'")
    for fragment, expected in (("#anna-komento", ["anna-komento"]), ("#loppu", ["kirjaudu"])):
        other, other_errors = opened(fragment)
        assert shown(other) == expected, fragment
        assert other_errors == []
    assert errors == []


def test_link_in_a_step_opens_the_other_step(opened):
    """Vaiheen tekstin linkki toiseen vaiheeseen avaa sen vaiheen."""
    page, errors = opened("#vertaa-tulosta")
    page.click(".jyu-step--current a[href='#avaa-sivu']")
    page.wait_for_function("document.querySelector('.jw-count').textContent === 'Vaihe 1 / 6'")
    assert shown(page) == ["avaa-sivu"]
    assert errors == []


def test_contents_link_plays_the_step_from_the_start(opened):
    """Sisällysluettelon linkki vaiheeseen toistaa sen animaation alusta heti
    ilman toistonappia, myös nykyisen vaiheen linkki."""
    page, errors = opened()
    link = ".md-sidebar--secondary a[href='#kirjaudu']"
    page.click(link)
    page.wait_for_selector(".koe-lopuksi.jw-hidden", state="attached")
    assert shown(page) == ["kirjaudu"]
    assert not page.is_visible(".jw-play")
    page.wait_for_selector(".koe-lopuksi:not(.jw-hidden)", state="attached")
    page.click(link)
    page.wait_for_selector(".koe-lopuksi.jw-hidden", state="attached")
    assert errors == []


def test_chapter_button_plays_the_first_step_of_the_chapter(opened):
    """Luvun nappi avaa luvun ensimmäisen vaiheen ja toistaa sen alusta."""
    page, errors = opened()
    page.click(".jw-pill:has-text('Loppu')")
    assert shown(page) == ["kirjaudu"]
    assert page.locator(".koe-lopuksi.jw-hidden").count() == 1
    assert page.get_attribute(".jw-pill:has-text('Loppu')", "aria-current") == "true"
    assert page.get_attribute(".jw-pill:has-text('Alku')", "aria-current") == "false"
    assert errors == []


def test_text_mode_shows_the_whole_walkthrough(opened):
    """Tekstinä: kaikki luvut ja vaiheet näkyviin, kohtaus ja ohjaimet piiloon.
    Leveällä palstalla ei ilmoitusta puhelimesta."""
    page, errors = opened()
    page.click(".jw-mode")
    assert shown(page) == EVERYTHING
    assert not page.is_visible(".jw-stage")
    assert not page.is_visible(".jw-next")
    assert not page.is_visible(".jw-notice")
    assert page.inner_text(".jw-mode") == "Näytä esityksenä"
    page.click(".jw-mode")
    assert shown(page) == ["avaa-sivu"]
    assert errors == []


def test_full_screen_puts_the_text_beside_the_scene(opened):
    """Koko ruutu näyttämön oikean alakulman kuvakkeesta: kohtaus vasemmalla
    koko korkeudeltaan näkyvissä ja vaiheen teksti sen oikealla puolella;
    kuvakkeesta ja Escistä takaisin sivulle."""
    page, errors = opened()
    stage = page.locator(".jyu-walk .jw-stage").bounding_box()
    button = page.locator(".jw-full").bounding_box()
    assert page.get_attribute(".jw-full", "aria-label") == "Koko ruutu"
    assert button["x"] + button["width"] <= stage["x"] + stage["width"]
    assert button["y"] + button["height"] <= stage["y"] + stage["height"]
    assert button["x"] > stage["x"] + stage["width"] / 2
    assert button["y"] > stage["y"] + stage["height"] / 2
    page.click(".jw-full")
    assert "jyu-walk--full" in page.get_attribute(".jyu-walk", "class")
    assert page.get_attribute(".jw-full", "aria-label") == "Sulje koko ruutu (Esc)"
    page.wait_for_function("document.querySelector('.jw-stage').clientWidth > 700")
    stage = page.locator(".jyu-walk .jw-stage").bounding_box()
    text = page.locator(".jyu-step--current").bounding_box()
    height = page.evaluate("innerHeight")
    assert page.locator(".jyu-walk").bounding_box()["width"] == page.evaluate("innerWidth")
    assert stage["x"] + stage["width"] <= text["x"] + 1
    assert 0 <= stage["y"] and stage["y"] + stage["height"] <= height
    assert text["y"] < stage["y"] + stage["height"]
    assert page.evaluate(CANVAS_PER_STAGE) == pytest.approx(1, abs=0.01)
    page.click(".jw-full")
    assert "jyu-walk--full" not in page.get_attribute(".jyu-walk", "class")
    page.click(".jw-full")
    page.keyboard.press("Escape")
    page.wait_for_function(
        "!document.querySelector('.jyu-walk').classList.contains('jyu-walk--full')")
    assert page.get_attribute(".jw-full", "aria-label") == "Koko ruutu"
    assert errors == []


# Ääni kirjataan eikä soiteta: play ja pause korvataan ennen sivun skriptejä.
# Kirjaan tulee vaiheen kohtaus, koska leikkeen nimi on tiiviste.
RECORD_AUDIO = """
window.played = [];
window.paused = 0;
HTMLMediaElement.prototype.play = function () {
  const file = this.src.split('/').pop();
  const step = document.querySelector(`.jyu-step[data-audio$="/${file}"]`);
  window.played.push(step ? step.dataset.scene : file);
  return Promise.resolve();
};
HTMLMediaElement.prototype.pause = function () { window.paused += 1; };
"""


def test_speaker_reads_each_step_aloud(opened):
    """Kaiutin päälle: vaihe alkaa alusta kuten Toista-napista, ja sen oma ääni
    soi heti ja jokaisessa vaiheessa, johon siirrytään. Vaihe, jonka
    leike puuttuu, ei soi (koekirjan komento). Pois päältä ääni pysähtyy, mutta
    vaihe ei ala alusta. Valinta muistetaan, mutta sivun avautuessa (osoitteen
    vaiheeseen) ääni alkaa vasta toistonapista. Tekstinä kaiutinta ei ole."""
    page, errors = opened(init=RECORD_AUDIO)
    typed = "document.querySelector('.koe-teksti').textContent"
    assert page.get_attribute(".jw-speak", "aria-pressed") == "false"
    page.click(".jw-play")
    page.wait_for_function(f"{typed} === 'Hei'")
    assert page.evaluate("played") == []
    page.click(".jw-speak")
    assert page.get_attribute(".jw-speak", "aria-pressed") == "true"
    assert page.evaluate("played") == ["selain"]
    assert page.evaluate(typed) == ""
    page.click(".jw-next")
    assert page.evaluate("played") == ["selain"]
    page.click(".jw-next")
    page.click(".jw-replay")
    assert page.evaluate("played") == ["selain", "piilotus", "piilotus"]
    page.click(".jw-tick >> nth=2")
    assert page.evaluate("played") == ["selain", "piilotus", "piilotus", "piilotus"]
    page.wait_for_function("!document.querySelector('.koe-lopuksi.jw-hidden')")
    paused = page.evaluate("paused")
    page.click(".jw-speak")
    assert page.get_attribute(".jw-speak", "aria-pressed") == "false"
    assert page.evaluate("paused") > paused
    assert page.evaluate("played.length") == 4
    assert page.is_visible(".koe-lopuksi")
    page.click(".jw-speak")
    page.reload()
    page.wait_for_selector(LIVE)
    assert page.get_attribute(".jw-speak", "aria-pressed") == "true"
    assert page.evaluate("played") == []
    page.click(".jw-play")
    assert page.evaluate("played") == ["piilotus"]
    page.click(".jw-mode")
    assert not page.is_visible(".jw-speak")
    assert errors == []


# Oikea toisto, mutta play-kutsun kohde talteen, jotta toistokohdan voi lukea.
KEEP_AUDIO = """
const play = HTMLMediaElement.prototype.play;
HTMLMediaElement.prototype.play = function () { window.voice = this; return play.call(this); };
"""


def test_replay_starts_the_audio_from_the_beginning(opened):
    """Toista aloittaa myös äänen alusta, vaikka tiedosto on sama. Oikea
    toisto: koekirjan leikkeet ovat 3 sekuntia hiljaisuutta (conftest.py)."""
    page, errors = opened(init=KEEP_AUDIO)
    page.click(".jw-speak")
    page.wait_for_function("window.voice && voice.currentTime > 1")
    page.click(".jw-replay")
    assert page.evaluate("voice.currentTime") < 0.5
    page.wait_for_function("!voice.paused && voice.currentTime > 0")
    assert errors == []


def test_phone_opens_the_walkthrough_as_text(opened):
    """Kapea palsta: ohje tekstinä ja ilmoitus; esityksen saa napista, ja se
    avautuu lähikuvana, josta pääsee koko kuvaan."""
    page, errors = opened(viewport=PHONE, ready=False)
    page.wait_for_selector(".jyu-walk--text")
    assert shown(page) == EVERYTHING
    assert page.is_visible(".jw-notice")
    assert not page.is_visible(".jw-stage")
    page.click(".jw-mode")
    assert shown(page) == ["avaa-sivu"]
    assert page.is_visible(".jw-play")
    assert page.is_visible(".jw-zoom")
    assert page.inner_text(".jw-zoom") == "Koko kuva"
    assert page.evaluate(CANVAS_PER_STAGE) > 1.3
    assert errors == []


def test_close_up_keeps_the_marked_spot_in_view(opened):
    """Lähikuva keskittää korostuksen, vaikka koko kohtaus ei mahdu näkyviin;
    Koko kuva -napista kohtaus palaa näyttämön levyiseksi. Ikkunan
    kaventaminen esityksen ollessa auki ei vaihda tekstiin."""
    page, errors = opened()
    page.click(".jw-play")
    page.wait_for_selector(".jw-ring")
    page.set_viewport_size({"width": 420, "height": 800})
    page.wait_for_selector(".jw-zoom:not([hidden])")
    assert shown(page) == ["avaa-sivu"]
    inside = page.evaluate("""() => {
      const stage = document.querySelector('.jw-stage').getBoundingClientRect();
      const ring = document.querySelector('.jw-ring').getBoundingClientRect();
      return ring.left >= stage.left && ring.right <= stage.right
          && ring.top >= stage.top && ring.bottom <= stage.bottom;
    }""")
    assert inside
    page.click(".jw-zoom")
    assert page.inner_text(".jw-zoom") == "Lähikuva"
    assert page.evaluate(CANVAS_PER_STAGE) == pytest.approx(1, abs=0.01)
    assert errors == []


def test_without_scenes_the_walkthrough_stays_text(opened):
    """Kohtaustiedosto ei latautunut: esitystä ei tehdä, ja ohje luetaan tekstinä."""
    page, _ = opened(block="**/images/vaiheet.js", ready=False)
    assert page.locator(".jw-ui").count() == 0
    assert shown(page) == EVERYTHING


# --- Kuvasuurennus (koekirjan kirja.toml: kuvasuurennus) ----------------------
# Luvun Kuvat kahdessa vaiheessa on kuva. Teema lataa GLightboxin unpkg.com:sta.

LIGHTBOX = ".glightbox-container .gslide.current img"

# Onko ikkunan keskellä päällimmäisenä suurennus.
LIGHTBOX_ON_TOP = """() => Boolean(document.elementFromPoint(innerWidth / 2, innerHeight / 2)
  ?.closest('.glightbox-container'))"""


def open_image(page):
    page.click(".jyu-step--current a.glightbox")
    page.wait_for_selector(LIGHTBOX)


def close_image(page):
    page.keyboard.press("Escape")
    page.wait_for_selector(".glightbox-container", state="detached")


def test_image_in_a_step_opens_large(opened):
    """Vaiheen kuva avautuu suurena päällimmäiseksi. Galleriassa on vain
    vaiheen oma kuva, ei toisen vaiheen piilossa olevaa. Nuolet eivät vaihda
    vaihetta suurennuksen ollessa auki, ja Esc sulkee vain suurennuksen.
    Sulkemisen jälkeen nuolet vaihtavat taas vaihetta."""
    page, errors = opened("#katso-kuvakaappaus")
    open_image(page)
    assert page.evaluate(LIGHTBOX_ON_TOP)
    assert page.locator(".glightbox-container .gslide").count() == 1
    page.keyboard.press("ArrowRight")
    page.keyboard.press("ArrowLeft")
    assert shown(page) == ["katso-kuvakaappaus"]
    close_image(page)
    assert shown(page) == ["katso-kuvakaappaus"]
    page.keyboard.press("ArrowRight")
    assert shown(page) == ["tallenna-tiedosto"]
    assert errors == []


def test_image_opens_large_in_full_screen(opened):
    """Koko ruudussa suurennus tulee ohjeen päälle: selaimen koko näytön
    tilassa on koko sivu, koska pelkkä ohje piilottaisi bodyyn tulevan
    suurennuksen. Esc sulkee ensin suurennuksen ja sitten koko ruudun."""
    page, errors = opened("#katso-kuvakaappaus")
    page.click(".jw-full")
    open_image(page)
    assert page.evaluate(LIGHTBOX_ON_TOP)
    close_image(page)
    assert "jyu-walk--full" in page.get_attribute(".jyu-walk", "class")
    page.keyboard.press("Escape")
    page.wait_for_function(
        "!document.querySelector('.jyu-walk').classList.contains('jyu-walk--full')")
    assert errors == []


def test_image_opens_large_on_a_phone(opened):
    """Puhelimessa ohje on tekstinä, ja vaiheen kuvan saa suureksi."""
    page, errors = opened(viewport=PHONE, ready=False)
    page.wait_for_selector(".jyu-walk--text")
    page.locator(".jyu-step a.glightbox").first.tap()
    page.wait_for_selector(LIGHTBOX)
    assert page.evaluate(LIGHTBOX_ON_TOP)
    assert errors == []


# --- Yksittäinen animaatio (<animation>, walkthrough.js: enhanceAnimation) ----
# Koesivun lopussa toisella välilehdellä listan kohdassa, varakuvana kuva.png.

ANIMATION_TEXT = "document.querySelector('.koe-anim-teksti').textContent"


def open_animation_tab(page):
    """Toinen välilehti auki ja animaatio näkyviin."""
    page.click(".tabbed-labels label:has-text('Toka')")
    page.locator(".jyu-anim .jw-stage").scroll_into_view_if_needed()


def test_animation_plays_when_it_comes_into_view(opened):
    """Kohtaus tulee varasisällön tilalle ja odottaa alussaan, kun sen
    välilehti on piilossa; välilehti auki ja näkyviin, niin se soi loppuun."""
    page, errors = opened()
    page.wait_for_selector(".jyu-anim--live", state="attached")
    page.wait_for_timeout(600)
    assert page.evaluate(ANIMATION_TEXT) == ""
    open_animation_tab(page)
    assert page.eval_on_selector(".jyu-anim > p", "p => p.getBoundingClientRect().height") <= 1
    page.wait_for_function(f"{ANIMATION_TEXT} === 'Moi'")
    page.wait_for_selector(".jyu-anim .jw-ring")
    assert "jw-on" in page.get_attribute(".koe-anim-nappi", "class")
    assert errors == []


def test_animation_replay_starts_from_the_beginning(opened):
    """Toista: kohtaus alkaa alusta ja soi uudelleen loppuun."""
    page, errors = opened()
    open_animation_tab(page)
    page.wait_for_selector(".jyu-anim .jw-ring")
    page.click(".jyu-anim .jw-replay")
    assert page.evaluate(ANIMATION_TEXT) == ""
    assert page.locator(".jyu-anim .jw-ring").count() == 0
    page.wait_for_selector(".jyu-anim .jw-ring")
    assert page.evaluate(ANIMATION_TEXT) == "Moi"
    assert errors == []


def test_type_delay_and_wait_slow_the_animation_down(opened):
    """data-type="100": kolme merkkiä vie vähintään 200 ms. data-wait="1200":
    klikkaus tulee vasta tauon jälkeen (ilman taukoa alle sekunnissa)."""
    page, errors = opened()
    page.evaluate("""() => {
        window.times = {};
        const text = document.querySelector('.koe-anim-teksti');
        const button = document.querySelector('.koe-anim-nappi');
        new MutationObserver(() => {
            const length = text.textContent.length;
            if (length === 1) times.first ??= performance.now();
            if (length === 3) times.typed ??= performance.now();
            if (button.classList.contains('jw-on')) times.clicked ??= performance.now();
        }).observe(text.closest('.jw-canvas'),
            { subtree: true, childList: true, characterData: true, attributes: true });
    }""")
    open_animation_tab(page)
    page.wait_for_function("window.times.clicked")
    times = page.evaluate("times")
    assert times["typed"] - times["first"] >= 190
    assert times["clicked"] - times["typed"] >= 1900
    assert errors == []


def test_animation_has_a_close_up_in_a_narrow_column(opened):
    """Kapeassa palstassa yksittäinenkin animaatio on lähikuvana, ja Koko
    kuva -napista kohtaus palaa näyttämön levyiseksi. Leveässä nappia ei ole."""
    scale = """() => {
      const stage = document.querySelector('.jyu-anim .jw-stage');
      return stage.querySelector('.jw-canvas').getBoundingClientRect().width / stage.clientWidth;
    }"""
    wide, wide_errors = opened()
    open_animation_tab(wide)
    assert not wide.is_visible(".jyu-anim .jw-zoom")
    page, errors = opened(viewport=PHONE, ready=False)
    page.wait_for_selector(".jyu-anim--live", state="attached")
    open_animation_tab(page)
    page.wait_for_selector(".jyu-anim .jw-ring")
    assert page.inner_text(".jyu-anim .jw-zoom") == "Koko kuva"
    assert page.evaluate(scale) > 1.3
    page.click(".jyu-anim .jw-zoom")
    assert page.inner_text(".jyu-anim .jw-zoom") == "Lähikuva"
    assert page.evaluate(scale) == pytest.approx(1, abs=0.01)
    assert wide_errors == []
    assert errors == []


def test_reduced_motion_shows_the_finished_animation(opened):
    """prefers-reduced-motion: kohtaus valmiina, kun se tulee näkyviin."""
    page, errors = opened(reduced_motion="reduce")
    open_animation_tab(page)
    page.wait_for_selector(".jyu-anim .jw-ring")
    assert page.evaluate(ANIMATION_TEXT) == "Moi"
    assert "jw-on" in page.get_attribute(".koe-anim-nappi", "class")
    assert errors == []


def test_printed_animation_shows_its_content(opened):
    """Tulosteessa kohtauksen tilalla on tagin sisältö."""
    page, errors = opened()
    page.wait_for_selector(".jyu-anim--live", state="attached")
    page.emulate_media(media="print")
    assert page.eval_on_selector(".jw-anim", "e => getComputedStyle(e).display") == "none"
    assert page.eval_on_selector(".jyu-anim > p", "p => getComputedStyle(p).position") == "static"
    assert errors == []


def test_hidden_animation_content_has_no_image_link(opened):
    """Kohtauksen tilalle piilotetun varasisällön kuva ei avaudu suurena:
    linkki olisi näkymätön sarkainpysäkki. Kuva jää ruudunlukijalle ja
    tulosteeseen."""
    page, errors = opened()
    page.wait_for_selector(".jyu-anim--live", state="attached")
    assert page.locator(".jyu-anim a").count() == 0
    assert page.locator(".jyu-anim img").count() == 1
    assert errors == []


def test_without_scenes_the_animation_shows_its_content(opened):
    """Kohtaustiedosto ei latautunut: animaatiota ei tehdä, ja varakuva näkyy
    ja avautuu suurena kuten muutkin kuvat."""
    page, _ = opened(block="**/images/vaiheet.js", ready=False)
    page.click(".tabbed-labels label:has-text('Toka')")
    assert page.locator(".jyu-anim--live").count() == 0
    assert page.is_visible(".jyu-anim a.glightbox img")
