/* Päävalikon piilotus työpöydällä: yläpalkin painike kytkee kiskon päälle ja
 * pois. Merkkaus: overrides/partials/header.html, ulkoasu: assets/css/layout.css.
 *
 * Tila on html-elementin attribuutti (data-jyu-rail="hidden"), josta
 * layout.css nollaa kiskon leveyden ja piilottaa kiskon. Valinta tallentuu
 * selaimeen (localStorage jyu-rail), ja header.html:n skripti asettaa
 * attribuutin ennen sisältöä, joten seuraava sivu aukeaa oikeassa tilassa
 * ilman välähdystä; tässä vain painikkeen teksti ja tila sovitetaan siihen.
 *
 * Kapealla näytöllä painike on piilossa ja valikko on teeman laatikko, mutta
 * attribuutti saa olla: layout.css lukee sen vain kiskon leveyksillä. */

(() => {
  "use strict";

  const button = document.getElementById("jyu-rail-button");
  const rail = document.querySelector(".md-sidebar--primary");
  if (!button || !rail) return;

  const KEY = "jyu-rail";
  const root = document.documentElement;
  /* Sama raja kuin kiskolla (layout.css). */
  const desktop = matchMedia("(min-width: 73.75em)");

  /* aria-controls osoittaa kiskoon; teema ei anna sille id:tä. */
  rail.id = button.getAttribute("aria-controls");

  const isHidden = () => root.getAttribute("data-jyu-rail") === "hidden";

  /* Vihjeen teksti kertoo, mitä painallus tekee. Title siirtyy teeman
   * vihjeeseen (tooltips.js), myös vihjeen ollessa auki. */
  const describe = () => {
    const text = isHidden() ? "Näytä valikko" : "Piilota valikko";
    button.title = text;
    button.setAttribute("aria-label", text);
    button.setAttribute("aria-expanded", String(!isHidden()));
  };

  /* Teema vierittää avoimen luvun näkyviin vain sivun latautuessa, eikä
   * piilotetulla (display: none) kiskolla ole mittoja, joten piilotettuna
   * avatun sivun kisko olisi palatessaan listan alussa. Luku keskelle, kuten
   * teema tekee latautuessa. Sivu ei vieri: kisko on kiinteä. */
  const reveal = () => {
    const wrap = rail.querySelector(".md-sidebar__scrollwrap");
    const active = wrap?.querySelector(".md-nav__link--active");
    if (!active) return;
    const area = wrap.getBoundingClientRect();
    const box = active.getBoundingClientRect();
    if (box.top >= area.top && box.bottom <= area.bottom) return;
    wrap.scrollTop += box.top - area.top - (area.height - box.height) / 2;
  };

  const toggle = () => {
    if (isHidden()) root.removeAttribute("data-jyu-rail");
    else root.setAttribute("data-jyu-rail", "hidden");
    describe();
    if (!isHidden()) reveal();
    try {
      if (isHidden()) localStorage.setItem(KEY, "hidden");
      else localStorage.removeItem(KEY);
    } catch {
      /* ei tallennusta */
    }
  };

  describe();

  /* Hiirellä painettu painike menettää kohdistuksen, jottei vihje jää auki
   * osoittimen lähdettyä (tooltips.js tekee saman muille napeille, mutta
   * jättää aria-expanded-napit itselleen). Näppäimistöllä (detail 0)
   * kohdistus jää, jotta kytkentä edestakaisin onnistuu. */
  button.addEventListener("click", (event) => {
    toggle();
    if (event.detail) button.blur();
  });

  /* b kytkee kiskon kuten teeman s avaa haun: vain työpöydällä, ilman
   * muunnosnäppäimiä ja vain kun ei kirjoiteta. Hakukenttä on shadow
   * DOM:issa, jossa event.target on isäntä: composedPath kertoo kentän. */
  document.addEventListener("keydown", (event) => {
    if (event.key !== "b" || event.repeat || !desktop.matches) return;
    if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
    const target = event.composedPath()[0];
    if (target instanceof Element
        && target.closest("input, textarea, select, [contenteditable]")) return;
    event.preventDefault();
    toggle();
  });
})();
