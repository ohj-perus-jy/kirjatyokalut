/* Sisällysluettelon sulkeminen kapealla näytöllä. Alle 960 px:n leveydellä
 * Zensical piirtää sisällysluettelon alakulman napista avautuvaksi laatikoksi,
 * ja avaus on pelkkää CSS:ää: nappi on <label>, joka rastittaa piilotetun
 * #__toc-valintaruudun, ja laatikko näkyy ruudun ollessa rastittuna. Kohdan
 * napautus vie otsikkoon, mutta mikään ei poista rastia, joten laatikko jää
 * peittämään juuri avattua tekstiä. Tässä rasti poistetaan, kun luettelon
 * linkkiä on napautettu. Työpöydällä ruutua ei ole rastittu, joten tämä ei
 * tee mitään. */

(() => {
  const toggle = document.getElementById("__toc")
  const contents = document.querySelector(
    ".md-sidebar--secondary [data-md-component=toc]")
  if (!toggle || !contents)
    return

  /* Yksi kuuntelija listalle, ei jokaiselle linkille erikseen. Teema vaihtaa
   * sivua ilman uudelleenlatausta (navigation.instant), jolloin lista
   * korvataan; se ei koske tätä, koska ominaisuus ei ole käytössä. */
  contents.addEventListener("click", event => {
    if (event.target.closest("a.md-nav__link"))
      toggle.checked = false
  })
})()
