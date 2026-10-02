/* Nappien vihjeet. Teema (content.tooltips) tekee title-attribuutista vihjeen
 * vain elementeille, jotka ovat sivulla sen käynnistyessä (DOMContentLoaded),
 * sekä omalle kopiointinapilleen. Nappiriviin sen jälkeen lisätyt napit
 * (playground.js, hidelines.js), soitinpalkki (puhe.js) ja vaiheittaisen
 * ohjeen napit (walkthrough.js) saisivat vain selaimen oman vihjeen, jota
 * kosketusnäyttö ei näytä lainkaan. Tässä niille tehdään vihje teeman omilla
 * luokilla (.md-tooltip2), jolloin ulkoasu tulee teeman tyylistä ja on sama
 * kuin kopiointinapilla. Toiminta kuten teemassa: vihje on auki, kun napilla
 * on osoitin tai kohdistus; auki ollessaan title on pois attribuutista, ettei
 * selain näytä omaansa päälle.
 *
 * Lisäksi: napautuksen jälkeen kohdistus jää nappiin, ja kosketusnäytöllä
 * osoitinta ei ole, joten vihje jäisi peittämään napin alla olevaa. Siksi
 * osoittimella (ei näppäimistöllä) painettu nappi menettää kohdistuksen.
 * Koskee myös teeman omia vihjeitä, kuten kopiointinappia. Valikkojen napit
 * (aria-expanded) hoitavat kohdistuksensa itse (sitemenu.js, fontmenu.js).
 *
 * Ensimmäisenä extra_javascriptissä: DOMContentLoaded-kuuntelijat ajetaan
 * rekisteröintijärjestyksessä, ja teeman jälkeen heti tämän on nähtävä, mitkä
 * title-elementit teema ehti ottaa, ennen kuin muut skriptit lisäävät omiaan. */

(() => {
  "use strict";

  /* Sulkemisen viive ja häivytyksen kesto, kuten teemassa. */
  const HIDE_MS = 250;

  /* Teeman ottamat elementit (title sivulla sen käynnistyessä) ja tässä
   * vihjeen saaneet napit. */
  const taken = new WeakSet();
  const attached = new WeakSet();

  let count = 0;

  const attach = (button) => {
    const tip = document.createElement("div");
    tip.className = "md-tooltip2";
    tip.setAttribute("role", "tooltip");
    tip.id = `__jyu_tooltip_${count++}`;
    const inner = document.createElement("div");
    inner.className = "md-tooltip2__inner md-typeset";
    tip.append(inner);

    let text = "";
    let open = false;
    let focused = false;
    let hovered = false;
    let timer = 0;

    const place = () => {
      const box = button.getBoundingClientRect();
      tip.style.setProperty("--md-tooltip-host-x", `${box.x + scrollX}px`);
      tip.style.setProperty("--md-tooltip-host-y", `${box.y + scrollY}px`);
      tip.style.setProperty("--md-tooltip-x", `${box.width / 2}px`);
      tip.style.setProperty("--md-tooltip-y", `${8 + box.height}px`);
    };

    const fill = (value) => {
      text = value;
      inner.textContent = value;
      tip.style.setProperty("--md-tooltip-width", `${inner.offsetWidth}px`);
    };

    const show = () => {
      clearTimeout(timer);
      if (open) return;
      const title = button.getAttribute("title");
      if (!title) return;
      open = true;
      button.removeAttribute("title");
      /* Häivytyksen aikana uudelleen avattu on vielä sivulla. */
      if (!tip.isConnected) document.body.append(tip);
      fill(title);
      tip.style.setProperty("--md-tooltip-tail", "0px");
      tip.classList.add("md-tooltip2--bottom");
      place();
      button.setAttribute("aria-describedby", tip.id);
      addEventListener("resize", place);
      /* Seuraavassa kehyksessä, jotta siirtymä näkyy, kuten teemassa. */
      requestAnimationFrame(() => {
        if (open) tip.classList.add("md-tooltip2--active");
      });
    };

    /* Sulkeminen viiveellä kuten teemassa: napautus (touchstart, touchend)
     * ehtii näyttää vihjeen, ja osoittimen käväisy napin ohi ei välkytä. */
    const hide = () => {
      if (!open) return;
      timer = setTimeout(() => {
        open = false;
        tip.classList.remove("md-tooltip2--active");
        removeEventListener("resize", place);
        button.removeAttribute("aria-describedby");
        /* Skripti on voinut vaihtaa titlen vihjeen ollessa auki
         * (hidelines.js); silloin uusi jää eikä vanhaa palauteta. */
        if (!button.hasAttribute("title")) button.setAttribute("title", text);
        timer = setTimeout(() => tip.remove(), HIDE_MS);
      }, HIDE_MS);
    };

    const update = () => {
      if (focused || hovered) show();
      else hide();
    };

    button.addEventListener("focusin", () => { focused = true; update(); });
    button.addEventListener("focusout", () => { focused = false; update(); });
    if (matchMedia("(hover)").matches) {
      button.addEventListener("mouseenter", () => { hovered = true; update(); });
      button.addEventListener("mouseleave", () => { hovered = false; update(); });
    } else {
      button.addEventListener("touchstart", () => { hovered = true; update(); },
        { passive: true });
      for (const type of ["touchend", "touchcancel"]) {
        button.addEventListener(type, () => { hovered = false; update(); });
      }
    }

    /* Title vaihtui vihjeen ollessa auki: teksti vihjeeseen ja attribuutti
     * taas pois. */
    new MutationObserver(() => {
      if (!open || !button.hasAttribute("title")) return;
      fill(button.getAttribute("title"));
      button.removeAttribute("title");
    }).observe(button, { attributeFilter: ["title"] });
  };

  const start = () => {
    for (const element of document.querySelectorAll("[title]")) taken.add(element);
    const consider = (button) => {
      if (taken.has(button) || attached.has(button)) return;
      attached.add(button);
      attach(button);
    };
    new MutationObserver((records) => {
      for (const record of records) {
        if (record.type === "attributes") {
          if (record.target.hasAttribute("title")) consider(record.target);
          continue;
        }
        for (const node of record.addedNodes) {
          if (!(node instanceof Element)) continue;
          if (node.matches("button[title]")) consider(node);
          node.querySelectorAll("button[title]").forEach(consider);
        }
      }
    }).observe(document.body, {
      childList: true, subtree: true, attributeFilter: ["title"],
    });
  };
  if (document.readyState === "loading") {
    addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }

  /* Osoittimella painettu vihjeellinen nappi menettää kohdistuksen (detail
   * on 0 näppäimistöllä). Vihjeellisyys katsotaan kirjanpidosta eikä
   * attribuuteista: avautuessaan teema ottaa titlen pois ennen kuin kirjoittaa
   * aria-describedbyn, joten click-hetkellä kumpaakaan ei välttämättä ole.
   * Kohdistus siirtyy lähimpään kohdistettavaan säiliöön, jos sellainen on
   * (vaiheittaisen ohjeen nuolinäppäimet toimivat sen sisällä), muuten pois. */
  document.addEventListener("click", (event) => {
    if (!event.detail) return;
    const button = event.target.closest("button");
    if (!button || button.hasAttribute("aria-expanded")) return;
    if (!taken.has(button) && !attached.has(button)) return;
    const host = button.parentElement?.closest("[tabindex]");
    if (host) host.focus({ preventScroll: true });
    else button.blur();
  });
})();
