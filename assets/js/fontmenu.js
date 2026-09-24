/* Leipätekstin kirjasimen alasvetovalikko yläpalkissa. Avaa ja sulkee listan,
 * kirjoittaa valinnan bodyn data-jyu-font-attribuuttiin ja localStorageen
 * ("jyu-font"). Tallennetun arvon lukee sivun alussa header.html:n
 * inline-skripti, jotta teksti ei välähdä oletuskirjasimella.
 *
 * Oletus (data-font="") ei tallennu vaan poistaa tallennuksen. Lista on
 * role="listbox" kuten <select>: nuolet liikkuvat, Enter valitsee, Esc sulkee.
 * Myös hiiri siirtää kohdistusta, joten korostettuna on aina yksi kohta.
 * Painikkeessa on vain kuvake, joten valinta kerrotaan sen title- ja
 * aria-label-attribuuteissa (kohdan data-short). Title näkyy teeman vihjeenä
 * (content.tooltips), ks. hint. */

(() => {
  "use strict";

  const KEY = "jyu-font";

  const root = document.querySelector("[data-md-component=jyu-font]");
  if (!root) return;

  const button = root.querySelector(".jyu-font__button");
  const list = root.querySelector(".jyu-font__list");
  const items = [...root.querySelectorAll(".jyu-font__item")];
  if (!button || !list || !items.length) return;

  /* localStorage voi puuttua (yksityinen tila); silloin valinta koskee vain tätä sivua. */
  const stored = () => {
    try {
      return localStorage.getItem(KEY) || "";
    } catch {
      return "";
    }
  };
  const store = (id) => {
    try {
      if (id) localStorage.setItem(KEY, id);
      else localStorage.removeItem(KEY);
    } catch {
      /* ei tallennusta */
    }
  };

  /* Teeman vihje on auki, kun painikkeella on osoitin tai kohdistus. Auetessaan
   * se ottaa title-attribuutin talteen ja sulkeutuessaan palauttaa sen. Jos
   * valinta tehdään vihjeen ollessa auki (esim. osoitin jää painikkeelle ja
   * valitaan nuolilla), vihjeeseen jäisi vanha nimi ja se palautuisi myös
   * attribuuttiin. Siksi auki olevan vihjeen teksti vaihdetaan ja palautettu
   * vanha nimi korjataan. Listan ollessa auki vihje piilotetaan (cover), koska
   * se tulisi painikkeen alle listan päälle. Vihjeen id on aria-describedbyssä
   * vain vihjeen ollessa auki, joten se otetaan talteen. */
  let name = "";
  let tip = "";
  const hint = (text) => {
    name = text;
    if (button.hasAttribute("title")) {
      button.title = text;
      return;
    }
    const inner = document.getElementById(tip)?.firstElementChild;
    if (inner) {
      inner.textContent = text;
      inner.parentElement.style.setProperty("--md-tooltip-width", `${inner.offsetWidth}px`);
    }
  };
  const cover = () => {
    const element = document.getElementById(tip);
    if (element) element.hidden = !list.hidden;
  };
  new MutationObserver(() => {
    tip = button.getAttribute("aria-describedby") || tip;
    if (button.hasAttribute("title") && button.title !== name) button.title = name;
    cover();
  }).observe(button, { attributeFilter: ["title", "aria-describedby"] });

  const apply = (id) => {
    const item = items.find((candidate) => candidate.dataset.font === id) || items[0];
    const chosen = item.dataset.font;
    if (chosen) document.body.setAttribute("data-jyu-font", chosen);
    else document.body.removeAttribute("data-jyu-font");
    for (const candidate of items) {
      candidate.setAttribute("aria-selected", String(candidate === item));
    }
    const text = "Leipätekstin kirjasin: " + (item.dataset.short || item.querySelector(".jyu-font__name").textContent);
    hint(text);
    button.setAttribute("aria-label", text);
  };

  /* Kohtien nimet näkyvät omilla kirjasimillaan, ja selain lataa kirjasimen
   * vasta kun sitä käytetään: ilman tätä nimet piirtyisivät avattaessa ensin
   * varakirjasimella ja vaihtuisivat hetken päästä, jolloin listan leveyskin
   * muuttuu. Lataus alkaa, kun osoitin tai kohdistus tulee valikkoon, eli
   * ennen kuin lista ehtii aueta. Perheet luetaan tyyleistä (fontmenu.css). */
  const preload = () => {
    for (const item of items) {
      const name = item.querySelector(".jyu-font__name");
      document.fonts?.load("1em " + getComputedStyle(name).fontFamily, name.textContent);
    }
  };
  root.addEventListener("pointerenter", preload, { once: true });
  root.addEventListener("focusin", preload, { once: true });

  const selected = () => items.find((item) => item.getAttribute("aria-selected") === "true") || items[0];

  const open = () => {
    list.hidden = false;
    cover();
    button.setAttribute("aria-expanded", "true");
    selected().focus();
  };

  const close = (refocus) => {
    if (list.hidden) return;
    list.hidden = true;
    cover();
    button.setAttribute("aria-expanded", "false");
    if (refocus) button.focus();
  };

  /* Ensin suljetaan, jotta vihje on taas näkyvissä ja hint voi mitata sen. */
  const choose = (item, refocus) => {
    close(refocus);
    store(item.dataset.font);
    apply(item.dataset.font);
  };

  /* Hiirellä kohdistus ei jää painikkeeseen eikä piilotettuun kohtaan, koska
   * teeman vihje pysyisi silloin auki osoittimen lähdettyä. Näppäimistöllä
   * (click-tapahtuman detail 0) kohdistus jää painikkeeseen tai palaa siihen. */
  button.addEventListener("click", (event) => {
    if (list.hidden) {
      open();
    } else {
      close(false);
      if (event.detail) button.blur();
    }
  });

  button.addEventListener("keydown", (event) => {
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      open();
    }
  });

  list.addEventListener("click", (event) => {
    const item = event.target.closest(".jyu-font__item");
    if (!item) return;
    item.blur();
    choose(item, false);
  });

  /* Hiiren alla oleva kohta saa kohdistuksen (ulkoasu: :focus). Erillinen
   * :hover-korostus jäisi näkyviin nuolilla liikuttaessa toisen rinnalle. */
  list.addEventListener("pointermove", (event) => {
    const item = event.target.closest(".jyu-font__item");
    if (item && item !== document.activeElement) item.focus();
  });

  list.addEventListener("keydown", (event) => {
    const index = items.indexOf(document.activeElement);
    const move = (to) => {
      event.preventDefault();
      items[(to + items.length) % items.length].focus();
    };
    switch (event.key) {
      case "ArrowDown": move(index + 1); break;
      case "ArrowUp": move(index - 1); break;
      case "Home": move(0); break;
      case "End": move(items.length - 1); break;
      case "Enter":
      case " ":
        event.preventDefault();
        if (index >= 0) choose(items[index], true);
        break;
      case "Escape":
        event.preventDefault();
        close(true);
        break;
      case "Tab":
        close(false);
        break;
    }
  });

  /* Sulje, kun painetaan muualle. */
  document.addEventListener("pointerdown", (event) => {
    if (!root.contains(event.target)) close(false);
  });

  /* Alkutila: bodyn attribuutti on jo asetettu, tässä vihje ja valintamerkki. */
  apply(stored());
})();
