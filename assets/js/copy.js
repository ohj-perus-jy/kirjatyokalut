/* Kopiointinapin ilmoitus napin viereen. Teeman nappi (content.code.copy)
 * kuittaa kopioinnin sivun oikean alakulman ilmoituksella (.md-dialog), joka
 * on niin kaukana napista, ettei lukija huomaa sitä. Tässä nappi otetaan
 * teemalta: sen data-clipboard-target poistetaan, jolloin teeman ClipboardJS
 * ei tartu painallukseen, ja kopiointi ja kuittaus tehdään itse. Kuittaus
 * on nappirivin elementti, mutta tyyli sijoittaa sen rivin vasemmalle
 * puolelle, joten se ei siirrä nappeja. Ulkoasu: assets/css/copy.css. */

(() => {
  "use strict";

  /* Ilmoituksen kesto, kuten teeman omalla. */
  const SHOWN_MS = 2000;

  /* Sama teksti kuin teeman: näkyvä koodi (innerText). Attribuutti kertoo
   * tyyleille kopioinnin olevan käynnissä (highlights.css, hidelines.css,
   * teeman rivinumerot ja huomautukset). */
  const text = (code) => {
    code.setAttribute("data-md-copying", "");
    const result = code.innerText;
    code.removeAttribute("data-md-copying");
    return result.trimEnd();
  };

  const notify = (nav, message) => {
    let note = nav.querySelector(":scope > .jyu-copied");
    if (!note) {
      note = document.createElement("span");
      note.className = "jyu-copied";
      note.setAttribute("role", "status");
      nav.prepend(note);
    }
    /* Näkyviin ennen tekstiä: role="status" lukee muutoksen ääneen vain
     * näkyvästä elementistä. */
    note.classList.add("jyu-copied--shown");
    note.textContent = message;
    clearTimeout(note.timer);
    note.timer = setTimeout(
      () => note.classList.remove("jyu-copied--shown"), SHOWN_MS);
  };

  const takeOver = (button) => {
    const pre = button.closest("pre");
    const code = pre?.querySelector(":scope > code");
    if (!code) return;
    button.removeAttribute("data-clipboard-target");
    button.addEventListener("click", async () => {
      const nav = button.parentElement;
      try {
        await navigator.clipboard.writeText(text(code));
        notify(nav, "Kopioitu leikepöydälle");
      } catch {
        notify(nav, "Kopiointi ei onnistunut");
      }
    });
  };

  /* Teema tekee napit vasta DOMContentLoaded-tapahtumassa (ks. playground.js:
   * afterTheme). Ilman leikepöytärajapintaa (http muualla kuin localhostissa)
   * napit jäävät teemalle, joka osaa vanhan execCommand-tavan. */
  const start = () => {
    if (!navigator.clipboard?.writeText) return;
    document.querySelectorAll(".md-code__button[data-md-type=copy]")
      .forEach(takeOver);
  };
  if (document.readyState === "loading") {
    addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
