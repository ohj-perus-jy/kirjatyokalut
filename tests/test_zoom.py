"""Kuvasuurennus koekirjalla (kirja.toml: kuvasuurennus, convert.py: IMAGE_ZOOM_CSS).

GLightbox on työkalujen oma (assets/), joten kuva avautuu suurena, vaikka
selain ei pääse unpkg.comiin, eikä sivu edes yritä hakea sieltä mitään.
Vaiheittaisen ohjeen kuvat ks. test_walkthrough.py.
"""

LIGHTBOX = ".glightbox-container .gslide.current img"


def test_the_image_opens_large_without_unpkg(browser, book, serve):
    """Kuvan klikkaus avaa sen suurena teeman tyylein, ja kirjasto ja tyyli
    tulevat sivustolta. Pyyntöjä unpkg.comiin ei synny."""
    base_url = serve(book.site)
    context = browser.new_context()
    requested: list[str] = []
    context.on("request", lambda request: requested.append(request.url))
    context.route("https://unpkg.com/**", lambda route: route.abort())
    page = context.new_page()
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("console", lambda message: message.type == "error"
            and errors.append(f"{message.text} {message.location['url']}".strip()))
    page.goto(f"{base_url}/osa1/01-hei/", wait_until="load")
    page.click(".md-content a.glightbox")
    page.wait_for_selector(LIGHTBOX)
    assert page.evaluate(
        "getComputedStyle(document.querySelector('.glightbox-container')).position") == "fixed"
    assert {f"{base_url}/assets/js/glightbox.min.js",
            f"{base_url}/assets/css/glightbox.min.css"} <= set(requested)
    assert [url for url in requested if "unpkg.com" in url] == []
    assert errors == []
    context.close()
