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
 * Teeman ottamien elementtien title siirretään heti talteen ja pois
 * attribuutista (stash). Teema ottaa titlen pois vasta avatessaan vihjeen,
 * kuvaruutua myöhemmin, ja siihen mennessä selain on voinut ajastaa oman
 * title-vihjeensä, joka jää näkyviin teeman vihjeen rinnalle: Chrome ja
 * Safari päivittävät sen tekstin vasta osoittimen liikkuessa, ja Chrome
 * näyttää sen myös näppäimistöllä kohdistetulle elementille. Teema avaa nyt
 * tyhjän vihjeen, ja teksti kirjoitetaan tästä (fill). Skriptin myöhemmin
 * asettama title siirtyy samoin, joten title on yhä tapa antaa vihjeen
 * teksti (fontmenu.js). Elementti, jolla ei ole muuta nimeä (teeman
 * teemanvaihtimen labelit), saa titlen aria-labeliksi.
 *
 * Ensimmäisenä extra_javascriptissä: DOMContentLoaded-kuuntelijat ajetaan
 * rekisteröintijärjestyksessä, ja teeman jälkeen heti tämän on nähtävä, mitkä
 * title-elementit teema ehti ottaa, ennen kuin muut skriptit lisäävät omiaan. */

(() => {
  "use strict";

  /* Häivytyksen kesto kuten teemassa, ja kosketuksella myös sulkemisen viive. */
  const HIDE_MS = 250;

  /* Teeman ottamat elementit (title sivulla sen käynnistyessä) ja tässä
   * vihjeen saaneet napit. */
  const taken = new WeakSet();
  const attached = new WeakSet();

  /* Teeman ottamien elementtien vihjeteksti ja ne, joille tämä antoi
   * aria-labelin titlestä. */
  const texts = new WeakMap();
  const labelled = new WeakSet();

  /* Teeman vihje on auki, kun aria-describedby osoittaa siihen. */
  const fill = (element) => {
    const tip = document.getElementById(element.getAttribute("aria-describedby"));
    if (tip?.getAttribute("role") !== "tooltip" || !texts.has(element)) return;
    const inner = tip.firstElementChild;
    inner.textContent = texts.get(element);
    tip.style.setProperty("--md-tooltip-width", `${inner.offsetWidth}px`);
  };

  const stash = (element) => {
    const title = element.getAttribute("title");
    if (title === null) return;
    element.removeAttribute("title");
    /* Tyhjä title on teeman palauttama: vihje avattiin titlen jo poissa ollessa. */
    if (!title) return;
    texts.set(element, title);
    const named = element.hasAttribute("aria-labelledby")
      || (element.hasAttribute("aria-label") && !labelled.has(element))
      || element.textContent.trim();
    if (!named) {
      element.setAttribute("aria-label", title);
      labelled.add(element);
    }
    fill(element);
  };

  let count = 0;

  /* Teeman näköinen vihje ankkurin alle: avaus heti, sulkeminen viiveellä ja
   * häivytys kuten teemassa. Lisätyille napeille (attach) ja teemanvaihtimelle
   * (palette). Sijainti päivitetään myös vierittäessä, koska yläpalkki pysyy
   * paikallaan. */
  const tooltip = () => {
    const tip = document.createElement("div");
    tip.className = "md-tooltip2";
    tip.setAttribute("role", "tooltip");
    tip.id = `__jyu_tooltip_${count++}`;
    const inner = document.createElement("div");
    inner.className = "md-tooltip2__inner md-typeset";
    tip.append(inner);

    let anchor = null;
    let open = false;
    let timer = 0;

    const place = () => {
      const box = anchor.getBoundingClientRect();
      tip.style.setProperty("--md-tooltip-host-x", `${box.x + scrollX}px`);
      tip.style.setProperty("--md-tooltip-host-y", `${box.y + scrollY}px`);
      tip.style.setProperty("--md-tooltip-x", `${box.width / 2}px`);
      tip.style.setProperty("--md-tooltip-y", `${8 + box.height}px`);
    };

    const fill = (value) => {
      inner.textContent = value;
      tip.style.setProperty("--md-tooltip-width", `${inner.offsetWidth}px`);
    };

    const show = (target, value) => {
      clearTimeout(timer);
      anchor = target;
      if (!open) {
        open = true;
        /* Häivytyksen aikana uudelleen avattu on vielä sivulla. */
        if (!tip.isConnected) document.body.append(tip);
        tip.style.setProperty("--md-tooltip-tail", "0px");
        tip.classList.add("md-tooltip2--bottom");
        addEventListener("resize", place);
        addEventListener("scroll", place, { passive: true });
        /* Seuraavassa kehyksessä, jotta siirtymä näkyy, kuten teemassa. */
        requestAnimationFrame(() => {
          if (open) tip.classList.add("md-tooltip2--active");
        });
      }
      fill(value);
      place();
    };

    /* Sulkeminen kuten teemassa: häivytys alkaa heti, ja vihje poistuu
     * häivytyksen jälkeen. wait viivästää häivytyksen alkua: kosketuksella
     * napautus (touchstart, touchend) ehtii näin näyttää vihjeen. closed
     * kutsutaan häivytyksen alkaessa. */
    const hide = (closed, wait = 0) => {
      if (!open) return;
      clearTimeout(timer);
      timer = setTimeout(() => {
        open = false;
        tip.classList.remove("md-tooltip2--active");
        removeEventListener("resize", place);
        removeEventListener("scroll", place);
        closed?.();
        timer = setTimeout(() => tip.remove(), HIDE_MS);
      }, wait);
    };

    return { id: tip.id, show, hide, fill, isOpen: () => open };
  };

  const attach = (button) => {
    const tip = tooltip();
    const touch = !matchMedia("(hover)").matches;
    let text = "";
    let owned = false;
    let focused = false;
    let hovered = false;

    /* Title on vihjeen hallussa avauksesta häivytyksen alkuun. */
    const show = () => {
      if (!owned) {
        const title = button.getAttribute("title");
        if (!title) return;
        text = title;
        owned = true;
        button.removeAttribute("title");
        button.setAttribute("aria-describedby", tip.id);
      }
      tip.show(button, text);
    };

    const hide = () => tip.hide(() => {
      owned = false;
      button.removeAttribute("aria-describedby");
      /* Skripti on voinut vaihtaa titlen vihjeen ollessa auki
       * (hidelines.js); silloin uusi jää eikä vanhaa palauteta. */
      if (!button.hasAttribute("title")) button.setAttribute("title", text);
    }, touch ? HIDE_MS : 0);

    const update = () => {
      if (focused || hovered) show();
      else hide();
    };

    button.addEventListener("focusin", () => { focused = true; update(); });
    button.addEventListener("focusout", () => { focused = false; update(); });
    if (!touch) {
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
      if (!owned || !button.hasAttribute("title")) return;
      text = button.getAttribute("title");
      tip.fill(text);
      button.removeAttribute("title");
    }).observe(button, { attributeFilter: ["title"] });
  };

  /* Teemanvaihtimen vihje näppäimistöllä. Teema kiinnittää vihjeen näkyvään
   * labeliin, mutta Tab kohdistaa piilotettuun radionappiin, eikä teeman
   * vihje aukea, koska kohdistus ei ole labelissa (eikä osoitintapahtumilla
   * voi auttaa: teema tarkistaa todellisen :hover-tilan). Siksi
   * näppäimistökohdistuksen ajan näytetään oma vihje näkyvän labelin alla
   * labelin tekstillä. Näkyvä label ei ole välttämättä kohdistetun napin
   * vieressä: teema näyttää sen hidden-attribuutilla eikä valinnalla, ja kun
   * yhtään nappia ei ole valittu, Tab kohdistaa ensimmäiseen. Nuolilla
   * vaihdettaessa teema vaihtaa näkyvän labelin change-tapahtumassa, joten
   * vihje siirretään seuraavassa kehyksessä. Kohdistusrengas: layout.css. */
  const palette = () => {
    const form = document.querySelector("[data-md-component=palette]");
    if (!form) return;
    const tip = tooltip();
    const show = () => {
      const label = form.querySelector("label:not([hidden])");
      const text = label && (texts.get(label) || label.getAttribute("aria-label"));
      if (text) tip.show(label, text);
    };
    form.addEventListener("focusin", (event) => {
      if (event.target.matches(".md-option:focus-visible")) show();
    });
    form.addEventListener("change", () => {
      if (tip.isOpen()) requestAnimationFrame(show);
    });
    form.addEventListener("focusout", () => tip.hide());
  };

  const start = () => {
    for (const element of document.querySelectorAll("[title]")) {
      taken.add(element);
      stash(element);
    }
    palette();
    const consider = (button) => {
      if (taken.has(button) || attached.has(button)) return;
      attached.add(button);
      attach(button);
    };
    new MutationObserver((records) => {
      for (const record of records) {
        if (record.type === "attributes") {
          const target = record.target;
          if (taken.has(target)) {
            if (record.attributeName === "title") stash(target);
            else fill(target);
          } else if (record.attributeName === "title" && target.hasAttribute("title")) {
            consider(target);
          }
          continue;
        }
        for (const node of record.addedNodes) {
          if (!(node instanceof Element)) continue;
          if (node.matches("button[title]")) consider(node);
          node.querySelectorAll("button[title]").forEach(consider);
        }
      }
    }).observe(document.body, {
      childList: true, subtree: true, attributeFilter: ["title", "aria-describedby"],
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
