"""Kopiointinappi komentorivilohkossa koekirjalla (copy.js).

console-lohkosta kopioidaan vain komennot: kehote ja tulosterivit jäävät
pois, joten leikepöydälle tulee vain se, minkä voi liittää terminaaliin.
Koekirjan osan 2 etusivulla on lohko kutakin tapausta varten.
"""

import pytest

BLOCK = "div.highlight"
COPY = "[data-md-type=copy]"


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
