"""Kopiointinappi ja hiirellä maalaaminen komentorivilohkossa koekirjalla
(copy.js, copy.css).

console-lohkosta kopioidaan vain komennot: kehote ja tulosterivit jäävät
pois, joten leikepöydälle tulee vain se, minkä voi liittää terminaaliin.
Hiirellä maalattuun tekstiin ei tule kehotetta. Koekirjan osan 2
etusivulla on lohko kutakin tapausta varten.
"""

import pytest
from playwright.sync_api import Error

BLOCK = "div.highlight"
COPY = "[data-md-type=copy]"

# Koekirjan osan 2 etusivun lohkot, joita testit käyttävät nimellä.
ALPINE = 6
SELECT = 7

# Maalaaminen on selaimen omaa toimintaa, ja selaimet eroavat siinä.
ENGINES = ("chromium", "firefox", "webkit")


@pytest.fixture(scope="session")
def chapter_url(book, serve) -> str:
    return f"{serve(book.site)}/osa2/"


@pytest.fixture
def page(browser, chapter_url):
    opened = browser.new_page()
    opened.context.grant_permissions(["clipboard-read", "clipboard-write"])
    opened.goto(chapter_url, wait_until="load")
    yield opened
    opened.close()


def copy(page, nth: int) -> str:
    """Kopioi lohkon ja lukee leikepöydän, kun kuittaus kertoo kopioinnin
    valmistuneen (copy.js kirjoittaa leikepöydälle asynkronisesti)."""
    block = page.locator(BLOCK).nth(nth)
    block.locator(COPY).click()
    block.locator(".jyu-copied--shown").wait_for()
    return page.evaluate("navigator.clipboard.readText()")


def test_only_commands_are_copied(page):
    """Kehotteet ja tulosterivit jäävät pois, BuildKitin #-rivit myös.
    Jatkorivi ja heredoc kuuluvat komentoon, ja kommentit säilyvät."""
    assert copy(page, 0) == (
        "docker run --rm \\\n"
        "    hello-world\n"
        "docker build -t kaiku .\n"
        "ls  # kommentti jää\n"
        "python3 - <<'EOF'\n"
        "# Pythonin kommentti jää\n"
        'print("hei")\n'
        "EOF")


def test_prompt_ends_where_it_ends(page):
    """Pygments venyttää kehotteen rivin seuraavaan $- tai %-merkkiin;
    kopioon tulee koko komento. Pelkkä kehote ilman komentoa jää pois."""
    assert copy(page, 1) == "kill %1\necho $?"


def test_hash_is_a_root_prompt_only_alone(page):
    """Pelkkä # on rootin kehote lohkossa, jossa ei ole muita kehotteita;
    $-lohkossa se on tulosteen kommenttirivi."""
    assert copy(page, 2) == "apt-get install -y curl"
    assert copy(page, 3) == "cat Dockerfile"


def test_other_blocks_are_copied_as_is(page):
    """Lohko ilman kehotetta on pelkkää tulostetta, eikä sen kopio saa olla
    tyhjä. Muissa kielissä kommentit ja #-rivit säilyvät."""
    assert copy(page, 4) == "Hello from Docker!"
    assert copy(page, 5) == '# kommentti\nprint("hei")  # rivin lopussa'


def test_prompts_and_output_stay_on_the_page(page):
    """Kopiointi ei muuta sivulla näkyvää lohkoa."""
    copy(page, 0)
    shown = page.locator(BLOCK).nth(0).locator("code").inner_text()
    assert shown.startswith("$ docker run --rm \\")
    assert "Hello from Docker!" in shown


def test_alpine_prompt_is_a_prompt(page):
    """Alpinen komentotulkin kehote on hakemisto ja #: "/ # ", "/app # "."""
    assert copy(page, ALPINE) == "ps\nexit"


def marked(page, nth: int) -> str:
    """Lohkon teksti, jossa kehotteeksi merkityt merkit ovat «»:n sisällä."""
    return page.locator(BLOCK).nth(nth).locator("code").evaluate("""code => {
      let out = "", inside = false;
      const walker = document.createTreeWalker(code, NodeFilter.SHOW_TEXT);
      for (let node; (node = walker.nextNode());) {
        const prompt = Boolean(node.parentElement.closest(".jyu-prompt"));
        if (prompt !== inside) out += prompt ? "«" : "»";
        inside = prompt;
        out += node.data;
      }
      return inside ? out + "»" : out;
    }""")


def test_prompts_are_marked_where_the_button_finds_them(page):
    """Maalauksesta jäävät pois (.jyu-prompt) täsmälleen ne kehotteet, jotka
    kopiointinappikin jättää pois: eivät BuildKitin #-rivit, heredocin
    kommentit, $- ja %-merkit komennon keskellä eivätkä tulosterivit."""
    assert marked(page, 0) == (
        "«$ »docker run --rm \\\n"
        "    hello-world\n"
        "Hello from Docker!\n"
        "«$ »docker build -t kaiku .\n"
        "#5 [1/2] FROM docker.io/library/python:3.13-slim\n"
        "#5 DONE 0.1s\n"
        "«$ »ls  # kommentti jää\n"
        "«$ »python3 - <<'EOF'\n"
        "# Pythonin kommentti jää\n"
        'print("hei")\n'
        "EOF\n"
        "hei\n")
    assert marked(page, 1) == (
        "«root@kontti:/app# »kill %1\n"
        "[1]+  Terminated              python kaiku.py\n"
        "«root@kontti:/app# »echo $?\n"
        "0\n"
        "«root@kontti:/app#»\n")
    assert marked(page, 2) == "«# »apt-get install -y curl\n"
    assert marked(page, 3) == (
        "«$ »cat Dockerfile\n# syntax=docker/dockerfile:1\nFROM python:3.13-slim\n")
    assert marked(page, 4) == "Hello from Docker!\n"
    assert "«" not in marked(page, 5)
    assert marked(page, ALPINE) == (
        "«/ # »ps\n"
        "PID   USER     TIME  COMMAND\n"
        "    1 root      0:00 sh\n"
        "«/app # »exit\n")


def test_marking_keeps_the_colours(page):
    """Kääre on Pygmentsin elementin sisällä, joten kehote on yhä kehotteen
    värinen (.gp) eikä komennon."""
    colours = page.locator(BLOCK).nth(SELECT).locator(".jyu-prompt").evaluate_all(
        """prompts => prompts.map(prompt => [
          getComputedStyle(prompt).color,
          getComputedStyle(prompt.closest('.gp')).color])""")
    assert len(colours) == 2
    assert all(own == prompt for own, prompt in colours)


@pytest.fixture(scope="module", params=ENGINES)
def engine(request, playwright_api):
    """Kukin selain vuorollaan. Pelkällä user-selectillä Chromium ja Firefox
    eivät aloittaneet maalausta lainkaan kehotteen päältä, eli rivin alusta,
    ja Firefoxissa taaksepäin maalattu rivi menetti ensimmäisen sanansa.
    run.sh test asentaa vain Chromiumin; muut ohitetaan, ellei niitä ole
    asennettu (.venv/bin/playwright install --with-deps firefox webkit)."""
    try:
        instance = getattr(playwright_api, request.param).launch()
    except Error as error:
        pytest.skip(f"{request.param} ei käynnisty: {str(error).splitlines()[0]}")
    yield instance
    instance.close()


@pytest.fixture
def selecting(engine, chapter_url):
    """Sivu maalauskokeille. Leikepöytä luetaan liittämällä se tekstikenttään,
    koska Firefox ja WebKit eivät anna lukea sitä navigator.clipboardilla."""
    opened = engine.new_page(viewport={"width": 1200, "height": 900})
    opened.goto(chapter_url, wait_until="load")
    opened.evaluate("""() => {
      const area = document.createElement('textarea');
      area.id = 'liitos';
      document.body.prepend(area);
    }""")
    yield opened
    opened.close()


def clear_clipboard(page) -> None:
    """Leikepöydälle tunniste, ettei edellinen kopio näy tuloksena, ja
    lohko keskelle ruutua, pois yläpalkin alta. Tekstikenttä ei saa jäädä
    kohdistetuksi: Chromium vierittää sivun alkuun, kun kohdistus lähtee
    kentästä, jossa on ollut valinta. Vieritys heti eikä teeman pehmeänä
    vierityksenä, jottei lohko liiku kohtien mittaamisen jälkeen."""
    area = page.locator("#liitos")
    area.fill("TYHJÄ")
    area.select_text()
    page.keyboard.press("ControlOrMeta+c")
    area.fill("")
    area.blur()
    page.evaluate("getSelection().removeAllRanges()")
    page.locator(BLOCK).nth(SELECT).evaluate(
        "block => block.scrollIntoView({block: 'center', behavior: 'instant'})")


def pasted(page) -> str:
    """Kopioi maalatun tekstin ja palauttaa sen tekstikenttään liitettynä."""
    page.keyboard.press("ControlOrMeta+c")
    area = page.locator("#liitos")
    area.focus()
    page.keyboard.press("ControlOrMeta+v")
    return area.input_value()


def drag(page, start, end) -> None:
    page.mouse.move(*start)
    page.mouse.down()
    page.mouse.move(*end, steps=8)
    page.mouse.up()


def prompt_start(page, line: int) -> tuple[float, float]:
    """Rivin kehotteen ensimmäisen merkin kohta: rivin alku."""
    box = page.locator(BLOCK).nth(SELECT).locator(".jyu-prompt").nth(line).bounding_box()
    return box["x"] + 1, box["y"] + box["height"] / 2


def line_end(page, line: int) -> tuple[float, float]:
    """Kohta vähän rivin tekstin lopun oikealla puolella. Rivin elementti on
    lohkon levyinen, ja ensimmäisen rivin oikeassa päässä ovat lohkon napit,
    joten tekstin loppu mitataan tekstin omista suorakulmioista."""
    right = page.locator(BLOCK).nth(SELECT).locator("code > span").nth(line).evaluate(
        """line => {
          const range = document.createRange();
          range.selectNodeContents(line);
          return Math.max(...[...range.getClientRects()].map(rect => rect.right));
        }""")
    return right + 20, prompt_start(page, line)[1]


def test_line_selected_from_its_start(selecting):
    """Rivin alusta loppuun maalattuna vain komento."""
    clear_clipboard(selecting)
    drag(selecting, prompt_start(selecting, 0), line_end(selecting, 0))
    assert pasted(selecting) == "docker run hello-world"


def test_lines_selected_from_the_start(selecting):
    """Kahden rivin maalaus: kummaltakin riviltä vain komento."""
    clear_clipboard(selecting)
    drag(selecting, prompt_start(selecting, 0), line_end(selecting, 1))
    assert pasted(selecting) == "docker run hello-world\nuname -r"


def test_line_selected_backwards(selecting):
    """Rivin lopusta alkuun: komento kokonaan, ensimmäinen sanakin."""
    clear_clipboard(selecting)
    drag(selecting, line_end(selecting, 0), prompt_start(selecting, 0))
    assert pasted(selecting) == "docker run hello-world"


def test_selection_ending_in_a_prompt(selecting):
    """Maalaus, joka päättyy seuraavan rivin kehotteeseen, päättyy riviin."""
    clear_clipboard(selecting)
    x, y = prompt_start(selecting, 1)
    drag(selecting, prompt_start(selecting, 0), (x + 30, y))
    assert pasted(selecting) == "docker run hello-world\n"


def test_line_selected_by_triple_click(selecting):
    """Kolmoisklikkaus valitsee rivin ilman kehotetta. Rivinvaihto tulee
    mukaan selaimesta riippuen."""
    clear_clipboard(selecting)
    x, y = prompt_start(selecting, 0)
    selecting.mouse.click(x + 100, y, click_count=3)
    assert pasted(selecting).rstrip("\n") == "docker run hello-world"


def test_block_selected_with_the_text_around_it(selecting):
    """Kappaleesta kappaleeseen maalattuna lohkosta tulevat komennot."""
    clear_clipboard(selecting)
    before = selecting.locator("p", has_text="Hiirellä maalattuun").bounding_box()
    after = selecting.locator("p", has_text="Kappale lohkon jälkeen").bounding_box()
    drag(selecting, (before["x"] + 5, before["y"] + before["height"] / 2),
         (after["x"] + 60, after["y"] + after["height"] / 2))
    text = pasted(selecting)
    assert "docker run hello-world\nuname -r\n" in text
    assert "$" not in text and "root@" not in text
