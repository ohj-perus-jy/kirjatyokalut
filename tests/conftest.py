"""Testien yhteiset palikat: käännetty sivusto, palvelin ja selain.

Sivusto käännetään oikeasti (convert.py + zensical build): tulostussivu
kootaan valmiista HTML:stä, joten testattava syntyy vasta käännöksessä.
"""

import functools
import http.server
import importlib.metadata
import shutil
import subprocess
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TOOL))

import convert  # noqa: E402  (polku asetettu yllä)

# Oikea kirja, jonka submodulena työkalut ovat (kirja.toml sen hakemistossa),
# tai None, kun työkalurepoa testataan yksinään: silloin vain koekirja.
BOOK = convert.BOOK if (convert.BOOK / convert.CONFIG_NAME).is_file() else None

# zensical-komento on samassa hakemistossa kuin testejä ajava python (.venv/bin).
ZENSICAL = Path(sys.executable).parent / "zensical"


def pytest_addoption(parser):
    parser.addoption(
        "--nobuild", action="store_true",
        help="älä käännä oikeaa kirjaa uudelleen, käytä olemassa olevaa site/:ä")


def build(book_dir: Path, tool: Path) -> Path:
    """convert.py + zensical build kirjan hakemistossa. -> site/."""
    for command in ([sys.executable, str(tool / "convert.py")], [str(ZENSICAL), "build"]):
        result = subprocess.run(command, cwd=book_dir, capture_output=True,
                                text=True)
        if result.returncode:
            raise AssertionError(
                f"{' '.join(command)} epäonnistui:\n{result.stdout}\n{result.stderr}")
    site = book_dir / "site"
    (site / VERSION_FILE).write_text(zensical_version(), encoding="utf-8")
    return site


# Kaikki, mistä käännetty sivusto riippuu: myös työkalujen omat palaset
# vanhentavat sivuston muuttuessaan. Polut kirjan ja työkalujen hakemistosta.
BOOK_SOURCES = ("../src", "mkdocs.yml", "kirja.toml")
TOOL_SOURCES = ("assets", "overrides", "icons", "convert.py", "mkdocs-pohja.yml")

# Suuri osa HTML:stä tulee Zensicalilta, joten myös sen versio vanhentaa
# sivuston. Versio ei näy lähdetiedostojen aikaleimoissa, joten käännös
# jättää siitä merkin sivustoon.
VERSION_FILE = ".zensical-versio"


def zensical_version() -> str:
    """Testejä ajavaan ympäristöön asennetun Zensicalin versio."""
    return importlib.metadata.version("zensical")


def is_stale(site: Path) -> bool:
    """Onko käännetty sivusto jäljessä lähteistään tai Zensicalin versiosta?
    Käännös on hidas eikä sitä tehdä turhaan, mutta vanhalla sivustolla ei
    saa testata."""
    index = site / "index.html"
    if not index.is_file():
        return True
    stamp = site / VERSION_FILE
    if (not stamp.is_file()
            or stamp.read_text(encoding="utf-8").strip() != zensical_version()):
        return True
    built = index.stat().st_mtime
    sources = ([BOOK / name for name in BOOK_SOURCES]
               + [TOOL / name for name in TOOL_SOURCES])
    for source in sources:
        paths = source.rglob("*") if source.is_dir() else [source]
        if any(path.stat().st_mtime > built for path in paths if path.is_file()):
            return True
    return False


@pytest.fixture(scope="session")
def real_site(request) -> Path:
    """Oikea kirja (../src) käännettynä. Käännetään vain jos site/ on jäljessä."""
    if BOOK is None:
        pytest.skip("ei kirjaa: työkalut eivät ole kirjan submodulena")
    site = BOOK / "site"
    if request.config.getoption("--nobuild"):
        if not (site / "index.html").is_file():
            pytest.skip("site/ puuttuu eikä --nobuild anna kääntää sitä")
        return site
    return build(BOOK, TOOL) if is_stale(site) else site


# Työkalujen palat, jotka käännös tarvitsee.
TOOL_FILES = ("convert.py", "mkdocs-pohja.yml")
TOOL_DIRS = ("assets", "overrides", "icons")


def copy_book(target: Path) -> Path:
    """Koekirja + työkalut omaan hakemistoonsa. -> zensical-hakemisto.

    Sama rakenne kuin kirjan repossa: src/ ja zensical/ sisaruksina, työkalut
    submodulen paikalla zensical/tyokalut/:ssa. Työkalut kopioidaan, koska
    testit muuttavat niitäkin (test_change.py).
    """
    shutil.copytree(TOOL / "tests" / "book" / "src", target / "src")
    zensical = target / "zensical"
    shutil.copytree(TOOL / "tests" / "book" / "zensical", zensical)
    tool = zensical / "tyokalut"
    tool.mkdir()
    for name in TOOL_FILES:
        shutil.copy(TOOL / name, tool / name)
    for name in TOOL_DIRS:
        shutil.copytree(TOOL / name, tool / name)
    return zensical


@dataclass
class Book:
    """Käännetty koekirja, jonka materiaalia testi saa muuttaa."""

    src: Path
    zensical: Path
    site: Path

    def rebuild(self) -> None:
        self.site = build(self.zensical, self.zensical / "tyokalut")


@pytest.fixture(scope="session")
def book(tmp_path_factory) -> Book:
    """Koekirja käännettynä kerran. Vain luettavaksi."""
    zensical = copy_book(tmp_path_factory.mktemp("book"))
    return Book(zensical.parent / "src", zensical, build(zensical, zensical / "tyokalut"))


@pytest.fixture
def mutable_book(tmp_path_factory) -> Book:
    """Oma koekirja testille, joka muuttaa materiaalia."""
    zensical = copy_book(tmp_path_factory.mktemp("book"))
    return Book(zensical.parent / "src", zensical, build(zensical, zensical / "tyokalut"))


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@pytest.fixture(scope="session")
def serve():
    """serve(site) -> osoite. Tulostussivu hakee luvut fetchillä, joten
    file:// ei kelpaa. Säikeistetty palvelin, koska haut lähtevät rinnakkain."""
    servers = []

    def start(site: Path) -> str:
        handler = functools.partial(QuietHandler, directory=str(site))
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        servers.append(server)
        return f"http://127.0.0.1:{server.server_address[1]}"

    yield start
    for server in servers:
        server.shutdown()
        server.server_close()


@pytest.fixture(scope="session")
def browser():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        instance = playwright.chromium.launch()
        yield instance
        instance.close()


@dataclass
class PrintPage:
    """Avattu /tulosta/, jolta selain on koonnut kirjan ja pyytänyt tulostusta."""

    page: object
    print_calls: list[str] = field(default_factory=list)
    drawn_lines: list[int] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def evaluate(self, script):
        return self.page.evaluate(script)


def open_print_page(browser, base_url: str, timeout: int = 120_000) -> PrintPage:
    """Avaa /tulosta/ ja odota, että sivu on koottu ja tulostusta pyydetty.

    window.print korvataan laskurilla: headless-selaimessa tulostusikkunaa ei
    ole. Kutsun hetkellä talletetaan tilarivi ja piirrettyjen terminaalirivien
    määrä, koska juuri se tila päätyy paperille.
    """
    page = browser.new_page()
    result = PrintPage(page)
    page.on("pageerror", lambda error: result.errors.append(str(error)))
    # Resurssin 404 tulee konsoliin ilman osoitetta, joten se otetaan mukaan
    # location-kentästä: muuten tunnettua puuttuvaa kuvaa ei voisi erottaa.
    page.on("console", lambda message: message.type == "error"
            and result.errors.append(
                f"{message.text} {message.location['url']}".strip()))
    page.add_init_script(
        "window.__printCalls = [];"
        "window.__drawnLines = [];"
        "window.print = () => {"
        "  window.__printCalls.push("
        "    document.getElementById('jyu-print-status').textContent.trim());"
        "  window.__drawnLines.push(document.querySelectorAll('.ap-line').length);"
        "};")
    page.goto(f"{base_url}/tulosta/", wait_until="load")
    page.wait_for_function("window.__printCalls.length > 0", timeout=timeout)
    result.print_calls = page.evaluate("window.__printCalls")
    result.drawn_lines = page.evaluate("window.__drawnLines")
    return result
