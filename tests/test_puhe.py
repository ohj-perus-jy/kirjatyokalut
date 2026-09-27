"""Ääneenluku: äänten teko (puhe.py) ilman puhepalvelua, merkkien vaikutus
sivuun oikealla jäsentimellä ja soitin (assets/js/puhe.js) selaimessa.

Synteesi korvataan funktiolla, joka kirjaa pyynnöt. Koko sivun koesivu on
osa1/puhe.md (SUMMARY.md:n ulkopuolella), ja koekirjan äänivaraston täyttää
conftest.py: copy_book valeäänillä, yhtä leikettä lukuun ottamatta
(MISSING_SPEECH).
"""

import re
import shutil
import subprocess
import sys
from html.parser import HTMLParser

import pytest

import convert
import puhe
from conftest import MISSING_SPEECH, MISSING_STEP, copy_book

PAGE = ('<walkthrough scenes="images/k.js" audio>\n\n'
        '<step scene="a">\n\nEka.\n\n</step>\n\n'
        '<step scene="b">\n\nToka.\n\n</step>\n\n'
        "</walkthrough>\n")


def test_ssml_escapes_the_text_and_keeps_the_lines_as_paragraphs():
    assert puhe.ssml("A & B.\nC <D>.", "fi-FI-NooraNeural") == (
        '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="fi-FI">'
        '<voice name="fi-FI-NooraNeural"><p>A &amp; B.</p><p>C &lt;D&gt;.</p></voice></speak>')


def test_the_voice_says_the_words_it_would_misread():
    assert convert.speech_say("Kielet C#, Java ja C++.") == "Kielet see sharp, Java ja C++."
    assert convert.speech_say("C#-kielessä") == "see sharp-kielessä"
    assert convert.speech_say("C#:n, C#:ssa, C#:ia, C#:iin") == (
        "see sharpin, see sharpissa, see sharpia, see sharpiin")
    assert convert.speech_say("ABC# C#x") == "ABC# C#x"
    assert "<p>see sharp.</p>" in puhe.ssml("C#.")


def test_a_written_ending_is_kept_and_a_letter_name_takes_a_front_vowel():
    assert convert.speech_say("Riderissa, TIMistä ja .NETin") == (
        "raiderissa, Timistä ja dotnetin")
    assert convert.speech_say("macOS:ssä, macOS:lla ja macOS: Pääte") == (
        "mäk oo äsässä, mäk oo äsällä ja mäk oo äs: Pääte")
    assert convert.speech_say("Rider IDE:nä") == "raider idenä"
    assert convert.speech_say("Timer, time, ASP.NET, ohj1ht") == "Timer, time, ASP.NET, ohj1ht"
    assert convert.speech_say("ohj1-kansio") == "oo hoo jii yksi-kansio"


# --- Leikkeet ja varasto ----------------------------------------------------------

@pytest.fixture
def store(tmp_path, monkeypatch):
    """Tyhjä äänivarasto ja git-identiteetti committeja varten."""
    folder = tmp_path / "puhe"
    monkeypatch.setattr(convert, "SPEECH_STORE", folder)
    for name in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{name}_NAME", "Testi")
        monkeypatch.setenv(f"GIT_{name}_EMAIL", "testi@example.invalid")
    return folder


def test_refresh_clips_makes_each_missing_text_once(store):
    """Sama teksti kahdesti on yksi leike; olemassa olevaa ei pyydetä, joten
    toinen ajo ei tee mitään. Tiedoston nimi on leikkeen tunniste."""
    requests: list[str] = []

    def synthesize(document: str) -> bytes:
        requests.append(document)
        return b"mp3"

    def refresh(texts: list[str]) -> list[str]:
        return puhe.refresh_clips(texts, synthesize, log=lambda _: None)

    assert refresh(["Eka.", "Toka.", "Eka."]) == [
        convert.speech_clip("Eka."), convert.speech_clip("Toka.")]
    assert len(requests) == 2 and "<p>Eka.</p>" in requests[0]
    assert refresh(["Toka.", "Eka."]) == []
    assert sorted(file.name for file in store.iterdir()) == sorted(
        f"{convert.speech_clip(text)}.mp3" for text in ("Eka.", "Toka."))


def test_walkthrough_steps_are_clips_in_the_same_store(store, tmp_path, monkeypatch):
    """Vaiheittaisen ohjeen vaihe on leike kuten sivun kappale: ajo löytää
    ohjeen, jonka tagissa on audio, ja käännös vaiheen leikkeen varastosta.
    Muuttunut vaihe jää äänettömäksi, kunnes sen leike tehdään."""
    src = tmp_path / "src"
    (src / "osa1").mkdir(parents=True)
    (src / "osa1" / "ohje.md").write_text(PAGE, encoding="utf-8")
    (src / "osa1" / "hiljainen.md").write_text(PAGE.replace(" audio>", ">"), encoding="utf-8")
    monkeypatch.setattr(convert, "SRC", src)
    monkeypatch.setattr(convert, "SPEECH_PAGES", ())
    assert puhe.all_pages() == ([], ["osa1/ohje.md"])
    texts = list(puhe.step_texts("osa1/ohje.md").values())
    assert puhe.refresh_clips(texts, lambda _: b"mp3", log=lambda _: None) == [
        convert.speech_clip("Eka."), convert.speech_clip("Toka.")]
    assert convert.walkthrough_audio(PAGE.replace("Toka.", "Toinen."),
                                     convert.available_clips()) == (
        {"a": convert.speech_clip("Eka.")}, ["b"])


def git(*arguments, cwd) -> str:
    return subprocess.run(["git", *arguments], cwd=cwd, check=True,
                          capture_output=True, text=True).stdout


def test_publish_pushes_new_clips_and_survives_a_concurrent_push(store, tmp_path, monkeypatch):
    """Ensimmäinen ajo kloonaa tyhjän varaston; uudet leikkeet (myös
    keskeytyneen ajon) committoidaan ja pushataan. Jos joku muu ehti pushata
    ensin, push onnistuu rebasen jälkeen, koska leikkeet eivät ole ristiriidassa."""
    remote = tmp_path / "varasto.git"
    git("init", "--bare", "--initial-branch=main", str(remote), cwd=tmp_path)
    monkeypatch.setattr(convert, "SPEECH_REPO", str(remote))
    logged: list[str] = []
    assert puhe.ensure_store(log=logged.append)
    assert (store / ".git").is_dir()
    assert puhe.publish(log=logged.append)
    (store / "aaaa.mp3").write_bytes(b"1")
    assert puhe.publish(log=logged.append)
    other = tmp_path / "toinen"
    git("clone", str(remote), str(other), cwd=tmp_path)
    (other / "bbbb.mp3").write_bytes(b"2")
    git("add", "bbbb.mp3", cwd=other)
    git("commit", "-m", "toinen", cwd=other)
    git("push", cwd=other)
    (store / "cccc.mp3").write_bytes(b"3")
    assert puhe.publish(log=logged.append)
    assert git("ls-tree", "--name-only", "main", cwd=remote).split() == [
        "aaaa.mp3", "bbbb.mp3", "cccc.mp3"]
    assert puhe.ensure_store(log=logged.append)
    assert not [line for line in logged if line.startswith("varoitus")]


def test_show_texts_lists_the_units_and_estimates_the_cost(store, monkeypatch):
    """--teksti: jokainen yksikkö ja ohjeen vaihe lajeineen, puuttuvat
    tähdellä, ja yhteenveto uniikeista merkeistä. Leike, joka on jo
    varastossa, ei maksa."""
    monkeypatch.setattr(convert, "SRC", convert.TOOL / "tests" / "book" / "src")
    store.mkdir()
    (store / f"{convert.speech_clip('Viimeinen kappale.')}.mp3").write_bytes(b"")
    lines: list[str] = []
    total, missing = puhe.show_texts(["osa1/puhe.md"], ["osa1/vaiheet.md"], log=lines.append)
    assert "* [koodi] Koodilohko, jota ei lueta ääneen." in lines
    assert "  [kappale] Viimeinen kappale." in lines
    assert "* [välilehdet] 2 välilehteä otsikoilla Windows ja macOS." in lines
    assert f"* [vaihe komento] {MISSING_STEP}" in lines
    assert total - missing == len("Viimeinen kappale.")
    assert lines[-1].startswith("\n") and f"{total} merkkiä" in lines[-1]


def test_an_edit_needs_only_the_changed_paragraph(tmp_path):
    """Leike on kappale: yhden kappaleen korjaus tuottaa yhden uuden tekstin,
    ja muut leikkeet kelpaavat sellaisinaan."""
    source = convert.TOOL / "tests" / "book" / "src" / "osa1" / "puhe.md"
    edited = tmp_path / "puhe.md"
    edited.write_text(source.read_text(encoding="utf-8").replace(
        "Laatikon teksti.", "Laatikon korjattu teksti."), encoding="utf-8")
    before, after = (set(convert.speech_texts(convert.convert_page(page, "osa1/puhe.md").text))
                     for page in (source, edited))
    assert after - before == {"Laatikon korjattu teksti."}
    assert before - after == {"Laatikon teksti."}


def test_strict_build_fails_without_the_store(tmp_path):
    """Julkaisussa (--strict) puuttuva varasto on virhe: sivut jäisivät hiljaa
    äänettömiksi. Varaston kanssa ääneenluvusta ei valiteta."""
    zensical = copy_book(tmp_path)

    def build() -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, "tyokalut/convert.py", "--strict"],
                              cwd=zensical, capture_output=True, text=True)

    assert "äänivarasto" not in build().stderr
    shutil.rmtree(zensical / "puhe")
    result = build()
    assert result.returncode == 1
    assert "virhe: äänivarasto puuttuu" in result.stderr


# --- Merkit eivät muuta sivua ----------------------------------------------------

class Every:
    """Leikejoukko, jossa on jokainen leike."""

    def __contains__(self, clip) -> bool:
        return True


MARKER_RE = re.compile(r'<span class=jyu-puhe data-puhe=[0-9a-f]+></span>| data-puhe="[0-9a-f]+"')
DATA_RE = re.compile(r'\s*<script type="application/json" id="jyu-puhe">.*?</script>', re.S)


def unmarked(text: str) -> str:
    """Merkit pois Markdownista tai HTML:stä (myös tyhjäksi jäävä { })."""
    text = re.sub(r' ?\{ data-puhe="[0-9a-f]+" \}', "", text)
    return DATA_RE.sub("", MARKER_RE.sub("", text)).rstrip()


class Markers(HTMLParser):
    """Merkit renderöidyssä HTML:ssä ja näkyviin jäänyt merkkiteksti."""

    def __init__(self):
        super().__init__()
        self.count = 0
        self.visible: list[str] = []

    def handle_starttag(self, tag, attrs):
        self.count += "data-puhe" in dict(attrs)

    def handle_data(self, data):
        if "puhe" in data and ("data-puhe" in data or "jyu-puhe" in data):
            self.visible.append(data)


def check_pages(zensical_dir) -> int:
    """Jokainen docs/-sivu merkittynä kaikilla leikkeillä: renderöinti ja
    sisällysluettelo ovat merkit pois lukien samat, jokainen merkki päätyy
    attribuutiksi eikä tekstiksi. -> merkkejä yhteensä."""
    from zensical.config import parse_mkdocs_config
    from zensical.markdown.render import render

    parse_mkdocs_config(str(zensical_dir / "mkdocs.yml"))
    total = 0
    docs = zensical_dir / "docs"
    for page in sorted(docs.rglob("*.md")):
        path = page.relative_to(docs).as_posix()
        if path == convert.PRINT_PAGE:
            continue
        text = unmarked(page.read_text(encoding="utf-8")) + "\n"
        units, _ = convert.speech_units(text)
        marked, _, _ = convert.mark_speech(text, Every())
        url = path.removesuffix(".md") + "/"
        plain, spoken = render(text, path, url), render(marked, path, url)
        assert unmarked(spoken["content"]) == plain["content"].rstrip(), path
        assert unmarked(repr(spoken["toc"])) == repr(plain["toc"]), path
        markers = Markers()
        markers.feed(spoken["content"])
        assert markers.visible == [], path
        assert markers.count == len(units), path
        total += markers.count
    return total


def test_markers_do_not_change_the_test_book(book):
    """Koekirjan jokainen sivu, myös ne, joita ei lueta: paloittelun on
    toimittava ennen kuin sivu otetaan ääneenluvun piiriin."""
    assert check_pages(book.zensical) > 50


def test_markers_do_not_change_the_real_book(real_site):
    """Kirjan jokainen sivu (hidas, mutta paloittelija jäljittelee
    Python-Markdownia vain osin, ja kirjan lähteissä on sen rajatapauksia)."""
    assert check_pages(real_site.parent) > 0


def test_the_built_page_links_only_the_clips_that_exist(book):
    """Käännetyllä sivulla on merkki jokaisella lohkolla, jonka leike on
    varastossa, ja leikkeet ovat sivustolla; muilla sivuilla ei merkkejä."""
    html = (book.site / "osa1" / "puhe" / "index.html").read_text(encoding="utf-8")
    clips = set(re.findall(r'data-puhe="?([0-9a-f]{16})', html))
    assert convert.speech_clip(MISSING_SPEECH) not in clips
    assert convert.speech_clip("Viimeinen kappale.") in clips
    assert '<script type="application/json" id="jyu-puhe">' in html
    folder = book.site / "assets" / "puhe"
    listed = set((folder / convert.SPEECH_INDEX).read_text(encoding="utf-8").split())
    assert clips <= listed
    assert all((folder / f"{clip}.mp3").is_file() for clip in listed)
    assert "data-puhe" not in (book.site / "osa1" / "01-hei" / "index.html").read_text(
        encoding="utf-8")


def test_the_built_walkthrough_plays_clips_from_the_store(book):
    """Vaiheittaisen ohjeen vaihe soittaa varaston leikettä sivuston
    assets/puhe/:sta, ja leike on luettelossa; vaihe, jonka leike puuttuu
    (MISSING_STEP), on äänetön."""
    page = book.site / "osa1" / "vaiheet"
    html = (page / "index.html").read_text(encoding="utf-8")
    # Renderöinti järjestää attribuutit, joten ne luetaan järjestyksestä riippumatta.
    sections = [dict(re.findall(r'(data-\w+)="([^"]*)"', attributes))
                for attributes in re.findall(r'<section class="jyu-step"([^>]*)>', html)]
    audio = {section["data-scene"]: section["data-audio"]
             for section in sections if "data-audio" in section}
    source = (book.src / "osa1" / "vaiheet.md").read_text(encoding="utf-8")
    steps = convert.walkthrough_speech(source)[1]
    assert steps["komento"] == MISSING_STEP
    assert audio == {scene: f"../../assets/puhe/{clip}.mp3"
                     for scene, clip in zip(steps, clips(list(steps.values())))
                     if scene != "komento"}
    listed = (book.site / "assets" / "puhe" / convert.SPEECH_INDEX).read_text(encoding="utf-8")
    for url in audio.values():
        assert (page / url).resolve().is_file()
        assert url.removeprefix("../../assets/puhe/").removesuffix(".mp3") in listed.split()


# --- Soitin selaimessa ----------------------------------------------------------

# Selaimen ääni korvataan: play kirjaa leikkeen ja pitää elementin soivana,
# kunnes testi kutsuu __advance (ääni loppui). Lataus on oikea, joten
# puuttuvan leikkeen error-tapahtuma tulee palvelimen 404:stä.
FAKE_AUDIO = """
window.__played = [];
Object.defineProperty(HTMLMediaElement.prototype, "paused", {
  configurable: true, get() { return !this.__playing; } });
HTMLMediaElement.prototype.play = function () {
  this.__playing = true;
  window.__current = this;
  window.__played.push(this.src.split("/").pop().replace(".mp3", ""));
  return Promise.resolve();
};
HTMLMediaElement.prototype.pause = function () { this.__playing = false; };
window.__advance = () => {
  const audio = window.__current;
  audio.__playing = false;
  audio.dispatchEvent(new Event("ended"));
};
"""

# Koesivun lohkot näkyvässä järjestyksessä Windows valittuna: macOS-välilehti
# ja suljetun <details>-kohdan sisältö ohitetaan, ja lohko, jonka leike puuttui
# käännöksessä (MISSING_SPEECH), on merkitsemätön.
BEFORE_TABS = [
    "Ääneenluku.",
    "Koko sivun ääneenluvun koesivu (tests/test puhe.py). Ei SUMMARY.md:ssä, "
    "jotta muiden testien laskemat luvut ja lohkot eivät muutu.",
    "Luettelon ensimmäinen kohta.",
    "Toinen kohta, jossa on linkki.",
    "Huomautus.",
    "Laatikon teksti.",
    "Oma tunnus.",
    "2 välilehteä otsikoilla Windows ja macOS.",
]
AFTER_TABS = [
    "Koodilohko, jota ei lueta ääneen.",
    "Avattava kohta: Lisätietoa.",
    "Taulukko, jota ei lueta ääneen.",
    "Viimeinen kappale.",
]


def clips(texts: list[str]) -> list[str]:
    return [convert.speech_clip(text, convert.SPEECH_DEFAULT_VOICE) for text in texts]


@pytest.fixture
def player(browser, book, serve):
    """player(polku) -> (sivu, virheet). Oma konteksti, jotta välilehden
    valinta ei jää muistiin. Puuttuvan leikkeen 404 ei ole virhe."""
    base = serve(book.site)
    contexts = []

    def open_page(path="osa1/puhe/"):
        context = browser.new_context(viewport={"width": 1280, "height": 900},
                                      reduced_motion="reduce")
        contexts.append(context)
        context.add_init_script(FAKE_AUDIO)
        page = context.new_page()
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("console", lambda message: message.type == "error"
                and "404" not in message.text and errors.append(message.text))
        page.goto(f"{base}/{path}", wait_until="load")
        return page, errors

    yield open_page
    for context in contexts:
        context.close()


def play_all(page) -> list[str]:
    """Soita loppuun: jokainen leike loppuu vuorollaan. -> soitetut leikkeet."""
    for _ in range(40):
        if page.locator(".jyu-puhe-status").text_content() == "Sivu luettu":
            break
        count = page.evaluate("window.__played.length")
        page.evaluate("window.__advance()")
        page.wait_for_function(f"window.__played.length > {count}"
                               " || document.querySelector('.jyu-puhe-status').textContent")
    return page.evaluate("window.__played")


def test_the_speaker_is_shown_only_on_a_page_with_speech(player):
    page, errors = player("osa1/01-hei/")
    assert page.locator(".jyu-puhe-button").is_hidden()
    page, errors = player()
    assert page.locator(".jyu-puhe-button").is_visible()
    assert page.locator(".jyu-puhe-bar").is_hidden()
    assert errors == []


def test_the_page_is_read_in_order_with_the_selected_tab_only(player):
    """Välilehtijoukosta ilmoitus ja valitun välilehden ilmoitus, sitten vain
    sen sisältö; suljetun <details>-kohdan sisältö ohitetaan; lopuksi palkki
    kertoo sivun luetuksi eikä korostusta jää."""
    page, errors = player()
    page.locator(".jyu-puhe-button").click()
    assert page.locator(".jyu-puhe-bar").is_visible()
    assert page.locator(".jyu-puhe-button").get_attribute("aria-pressed") == "true"
    played = play_all(page)
    assert played == clips(BEFORE_TABS + ["Luetaan välilehti Windows, mutta ei muita.",
                                          "Windowsin ohje."] + AFTER_TABS)
    assert page.locator(".jyu-puhe-status").text_content() == "Sivu luettu"
    assert page.locator(".jyu-puhe-nyt").count() == 0
    assert errors == []


def test_the_reader_hears_the_tab_they_have_chosen(player):
    page, _ = player()
    page.get_by_text("macOS", exact=True).first.click()
    page.locator(".jyu-puhe-button").click()
    played = play_all(page)
    assert played == clips(BEFORE_TABS + ["Luetaan välilehti macOS, mutta ei muita.",
                                          "macOSin ohje."] + AFTER_TABS)


def test_the_block_being_read_is_highlighted_and_can_be_changed(player):
    """Korostus seuraa lohkoa; seuraava ja edellinen vaihtavat lohkoa, ja
    lohkon klikkaus lukee siitä, linkin klikkaus ei."""
    page, errors = player()
    page.locator(".jyu-puhe-button").click()
    assert page.locator(".jyu-puhe-nyt").text_content().startswith("Ääneenluku")
    page.locator(".jyu-puhe-next").click()
    assert page.locator(".jyu-puhe-nyt").text_content().startswith("Koko sivun")
    page.locator(".jyu-puhe-prev").click()
    assert page.locator(".jyu-puhe-nyt").text_content().startswith("Ääneenluku")
    page.get_by_text("Viimeinen kappale.").click()
    assert page.evaluate("window.__played.at(-1)") == clips(["Viimeinen kappale."])[0]
    played = page.evaluate("window.__played.length")
    page.route("https://example.invalid/**", lambda route: route.abort())
    page.locator("article a[href^='https://example.invalid']").click(modifiers=["Control"])
    assert page.evaluate("window.__played.length") == played
    assert errors == []


def test_a_clip_that_does_not_load_is_skipped(player):
    """Käännöksen jälkeen kadonnut leike: seuraava soi ilman odottelua."""
    page, _ = player()
    table, last = clips(["Taulukko, jota ei lueta ääneen.", "Viimeinen kappale."])
    page.route(f"**/{table}.mp3", lambda route: route.abort())
    page.locator(".jyu-puhe-button").click()
    page.locator("article table").click()
    page.wait_for_function(f"window.__played.at(-1) === '{last}'")
    assert page.evaluate("window.__played.slice(-2)") == [table, last]


def test_closing_stops_the_reading(player):
    page, _ = player()
    page.locator(".jyu-puhe-button").click()
    page.locator(".jyu-puhe-close").click()
    assert page.locator(".jyu-puhe-bar").is_hidden()
    assert page.locator(".jyu-puhe-nyt").count() == 0
    assert page.locator(".jyu-puhe-button").get_attribute("aria-pressed") == "false"
    assert page.evaluate("document.querySelector('.jyu-puhe-button') && "
                         "[...document.querySelectorAll('audio')].every(a => a.paused)")
    page.locator(".jyu-puhe-button").click()
    page.locator(".jyu-puhe-button").click()
    assert page.locator(".jyu-puhe-bar").is_hidden()


def test_the_speaker_tooltip_closes_after_a_click(player):
    """Teeman vihje on auki myös kohdistuksen ajan: hiiren painallus ei jätä
    sitä auki, eikä nimi vaihdu (tila on aria-pressedissä)."""
    page, _ = player()
    button = page.locator(".jyu-puhe-button")
    button.hover()
    page.wait_for_selector(".md-tooltip2--active")
    button.click()
    page.mouse.move(600, 500)
    page.wait_for_selector(".md-tooltip2--active", state="detached")
    # Vihje palauttaa title-attribuutin vasta poistuessaan.
    page.wait_for_selector(".jyu-puhe-button[title]")
    assert button.get_attribute("aria-pressed") == "true"
    assert button.get_attribute("title") == "Kuuntele sivu"
    assert button.get_attribute("aria-label") == "Kuuntele sivu"
    button.focus()
    page.keyboard.press("Enter")
    assert button.get_attribute("aria-pressed") == "false"
    assert page.evaluate("document.activeElement.classList.contains('jyu-puhe-button')")


def test_the_speed_cycles_applies_to_the_next_clip_and_is_remembered(player):
    page, errors = player()
    speed = page.locator(".jyu-puhe-speed")
    page.locator(".jyu-puhe-button").click()
    assert speed.text_content() == "1×"
    shown = []
    for _ in range(6):
        speed.click()
        shown.append(speed.text_content())
    assert shown == ["1,1×", "1,25×", "1,5×", "1,75×", "2×", "1×"]
    speed.click()
    speed.click()
    assert speed.get_attribute("aria-label") == "Lukunopeus 1,25×"
    page.locator(".jyu-puhe-next").click()
    assert page.evaluate("window.__current.playbackRate") == 1.25
    page.reload()
    page.locator(".jyu-puhe-button").click()
    assert speed.text_content() == "1,25×"
    assert page.evaluate("window.__current.playbackRate") == 1.25
    assert errors == []
