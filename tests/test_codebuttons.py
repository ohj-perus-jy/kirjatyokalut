"""Koodilohkon nappirivi pitkän ensimmäisen rivin päällä koekirjalla
(codebuttons.css).

Nappien alle tulee lohkon värinen pinta, joten rivin loppu on luettavissa
vain, jos sen saa vieritettyä nappien vasemmalle puolelle. Kapealla ruudulla
ohj1:n muokattavan C#-lohkon (neljä nappia) ensimmäinen näkyvä rivi on
lohkoa pidempi.
"""

import pytest

EDITABLE = "div.highlight.language-csharp.editable"
MARKED = "div.highlight[data-hl-green]"
COPY = "[data-md-type=copy]"

# Ensimmäisen näkyvän rivin viimeisen merkin oikea reuna ja nappirivin vasen
# reuna ruudulla.
LINE_END_AND_ROW = """block => {
  const code = block.querySelector("pre > code");
  const line = code.querySelector(":scope > :nth-child(1 of :not(.boring))");
  const range = document.createRange();
  range.selectNodeContents(line);
  const ends = [...range.getClientRects()].filter(r => r.width).map(r => r.right);
  const row = block.querySelector("nav.md-code__nav").getBoundingClientRect();
  return [Math.max(...ends), row.left];
}"""


@pytest.fixture(scope="session")
def base_url(book, serve) -> str:
    return serve(book.site)


@pytest.fixture
def narrow(browser):
    context = browser.new_context(viewport={"width": 390, "height": 800})
    opened = context.new_page()
    yield opened
    context.close()


def test_the_end_of_a_long_first_line_scrolls_clear_of_the_buttons(
        narrow, base_url):
    """Koodin perään on varattu nappirivin levyinen tila. Vierittämättä rivi
    ulottuu nappien alle; muuten testi ei mittaisi mitään."""
    narrow.goto(f"{base_url}/osa1/csharp/", wait_until="load")
    end, row = narrow.eval_on_selector(EDITABLE, LINE_END_AND_ROW)
    assert end > row
    narrow.eval_on_selector(
        f"{EDITABLE} pre > code", "code => code.scrollLeft = code.scrollWidth")
    end, row = narrow.eval_on_selector(EDITABLE, LINE_END_AND_ROW)
    assert end <= row


def test_the_surface_under_the_buttons_takes_a_marked_lines_colour(
        browser, base_url):
    """Korostettu nauha ei katkea nappien kohdalla. Koekirjan lohkossa rivi 1
    on piilossa, joten ensimmäinen näkyvä on korostettu rivi 2."""
    opened = browser.new_page()
    opened.goto(f"{base_url}/osa1/01-hei/", wait_until="load")
    surface, band = opened.eval_on_selector(MARKED, """block => {
      const probe = document.createElement("div");
      probe.style.backgroundColor = getComputedStyle(block.querySelector("pre"))
        .getPropertyValue("--jyu-code-panel-color");
      document.body.append(probe);
      const line = block.querySelector("code > .hl-green:not(.boring)");
      return [getComputedStyle(probe).backgroundColor,
              getComputedStyle(line).backgroundColor];
    }""")
    opened.close()
    assert surface == band


def test_the_copy_note_does_not_widen_the_button_row(browser, base_url):
    """Kuittaus on rivin ulkopuolella: piilotettunakin se levittäisi riviä ja
    sen alle piirrettyä pintaa pysyvästi."""
    context = browser.new_context()
    context.grant_permissions(["clipboard-read", "clipboard-write"])
    opened = context.new_page()
    opened.goto(f"{base_url}/osa1/01-hei/", wait_until="load")
    row = opened.locator(f"{MARKED} nav.md-code__nav")
    before = row.bounding_box()["width"]
    opened.click(f"{MARKED} {COPY}")
    note = row.locator(".jyu-copied--shown")
    note.wait_for()
    assert row.bounding_box()["width"] == before
    box = note.bounding_box()
    assert box["x"] + box["width"] <= row.bounding_box()["x"]
    context.close()
