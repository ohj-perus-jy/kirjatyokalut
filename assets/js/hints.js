/* Opastusnuolet koodilohkon nappeihin. Aidan määre (luokkana lohkon divissä,
 * convert.py: fence_info) nimeää napin: copyhint kopiointinappiin, playhint
 * ajonappiin, eyehint silmänappiin. Napin alle tulee keinuva nuoli, joka
 * poistuu napin ensimmäisellä painalluksella (hints.css). Kirja merkitsee
 * määreellä lohkon, jonka kohdalla toiminto esitellään.
 *
 * Painallus jää localStorageen ("jyu-hints": napin tyypit, joita lukija on
 * painanut), eikä sen napin nuolta näytetä enää millään sivulla: opastus on
 * tehnyt tehtävänsä. Mikä tahansa saman tyypin nappi käy, ei vain
 * opastettu, ja muiden tyyppien nuolet jäävät. Ilman localStoragea
 * (yksityinen tila) nuoli palaa seuraavalla sivulla.
 *
 * Nuoli on napin oma lapsi, joten se seuraa nappia, olipa rivissä mitä
 * nappeja tahansa: lohkossa ei välttämättä ole ajonappia (ignore,
 * noplayground) eikä silmää (ei piilorivejä). Jos määreen nappia ei ole,
 * nuolta ei tule. Nuoli on SVG eikä maski kuten napin kuvake, koska maski
 * leikkaisi heittovarjon pois; väri tulee currentColorista. aria-hidden,
 * ettei ruudunlukija lue kuvaa; nuoli on osoittimelle läpinäkyvä.
 *
 * Napit tekevät teema (kopiointi, DOMContentLoaded), playground.js ja
 * hidelines.js (DOMContentLoaded-kuuntelijat omassa järjestyksessään), joten
 * tämä on skripteistä viimeisenä (mkdocs-pohja.yml) ja odottaa saman
 * tapahtuman. */

(() => {
  "use strict";

  /* Määre -> napin data-md-type (teema, playground.js, hidelines.js). */
  const HINTS = { copyhint: "copy", playhint: "run", eyehint: "hidelines" };

  const KEY = "jyu-hints";

  /* localStorage voi puuttua (yksityinen tila); silloin nuoli poistuu vain
   * tältä sivulta. */
  const pressed = () => {
    try {
      const types = JSON.parse(localStorage.getItem(KEY));
      return new Set(Array.isArray(types) ? types : []);
    } catch {
      return new Set();
    }
  };
  const remember = (type) => {
    try {
      localStorage.setItem(KEY, JSON.stringify([...pressed().add(type)]));
    } catch {
      /* ei tallennusta */
    }
  };

  const ARROW = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 28">'
    + '<path d="M12 25V5M4.5 12.5 12 5l7.5 7.5" fill="none" stroke="currentColor"'
    + ' stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round"/></svg>';

  const addHint = (button) => {
    const hint = document.createElement("span");
    hint.className = "jyu-hint";
    hint.setAttribute("aria-hidden", "true");
    hint.innerHTML = ARROW;
    button.append(hint);
  };

  /* Saman tyypin kaikki nuolet pois kerralla: sivulla voi olla useampi
   * opastettu lohko. */
  const removeHints = (type) => {
    for (const hint of document.querySelectorAll(
      `[data-md-type=${type}] > .jyu-hint`)) {
      hint.remove();
    }
  };

  const start = () => {
    const done = pressed();
    for (const [attribute, type] of Object.entries(HINTS)) {
      if (done.has(type)) continue;
      for (const block of document.querySelectorAll(`div.highlight.${attribute}`)) {
        const button = block.querySelector(
          `:scope > pre > nav.md-code__nav > [data-md-type=${type}]`);
        if (button) addHint(button);
      }
    }
    /* Kuuntelija dokumentissa, ei napeissa: lukija voi painaa myös nappia,
     * jonka alla ei ole nuolta, ja sekin opettaa toiminnon. */
    document.addEventListener("click", (event) => {
      const type = event.target.closest?.("nav.md-code__nav > [data-md-type]")
        ?.dataset.mdType;
      if (!type || !Object.values(HINTS).includes(type)) return;
      remember(type);
      removeHints(type);
    });
  };

  if (document.readyState === "loading") {
    addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
