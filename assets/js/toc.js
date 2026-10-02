/* Sisällysluettelon sulkeminen kapealla näytöllä. Alle 960 px:n leveydellä
 * Zensical piirtää sisällysluettelon alakulman napista avautuvaksi laatikoksi,
 * ja avaus on pelkkää CSS:ää: nappi on <label>, joka rastittaa piilotetun
 * #__toc-valintaruudun, ja laatikko näkyy ruudun ollessa rastittuna. Kohdan
 * napautus vie otsikkoon, mutta mikään ei poista rastia, joten laatikko jää
 * peittämään juuri avattua tekstiä; myöskään laatikon ulkopuolen napautus ei
 * sulje sitä. Tässä rasti poistetaan molemmissa. Työpöydällä ruutua ei ole
 * rastittu, joten tämä ei tee mitään. */

(() => {
  const toggle = document.getElementById("__toc")
  const sidebar = document.querySelector(".md-sidebar--secondary")
  if (!toggle || !sidebar)
    return

  /* Yksi kuuntelija koko sivulle. Sivupalkin sisällä (nappi, laatikko)
   * suljetaan vain linkin napautuksesta, jotta vierityspalkin tai listan
   * reunan kosketus ei sulje; napin ja laatikon otsikon <label>it vaihtavat
   * rastin itse. Kaikki muu sivulla on ulkopuolta. */
  document.addEventListener("click", event => {
    if (!toggle.checked)
      return
    const inside = sidebar.contains(event.target)
    if (!inside || event.target.closest("a.md-nav__link"))
      toggle.checked = false
  })
})()
