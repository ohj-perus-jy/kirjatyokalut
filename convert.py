#!/usr/bin/env python3
"""Kääntää mdBookin lähdepuun (../src) Zensicalin docs/-hakemistoksi.

Työkalut (tämä hakemisto: skriptit, assets, icons, overrides) ovat kirjoille
yhteiset; kirjan omat tiedostot (kirja.toml, mkdocs.yml, cache/, docs/, nav.yml)
ovat kirjan hakemistossa, ks. find_book.

Ajo ilman argumentteja muuntaa kerran; `--watch` ajaa muunnoksen jokaisesta
lähdepuun tai assettien muutoksesta (run.sh käynnistää sen palvelimen rinnalle).

main: sync_docs kopioi muut kuin Markdown-tiedostot, jokainen sivu ajetaan
muunnosten läpi mainin järjestyksessä (järjestys ei ole vapaa, perustelut
mainissa), assetit kopioidaan, SUMMARY.md:stä tulee nav.yml ja tulostussivu,
ja lopuksi siivotaan jäänteet ja tulostetaan muunnosten lukumäärät.

Kirjoitetaan vain muuttunut (write_if_changed) ja yksi ajo kerrallaan
(only_one_run). <asciinema>-tagit menevät läpi sellaisenaan (assets/js/asciinema.js).
Generoitu docs/ on kertakäyttöinen — tämä skripti on totuus.
"""

import collections
import contextlib
import fcntl
import filecmp
import fnmatch
import functools
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
import tomllib
import unicodedata
import traceback
import urllib.error
import urllib.request
import zlib
from collections.abc import Callable
from html import escape, unescape
from pathlib import Path
from typing import NamedTuple

TOOL = Path(__file__).resolve().parent
CONFIG_NAME = "kirja.toml"


def find_book() -> Path:
    """Kirjan hakemisto: se, jossa kirja.toml on. Ajohakemisto (run.sh,
    pages.yml, testit) tai työkalujen ylähakemisto (submodule tyokalut/).
    Ilman asetustiedostoa ylähakemisto; main kieltäytyy silloin ajosta."""
    for candidate in (Path.cwd(), TOOL.parent):
        if (candidate / CONFIG_NAME).is_file():
            return candidate
    return TOOL.parent


BOOK = find_book()
SRC = BOOK.parent / "src"
DOCS = BOOK / "docs"
ASSETS = TOOL / "assets"

# Kirjan asetukset. Vakioiden nimet ovat moduulitasolla, jotta testit voivat
# kiinnittää ne (monkeypatch) kirjasta riippumatta.
CONFIG = (tomllib.loads((BOOK / CONFIG_NAME).read_text(encoding="utf-8"))
          if (BOOK / CONFIG_NAME).is_file() else {})

# Kirjan lyhyt nimi verkkopyyntöjen User-Agentiin (PlantUML, puhe.py).
BOOK_NAME = CONFIG.get("nimi", "kirja")

# Kuvakkeiden glyfit (ks. ICON_MAP) kopioina Zensicalin templates/.icons/:sta,
# koska run.sh ajaa skriptin systeemin python3:lla eikä .venv:stä. test_convert.py
# vertaa kopiot teemaan.
ICONS = TOOL / "icons"

SUMMARY_LINK_RE = re.compile(
    r"^(?P<indent>\s*)(?P<bullet>[-*]\s*)?\[(?P<title>[^\]]*)\]\((?P<href>[^)]*)\)")

# Markdown-tiedostot, jotka eivät ole sivuja (fnmatch lähdepuun polusta).
# mdBook kääntää vain SUMMARY.md:n luvut, Zensical jokaisen .md:n. ohj1:
# tehtävän aloituspohja on opiskelijalle annettava tiedosto, jonka linkki
# #lisaa_osoite on paikkamerkki ja siksi aina rikki. Ks. is_page.
# kirja.toml: ei_sivuja = ["exercises/*/starter/*.md"].
NOT_PAGES: tuple[str, ...] = tuple(CONFIG.get("ei_sivuja", ()))

# Koko sivun ääneenluku (ks. speech_units), kirja.toml:n [puhe]-taulukko:
# sivut (fnmatch lähdepuun polusta, ks. is_speech_page), varasto (leikkeiden
# kansio kirjan hakemistosta, erillisen repon klooni, ks. puhe.py), repo
# (varaston osoite puhe.py:lle) ja aani (Azuren ääni).
SPEECH_CONFIG: dict = CONFIG.get("puhe", {})
SPEECH_PAGES: tuple[str, ...] = tuple(SPEECH_CONFIG.get("sivut", ()))
SPEECH_STORE = BOOK / SPEECH_CONFIG.get("varasto", "puhe")
SPEECH_REPO: str | None = SPEECH_CONFIG.get("repo")
SPEECH_DEFAULT_VOICE = "fi-FI-HarriNeural"
SPEECH_VOICE: str = SPEECH_CONFIG.get("aani", SPEECH_DEFAULT_VOICE)

# Kuvan klikkaus avaa sen täysikokoisena (Zensicalin GLightbox-laajennus,
# ks. build_base). Kirjakohtainen, koska sitä kokeillaan ensin ohj2:ssa.
# kirja.toml: kuvasuurennus = true.
IMAGE_ZOOM: bool = CONFIG.get("kuvasuurennus", False)

# Otsikko, jonka edessä on 1-3 välilyöntiä: CommonMark (mdBook) sallii sen,
# Python-Markdown ei, vaan jättää risuaidat näkyviin. Ks. dedent_headings.
INDENTED_HEADING_RE = re.compile(r"^ {1,3}(?=#{1,6}\s)")

# Linkin ankkuriosa "](../sivu.md#käyttö)", ks. convert_anchors.
ANCHOR_LINK_RE = re.compile(r"\]\((?P<target>[^)\s]*)#(?P<fragment>[^)\s]+)\)")

# Otsikon oma tunnus "## Otsikko{#tunnus}" ilman välilyöntiä aaltosulun edellä.
HEADING_ANCHOR_RE = re.compile(
    r"^(?P<heading>#+\s+\S.*?\S)(?P<anchor>\{#[^}\s]+\})\s*$")

# Tulostussivu: koko kirja yhdellä sivulla, ks. assets/js/print.js.
PRINT_PAGE = "tulosta.md"

PRINT_INTRO = """\
---
title: Koko kirja
search:
  exclude: true
hide:
  - toc
---

<div id="jyu-print-intro" markdown>

# Koko kirja yhtenä sivuna

<p id="jyu-print-status">Selain kokoaa luvut tälle sivulle ja avaa
tulostusikkunan itsestään. Jos JavaScript ei ole käytössä, alla oleva
luettelo on kirjan sisällysluettelo.</p>

</div>

<div id="jyu-print" markdown>

"""

NAV_ENTRY_RE = re.compile(r'^\s*-\s+"(?P<title>[^"]+)":\s*(?P<href>\S+\.md)\s*$', re.M)

# mdBookin välilehdet (preprocessor.accordion): "### [Windows](#tab/win)" aloittaa
# lohkon, "***" lopettaa, peräkkäiset lohkot ovat yksi joukko. Otsikkotasolla ei
# ole väliä, lähde käyttää sekaisin ### ja ####.
TAB_HEADING_RE = re.compile(
    r"^#{1,6}\s+\[(?P<label>[^\]]+)\]\(#tab/(?P<id>[^)]+)\)\s*$")
TAB_END = "***"

# mdBookin monitiedostolohkot (preprocessor.codeblock-tabs). Merkinnät ovat
# lähteessä epätarkkoja ("//FILE:", välilyöntejä lopussa, FILE_END puuttuu tai
# on liikaa) ja mdBook sietää sen, joten sama sietokyky tässä.
FILE_BEGIN_RE = re.compile(r"^\s*//\s*FILE:\s*(?P<name>.+?)\s*$")
FILE_END_RE = re.compile(r"^\s*//\s*FILE_END\s*$")

# Koodiaita. Sisennys otetaan talteen ja kirjoitetaan takaisin sellaisenaan.
CODE_FENCE_RE = re.compile(r"^(?P<indent>\s*)(?P<fence>```+|~~~+)(?P<info>[^\n`]*)$")

# Sama aita myös lainauslohkon sisällä ("> ```java,ignore"). Vain convert_fences
# käyttää: se kirjoittaa pelkän otsikon, joten ">" kelpaa sisennykseksi.
QUOTED_FENCE_RE = re.compile(
    r"^(?P<indent>[\s>]*)(?P<fence>```+|~~~+)(?P<info>[^\n`]*)$")

# mdBookin piilorivit (book.toml: hidelines): "//-"-alkuinen rivi kuuluu
# ohjelmaan muttei näy. ohj1:n book.toml määrittelee vain csharpin; java ja
# javascript ovat mukana ohj2:n koekirjan (tests/book) ja testien takia.
# Lainausmerkit rivin alussa otetaan talteen: alertin sisällä olevassa aidassa
# ">" on vielä paikallaan, koska convert_alerts ajetaan myöhemmin.
HIDELINE_RE = re.compile(r"^((?:[ \t]*>)*[ \t]*)//-")
HIDELINE_LANGUAGES = ("csharp", "java", "javascript")

# mdBookin korostusmerkinnät (theme/code-highlights.js): "// HIGHLIGHT_GREEN_BEGIN"
# ... "// HIGHLIGHT_GREEN_END" värittää väliin jäävät rivit, merkintärivit eivät
# näy. Väli "//":n jälkeen on valinnainen ja rivi voi olla sisennetty tai
# lainauksessa, kuten piiloriveillä.
HIGHLIGHT_RE = re.compile(
    r"^[\s>]*//\s*HIGHLIGHT_(?P<color>[A-Z0-9]+)_(?P<edge>BEGIN|END)\s*$")
HIGHLIGHT_COLORS = ("green", "yellow", "red", "blue")

# ohj1:n mdBook-skripti (theme/code-highlights.js) käsitteli vain javan; csharp
# on kirjan koodia varten, java koekirjan ja testien takia. json ja bash ovat
# työkaluohjeita varten (settings.json, komentorivi): merkintärivit poistetaan
# ennen renderöintiä, joten "//" ei päädy JSON-lexerille.
HIGHLIGHT_LANGUAGES = ("csharp", "java", "json", "bash")

# mdBookin sisällytysmakro. Polun perässä voi olla rivivalinta, ks. take_lines.
INCLUDE_RE = re.compile(r"\{\{#include\s+(?P<spec>[^}\s][^}]*?)\s*\}\}")

# mdBookin alertit (mdbook-alerts): lainauslohko, jonka ensimmäinen rivi on
# pelkkä "[!TUNNUS]". Tunnuksen kirjainkoko vaihtelee lähteessä.
ALERT_RE = re.compile(r"^>\s*\[!(?P<label>[^\]]+)\]\s*$")

# Tunnus (pienellä) -> admonition-tyyppi ja otsikko. Tyyppi valittu mdBookin
# värin ja kuvakkeen mukaan. Teeman tyypeistä vain kanoniset: Zensicalin CSS:ssä
# ei ole aliaksia, joten esim. "important" jäisi tyylittömäksi — siksi Tärkeää
# on "tip". Oppaiden merkinnät (Kokeile, Ei toimi vielä, Kysymys) ovat omia
# tyyppejä, joiden väri ja kuvake ovat assets/css/admonitions.css:ssä; ne
# korvaavat TIM-wikin kuvatiedostot, ja useimmiten lohkossa on pelkkä tunnusrivi.
ALERT_KINDS = {
    "osaamistavoitteet": ("abstract", "Osaamistavoitteet"),
    "huomautus": ("note", "Huomautus"),
    "vinkki": ("tip", "Vinkki"),
    "tärkeää": ("tip", "Tärkeää"),
    "varoitus": ("warning", "Varoitus"),
    "todo": ("info", "Todo"),
    "wip": ("danger", "WIP"),
    "kokeile": ("kokeile", "Kokeile käynnistää pelisi"),
    "ei toimi vielä": ("ei-toimi", "Ei toimi vielä"),
    "kysymys": ("kysymys", "Kysymys"),
}

# Tuntematon tunnus säilyy otsikkona sellaisenaan; tyypiksi tulee neutraalein.
ALERT_FALLBACK = "note"

# <details>-lohkot. Python-Markdown päästää raa'an HTML-lohkon sisällön läpi
# jäsentämättä; markdown-attribuutti (md_in_html, Zensicalin oletuslistalla)
# korjaa sen. <details closed> ei ole HTML:ää mutta toimii, joten attribuutit
# jätetään paikalleen. Lookahead ohittaa jo käännetyn tagin (toistokelpoisuus).
DETAILS_RE = re.compile(r"<details(?![^>]*\bmarkdown=)(?P<attrs>[^>]*)>")

# Sama <summary>-tagille, mutta vain kun yhteenvedossa on tyhjä rivi ennen
# </summary>:ä: se on sama raja, jolla mdBookin pulldown-cmark alkaa jäsentää
# Markdownia. Yksirivinen tai rivitetty teksti jätetään rauhaan, muuten se
# käärittäisiin <p>:hen ja avauspalkki saisi kappaleen marginaalit.
# Arvo on "block" eikä "1": <summary> on md_in_html:n span_tags-listalla, joten
# "1" tarkoittaisi vain rivinsisäistä jäsennystä ja otsikko jäisi risuaidoiksi.
SUMMARY_RE = re.compile(r"<summary(?![^>]*\bmarkdown=)(?P<attrs>[^>]*)>")
SUMMARY_END = "</summary>"
# Rivinsisäinen koodi, jossa tagi on tekstiä (Kirjoita `<summary>`-tagien väliin).
INLINE_CODE_RE = re.compile(r"(`[^`\n]*`)")

# Omaksi kappaleekseen jäänyt <br />, lähteessä väljyydeksi lohkojen väliin.
# Python-Markdown tekee siitä <p><br /></p>, joka moninkertaistaa lohkojen välin;
# laatikoiden omat marginaalit riittävät. Vain omalla rivillään sarakkeessa 0
# oleva tagi pudotetaan: rivin lopussa se on rivinvaihto, sisennetty voi olla koodia.
BREAK_LINE_RE = re.compile(r"^<br\s*/?>\s*$")

# Harjoitustyön vaatimusdivit (harjoitustyo.md), sama ongelma kuin <details>.
# Myös uloin divi tarvitsee attribuutin: md_in_html ei etene sisempiin lohkoihin,
# jos uloin on käsittelemätöntä HTML:ää. Divi ei ole span_tagsissa, joten "1" riittää.
DIV_RE = re.compile(r"<div(?![^>]*\bmarkdown=)(?P<attrs>[^>]*)>")

# Luokkakaaviot: ```plantuml-aita lähetetään samalle PlantUML-palvelimelle kuin
# kirjassa ja vastaus talletetaan tiedostoksi (nimi = lähteen sha1), aita
# korvataan kuvaviittauksella. Tiedostot ovat kirjan versionhallinnassa
# (cache/plantuml/, main kopioi ne docs/assets/plantuml/:iin), joten käännös
# tarvitsee verkkoa vain uudelle tai muuttuneelle kaaviolle; jos palvelin ei
# vastaa, aita jää ennalleen ja ajo varoittaa. Palvelin vaatii User-Agentin
# (muuten 403).
PLANTUML_FENCE_RE = re.compile(r"^(?P<indent>\s*)(?P<fence>```+|~~~+)plantuml\s*$")
PLANTUML_URL = "https://www.plantuml.com/plantuml/svg/"
PLANTUML_AGENT = f"{BOOK_NAME}-zensical"
PLANTUML_DIR = BOOK / "cache" / "plantuml"
PLANTUML_ALPHABET = (
    "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_")

# Kaikki kaaviot ovat luokkakaavioita, joten alt-teksti voi olla tarkka.
PLANTUML_ALT = "UML-luokkakaavio"

# ASCII-kaaviot: ```bob-aita piirretään svgbob_cli:llä (sama svgbob kuin
# mdbook-svgbobissa). Riippuvuus on pehmeä: valmiit kaaviot ovat
# versionhallinnassa (cache/svgbob/), ja ilman komentoa aita jää ennalleen.
# Puuttuva komento asennetaan cargolla, kun sitä ensi kerran tarvitaan.
# Julkaisussa --strict kaataa ajon, jottei kaavio katoa huomaamatta.
# SVG upotetaan sivulle eikä viitata <img>:llä, koska sen värit tulevat sivun
# CSS-muuttujista, joita <img>:n sisältö ei näe; siksi hakemisto on välimuisti
# eikä asset. Kääre on <div>, koska <svg> ei ole Python-Markdownin
# BLOCK_LEVEL_ELEMENTS-listalla ja päätyisi kappaleen sisään.
SVGBOB_FENCE_RE = re.compile(r"^(?P<indent>\s*)(?P<fence>```+|~~~+)bob\s*$")
SVGBOB_DIR = BOOK / "cache" / "svgbob"

# svgbob ja beautiful-mermaid kirjoittavat jokaiseen kaavioon samat id="arrow"
# ym. määrittelyt, joten saman sivun kaaviot saavat juoksevan etuliitteen
# (prefix_svg_ids); print.js lisää tulostussivulla vielä luvun oman etuliitteen.
SVG_ID_RE = re.compile(r'\bid="(?P<name>[^"]+)"')
SVG_REF_RE = re.compile(r"url\(#(?P<name>[^)]+)\)")

SVGBOB_VERSION = "0.7.6"
# book.tomlin piirtoasetukset, värit ja kirjasin Zensicalin muuttujina.
SVGBOB_OPTIONS = [
    "--font-size", "14",
    "--font-family", "var(--md-code-font-family)",
    "--fill-color", "var(--md-default-fg-color)",
    "--stroke-color", "var(--md-default-fg-color)",
    "--stroke-width", "2",
    "--background", "transparent",
]

# svgbob_problems: tekstin sijainti (solu 8 × 16 px) ja lähteen lainatut osat.
SVGBOB_TEXT_RE = re.compile(
    r'<text x="(?P<x>\d+)" y="(?P<y>\d+)"\s*>(?P<text>[^<]*)</text>')
SVGBOB_QUOTED_RE = re.compile(r'"[^"]*"')
SVGBOB_PAREN_RE = re.compile(r"\w[()]|[()]\w")
# Tarkoituksella piirretty soikio: sulun jälkeen väli, esim. ( 18 ) tai ( -148).
SVGBOB_OVAL_RE = re.compile(r"\(\s[^()]*\)")

# svgbob_fit_text: kuvan ja taustan koko sekä merkin leveys. diagrams.css
# pakottaa tekstin svgbobin 8 px:n ruutuun (font-size: calc(8px / .6)).
SVGBOB_SIZE_RE = re.compile(r'width="(?P<width>\d+)" height="(?P<height>\d+)"')
SVGBOB_CHAR_WIDTH = 8

# Mermaid-kaaviot: ```mermaid-aita piirretään beautiful-mermaidilla
# (mermaid/render.mjs, Node) ja upotetaan sivulle SVG:nä kuten bob-kaaviot:
# värit ja kirjasin tulevat sivun CSS-muuttujista (diagrams.css), joten tumma
# teema vaihtuu ilman uudelleenpiirtoa, ja tulostussivu näkee kaaviot. Aiemmin
# teema piirsi aidat selaimessa mermaid.js:llä, jota ei enää ladata. Riippuvuus
# on pehmeä kuten svgbob: valmiit kaaviot ovat versionhallinnassa
# (cache/mermaid/), puuttuvat paketit asennetaan npm:llä, kun niitä ensi kerran
# tarvitaan, ja ilman nodea aita jää koodilohkoksi; --strict kaataa ajon.
MERMAID_FENCE_RE = re.compile(r"^(?P<indent>\s*)(?P<fence>```+|~~~+)mermaid\s*$")
MERMAID_DIR = BOOK / "cache" / "mermaid"
MERMAID_TOOL = TOOL / "mermaid"
MERMAID_RENDER = MERMAID_TOOL / "render.mjs"
MERMAID_MODULES = MERMAID_TOOL / "node_modules"
# Piirtäjän omat korjaukset (patch-package, npm ci ajaa ne), ks. mermaid_renderer.
MERMAID_PATCHES = MERMAID_TOOL / "patches"

# mermaid_clean: piirtäjän tyylilohkosta Google Fontsin @import-rivit pois ja
# kirjasimet teeman muuttujiksi, juurielementin värit (style="--bg:...")
# diagrams.css:n varaan.
MERMAID_IMPORT_RE = re.compile(r"^[ \t]*@import url\([^)]*\);[ \t]*\n", re.MULTILINE)
MERMAID_FONT_RE = re.compile(r"^(?P<indent>[ \t]*)text \{ font-family: [^}]*\}", re.MULTILINE)
MERMAID_MONO_RE = re.compile(r"^(?P<indent>[ \t]*)\.mono \{ font-family: [^}]*\}", re.MULTILINE)
MERMAID_STYLE_ATTR_RE = re.compile(r'(?P<svg><svg\b[^>]*?) style="--bg:[^"]*"')
# Luokan jäsenten merkinnät, jotka beautiful-mermaid 1.1.3 jättää tekstiin:
# geneerinen tyyppi List~Kortti~ tekstielementin sisällössä sekä abstraktin (*)
# ja staattisen ($) jäsenen merkki paluutyypin palassa ("<tspan>: </tspan>
# <tspan>* boolean</tspan>"), vaikka piirtäjä tunnistaa merkin (kursiivi,
# alleviivaus). Ilman paluutyyppiä myös kaksoispiste pois.
MERMAID_TEXT_RE = re.compile(r"(?<=>)[^<>]+(?=</t)")
MERMAID_GENERIC_RE = re.compile(r"~(?P<type>[^~<>]+)~")
MERMAID_MARKER_RE = re.compile(
    r"(?P<colon><tspan[^>]*>: </tspan>)<tspan(?P<attrs>[^>]*)>[*$](?: (?P<rest>[^<]*))?</tspan>")
# Luokan osastot: beautiful-mermaid 1.1.3 piirtää aina otsikon alle attribuutti-
# ja metodiosaston, tyhjän 8 px:n korkuisena (CLS.emptySectionHeight), joten
# jäsenetön luokka näkyy kahtena tyhjänä kaistaleena. Ryhmässä on ulkolaatikko,
# otsikon tausta ja kaksi osastojen rajaviivaa, kukin omalla rivillään.
MERMAID_CLASS_RE = re.compile(
    r'(?P<open><g class="class-node"[^>]*>\n)(?P<body>.*?\n)(?=</g>)', re.DOTALL)
MERMAID_RECT_RE = re.compile(r'<rect x="[^"]*" y="(?P<y>[^"]*)" width="[^"]*" height="(?P<height>[^"]*)"')
MERMAID_LINE_RE = re.compile(r'^[ \t]*<line [^>]*\by1="(?P<y>[^"]*)"[^>]*/>\n', re.MULTILINE)
MERMAID_TEXT_Y_RE = re.compile(r'^(?P<start>[ \t]*<text [^>]*?\by=")(?P<y>[^"]*)(?P<end>"[^>]*>)', re.MULTILINE)
MERMAID_EMPTY_SECTION = 8

# Kaavion koko sivulla: piirtäjän tekstit ovat kiinteitä (luokan nimi 13,
# jäsenet 11 viewBox-yksikköä) eikä niihin ole asetusta, joten diagrams.css
# antaa SVG:lle leveyden em-yksikössä ja skaalaa koko kaavion leipätekstin
# mukaan. Leveys luetaan viewBoxista kääreen muuttujaan (MERMAID_WIDTH_VAR).
# mermaid_zoom: kuvasuurennus (IMAGE_ZOOM) myös kaavioille. Suurennos on 2
# kertaa piirroksen koko eli noin 1,6 kertaa sivulla näkyvä (16,5 px:n
# leipätekstillä kaavio on sivulla 1,27-kertainen); leveä kaavio rajautuu
# ikkunaan.
MERMAID_WIDTH_VAR = "--jyu-mermaid-width"
MERMAID_ZOOM = 2
MERMAID_ROOT_RE = re.compile(r"<svg\b")
MERMAID_VIEWBOX_RE = re.compile(r'\bviewBox="[-\d.]+ [-\d.]+ (?P<width>[\d.]+) [\d.]+"')

# Tehtäväkortit: mdBookin omat elementit <task>, <task-title num="">, <points>,
# <handout>, <task-link>. <task> ei ole Python-Markdownin BLOCK_LEVEL_ELEMENTS-
# listalla, joten kortti jäisi kappaleen sisään eikä md_in_html käsittelisi sitä
# edes attribuutilla. Siksi diveiksi: nimi luokkaan (assets/css/tasks.css),
# tehtävänanto markdown="1":llä. Tunnusrivi on raakaa HTML:ää ilman attribuuttia.
TASK_TAG_RE = re.compile(r"</?(?:task|task-title|task-link|handout)[ >]")
TASK_TITLE_RE = re.compile(
    r'<task-title\s+num="(?P<num>[^"]*)"\s*>(?P<inner>.*?)</task-title>')
TASK_POINTS_RE = re.compile(r"<points>(?P<points>.*?)</points>")

# Bonusmerkki <i class="jyu-star"></i>. Merkki piirretään Materialin
# creation-kuvakkeella (.icons/material/creation.svg). Valmis inline-SVG eikä
# lyhytkoodi, koska <summary>-rivillä Python-Markdown jäsentää lyhytkoodin vain
# attribuutilla markdown="span", ja muunnos nimeää merkin ruudunlukijalle
# (BONUS_WORD_RE). Kääre .twemoji on teeman oma, joten koko, kohdistus ja väri
# tulevat teeman CSS:stä; oma sääntö vain väriin, ks. assets/css/tasks.css.
BONUS_TAG_RE = re.compile(r'<i\s+class="[^"]*\bjyu-star\b[^"]*"\s*>\s*</i>')
BONUS_MARK_PATH = (
    "m19 1-1.26 2.75L15 5l2.74 1.26L19 9l1.25-2.74L23 5l-2.75-1.25"
    "M9 4 6.5 9.5 1 12l5.5 2.5L9 20l2.5-5.5L17 12l-5.5-2.5"
    "M19 15l-1.26 2.74L15 19l2.74 1.25L19 23l1.25-2.75L23 19l-2.75-1.26")

# Rivillä jo oleva bonussana: merkki nimetään ruudunlukijalle vain, jos rivillä
# ei ole samaa tietoa tekstinä.
BONUS_WORD_RE = re.compile(r"bonus|valinnais", re.IGNORECASE)
TASK_TAGS = (
    ("<task>", '<div class="task" markdown="1">'),
    ("</task>", "</div>"),
    ("<handout>", '<div class="task-handout" markdown="1">'),
    ("</handout>", "</div>"),
    ("<task-link>", '<div class="task-link">'),
    ("</task-link>", "</div>"),
)

# Loput ikonitagit (<i class="bi bi-play-fill">, <i class="fa fa-eye">); fontteja
# ei ladata, joten ilman muunnosta ne ovat tyhjää tilaa. Etsitään koko tekstistä
# eikä riveittäin, koska tagi voi olla rivitetty kesken — myös lainauslohkossa,
# jolloin jatkorivi alkaa ">":llä; siksi [\s>]+ eikä \s+. (?P=prefix) pitää
# parit bi bi- / fa fa- erillään.
ICON_TAG_RE = re.compile(
    r'<i[\s>]+class="(?P<prefix>bi|fa)[\s>]+(?P=prefix)-(?P<name>[a-z0-9-]+)'
    r'[^"]*"\s*>\s*</i>')

# Valikkopolun nuoli (File › New) on välimerkki, ei kuvake: pelkkä merkki
# riittää. › (U+203A) siksi, että Source Serif 4:n latin-osajoukko sisältää sen
# (→ ja ▸ eivät kuulu siihen, ja tulisivat varakirjasimesta). Väri vaimennetaan
# assets/css/icons.css:ssä.
PATH_ARROW_ICONS = ("bi-chevron-right", "bi-arrow-right")
PATH_ARROW = '<span class="jyu-path">›</span>'
# Suoraan kirjoitettu › (**Access › Personal access tokens**) saa saman kääreen,
# muuten se jäisi täyteen tekstiväriin. Ohitetaan inline-koodi (merkki on
# esimerkkiä), valmis kääre (muunnos toistuu) ja HTML-tagi (attribuuttiin span ei
# kuulu). Kääre ennen tagia, koska tagin kuvio osuisi kääreen alkuun.
PATH_ARROW_CHAR_RE = re.compile(
    r"(?P<skip>(?P<ticks>`+).+?(?<!`)(?P=ticks)(?!`)"
    r"|" + re.escape(PATH_ARROW) + r"|<[A-Za-z/][^<>]*>)|›", re.DOTALL)

# Oikeat kuvakkeet: käyttöliittymän nappeja, joihin teksti viittaa. Sivuston
# omille napeille sama glyfi kuin napissa (header.html, mkdocs.yml,
# playground.css, hidelines.css); IntelliJ:n ja SceneBuilderin napeille
# Materialin lähin vastine, ääriviivaversio leipätekstin painon takia.
# Glyfit ovat kopioina icons/-hakemistossa, ks. ICONS.
ICON_MAP = {
    "bi-layout-sidebar": "material/menu",
    "bi-list": "material/menu",
    "bi-search": "material/magnify",
    "bi-printer": "lucide/printer",
    "bi-circle-half": "material/weather-night",
    "bi-play-fill": "material/play",
    "fa-play": "material/play",
    "fa-eye": "material/eye-outline",
    "fa-history": "material/history",
    "bi-bug": "material/bug",
    "bi-folder": "material/folder-outline",
    "bi-folder2": "material/folder-outline",
    "bi-terminal": "material/console-line",
    "bi-gear-fill": "material/cog",
    "bi-lightbulb-fill": "material/lightbulb-on-outline",
    "bi-info-circle": "material/information-outline",
    # ohj1: index.md:n edellinen/seuraava-nuolet (navigation.footer).
    "bi-arrow-left-circle": "material/arrow-left-circle-outline",
    "bi-arrow-right-circle": "material/arrow-right-circle-outline",
}


# Muunnoksen lukko, ks. only_one_run.
LOCK = BOOK / ".convert.lock"

# Piirtäjät, jotka epäonnistuivat tässä ajossa ("plantuml", "svgbob",
# "mermaid"); main
# tyhjentää ajon aluksi. prune_diagrams ei saa siivota vajaan käytettyjen joukon
# perusteella. Moduulitason joukko, koska testit nojaavat paluuarvojen muotoon.
FAILED: set[str] = set()

# Tässä ajossa piirretyt kaaviot piirtäjittäin; main tyhjentää ajon aluksi ja
# kertoo lopuksi, koska cache/ on versionhallinnassa: uudet tiedostot pitää
# committoida (--strict ei piirrä), ja piirtäjän muutos piirtää kaikki
# uusiksi, jolloin ne kannattaa katsoa läpi.
RENDERED: collections.Counter[str] = collections.Counter()

# --strict (julkaisu): puuttuvia piirtäjiä ei asenneta. main asettaa.
STRICT = False


def only_one_run():
    """Vain yksi muunnos kerrallaan, myös eri prosesseista. -> kontekstivaraaja.

    Rinnakkaiset ajot (kaksi run.sh:ta) sekoittavat docs/:n, ja prune_diagrams
    poistaisi versionhallinnassa olevia kaavioita, joita toinen ajo ei enää
    nähnyt käytetyiksi. flock eikä lukkotiedosto, jotta lukko vapautuu myös
    tapetusta ajosta.
    """
    return _locked()


@contextlib.contextmanager
def _locked():
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    with open(LOCK, "w", encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def is_page(source_path: str) -> bool:
    """Tuleeko lähdepuun Markdown-tiedostosta (polku lähdepuusta) sivu.

    SUMMARY.md on navigaatio (build_nav), NOT_PAGES tiedostoja, joita mdBook ei
    julkaise. Kumpaakaan ei kirjoiteta docs/:iin, joten sync_docs poistaa
    aiemman ajon kopion jäänteenä.
    """
    return source_path != "SUMMARY.md" and not any(
        fnmatch.fnmatchcase(source_path, pattern) for pattern in NOT_PAGES)


def is_speech_page(source_path: str) -> bool:
    """Luetaanko sivu (polku lähdepuusta) ääneen, ks. SPEECH_PAGES."""
    return any(fnmatch.fnmatchcase(source_path, pattern) for pattern in SPEECH_PAGES)


def prune_diagrams(folder: Path, used: set[str], complete: bool = True) -> int:
    """Käyttämättömät kaaviotiedostot pois. -> poistettuja.

    Nimi on lähteen sha1, joten muokattu kaavio jättäisi vanhan tiedoston.
    Ei siivota, jos used on tyhjä tai complete=False (ks. FAILED): silloin
    joukko on vajaa, ja tiedostot ovat versionhallinnassa eli poisto on
    menetettyä työtä.
    """
    if not complete or not used or not folder.is_dir():
        return 0
    removed = 0
    for path in folder.glob("*.svg"):
        if path.name not in used:
            path.unlink()
            removed += 1
    return removed


def build_base() -> str:
    """Kirjojen yhteiset asetukset (mkdocs-pohja.yml) nav.yml:n alkuun.

    Kirjan mkdocs.yml perii nav.yml:n (INHERIT), joten sinne jäävät vain
    kirjan omat rivit. Pohjan TYOKALUT on polku kirjan hakemistosta tähän
    hakemistoon: Zensical ratkaisee custom_dirin mkdocs.yml:n sijainnista.
    IMAGE_ZOOM lisää laajennuslistaan GLightboxin.
    """
    base = (TOOL / "mkdocs-pohja.yml").read_text(encoding="utf-8")
    if IMAGE_ZOOM:
        base = base.replace("\nmarkdown_extensions:\n", "\nmarkdown_extensions:\n"
                            "  zensical.extensions.glightbox: {}\n")
    tool = Path(os.path.relpath(TOOL, BOOK)).as_posix()
    return ("# Generoitu (convert.py): mkdocs-pohja.yml + navigaatio. Älä muokkaa.\n"
            + base.replace("custom_dir: TYOKALUT/", f"custom_dir: {tool}/") + "\n")


def build_extra(tab_labels: set[str]) -> str:
    """extra.edit_source ja extra.tab_labels mkdocs.yml:n INHERIT-lohkoon.

    tab_labels: convert_tabsin välilehtiotsikot, jotka content.tabs.link saa
    muistaa selaimessa (overrides/partials/javascripts/content.html) — ei
    tiedostonimiä, jotta klikattu tiedosto ei avaisi muita lohkoja väärältä
    välilehdeltä. edit_source: docs/-polku -> src-polku, tyhjä PRINT_PAGElle =
    ei muokkauslinkkiä (overrides/partials/copyright.html). Muut sivut ovat
    docs/:ssä samassa polussa kuin src:ssä, joten ne eivät tarvitse riviä.
    """
    sources = {PRINT_PAGE: ""}
    lines = ["", "# Muokkauslinkin polkukartta, ks. overrides/partials/copyright.html,",
             "# ja välilehtimuistin sallitut otsikot, ks.",
             "# overrides/partials/javascripts/content.html.",
             "extra:", "  edit_source:"]
    for docs_path, src_path in sorted(sources.items()):
        lines.append(f'    "{docs_path}": "{src_path}"')
    lines.append("  tab_labels:")
    for label in sorted(tab_labels):
        lines.append(f'    - "{label}"')
    return "\n".join(lines) + "\n"


def build_print_page(nav_yaml: str) -> str:
    """nav: -lohko -> docs/tulosta.md: linkki jokaiseen lukuun kirjan järjestyksessä.

    Pelkkä runko: assets/js/print.js hakee luvut omilta sivuiltaan valmiina
    HTML:nä. Lukuja ei voi liittää yhdeksi Markdown-tiedostoksi, koska kesken
    jäänyt HTML-lohko tai pariton aita nielaisisi seuraavan luvun alun.
    Ilman JavaScriptiä luettelo jää näkyviin sisällysluettelona.
    """
    lines = [PRINT_INTRO]
    for match in NAV_ENTRY_RE.finditer(nav_yaml):
        lines.append(f"- [{match['title']}]({match['href']})")
    lines.append("\n</div>\n")
    return "\n".join(lines)


def build_nav() -> str:
    """src/SUMMARY.md -> mkdocs nav: -lohko.

    Numerointi kuten mdBookissa: vain listakohdat, juoksevasti erottimien yli;
    etu- ja jälkilinkit jäävät numeroimatta.
    """
    entries: list[tuple[int, str, str, bool]] = []
    # Sisennyspino: taso on pinon syvyys, ei leveys jaettuna kahdella, koska
    # lähteen sisennys ei ole tasainen (ohj1: 1, 3 ja 4 välilyöntiä).
    indents: list[int] = []
    for raw in (SRC / "SUMMARY.md").read_text(encoding="utf-8").split("\n"):
        if not raw.strip() or raw.strip().startswith("#") or set(raw.strip()) == {"-"}:
            continue
        match = SUMMARY_LINK_RE.match(raw)
        if not match:
            continue
        href = match.group("href").strip()
        title = match.group("title").strip()
        if not href:
            # SUMMARY.md:n kikka ulkoiselle linkille: [Otsikko<https://url>]()
            embedded = re.match(r"^(?P<t>.*?)<(?P<u>https?://[^>]+)>$", title)
            if not embedded:
                continue
            title, href = embedded.group("t").strip(), embedded.group("u")
        else:
            href = href.lstrip("./")
        if match.group("bullet"):
            width = len(match.group("indent").expandtabs(4))
            while indents and width < indents[-1]:
                indents.pop()
            if not indents or width > indents[-1]:
                indents.append(width)
            level = len(indents) - 1
        else:
            # Etu- ja jälkilinkki ei kuulu luetteloon: ylin taso, ja seuraava
            # luettelo alkaa alusta. Sisennetty etulinkki on edellisen etulinkin
            # alasivu (mdBook ei sallinut tätä, Zensical sallii); edellinen on
            # silloin hakemistonsa index.md, ks. navigation.indexes.
            indents.clear()
            nested = (match.group("indent") and entries
                      and entries[-1][0] == 0 and not entries[-1][3])
            level = 1 if nested else 0
        entries.append((level, title.replace('"', "'"), href,
                        bool(match.group("bullet"))))

    counters: list[int] = []

    def number_for(depth: int) -> str:
        """Juokseva numero syvyydelle: 1, 1.1, 1.2, 2, ..."""
        del counters[depth + 1:]
        while len(counters) <= depth:
            counters.append(0)
        counters[depth] += 1
        return ".".join(str(n) for n in counters)

    def emit(index: int, depth: int, out: list[str]) -> int:
        pad = "  " * (depth + 1)
        while index < len(entries):
            level, title, href, numbered = entries[index]
            if level < depth:
                return index
            if numbered:
                title = f"{number_for(level)} {title}"
            has_children = index + 1 < len(entries) and entries[index + 1][0] > level
            if has_children:
                out.append(f'{pad}- "{title}":')
                # Osan etusivu ensimmäisenä lapsena (navigation.indexes) tekee
                # osion otsikosta linkin. Otsikko numeroineen myös lapselle,
                # koska edellinen/seuraava-linkit ja <title> lukevat sen sieltä.
                out.append(f'{pad}  - "{title}": {href}')
                index = emit(index + 1, depth + 1, out)
            else:
                out.append(f'{pad}- "{title}": {href}')
                index += 1
        return index

    lines = ["nav:"]
    emit(0, 0, lines)
    return "\n".join(lines) + "\n"


def dedent_headings(text: str) -> tuple[str, int]:
    """Otsikon edestä 1-3 välilyöntiä pois. -> (teksti, siirrettyjä).

    Koodiaidat ohitetaan: aidan sisällä sisennetty "#" on kommentti. ohj1:
    kaksi otsikkoa (osa5/1-debuggaus.md, luennot/luento16.md).
    """
    out: list[str] = []
    open_fence: str | None = None
    moved = 0
    for line in text.split("\n"):
        fence = CODE_FENCE_RE.match(line)
        if fence and open_fence is None:
            open_fence = fence["fence"]
        elif (fence and open_fence is not None and not fence["info"].strip()
                and len(fence["fence"]) >= len(open_fence)):
            open_fence = None
        elif open_fence is None and INDENTED_HEADING_RE.match(line):
            line = line.lstrip(" ")
            moved += 1
        out.append(line)
    return "\n".join(out), moved


def take_lines(content: str, selector: str) -> str | None:
    """Sisällytettävän tiedoston rivivalinta. -> teksti, tai None jos ei rivejä.

    mdBookin muodot "", "N", "A:B", "A:" ja ":B"; numerot 1-pohjaisia, päät
    mukaan. Ilman loppurivinvaihtoa kuten mdBookissa, jotta sisällytys mahtuu
    taulukon soluun. Ankkurimuotoa (":ANCHOR") ei toteuteta: se palauttaa
    None ja makro jää näkyviin.
    """
    lines = content.splitlines()
    if not selector:
        return "\n".join(lines)
    bounds = selector.split(":")
    if len(bounds) > 2 or not any(bounds) or not all(b.isdigit() or not b
                                                     for b in bounds):
        return None
    first = bounds[0]
    last = bounds[1] if len(bounds) == 2 else first
    start = int(first) if first else 1
    end = int(last) if last else len(lines)
    return "\n".join(lines[max(start - 1, 0):end])


def convert_includes(text: str, page: Path) -> tuple[str, int]:
    """mdBookin {{#include}} -> tiedoston sisältö paikalleen. -> (teksti, määrä).

    page on lähdepuun sivu, ei docs/-kopio: sisällytettävä tiedosto luetaan
    aina muuntamattomana, koska tehtävänannot ovat itsekin muunnettavia sivuja.
    Rivin sisennystä ei toisteta, kuten ei mdBookkaan. Puuttuvasta tiedostosta
    ja tuntemattomasta valinnasta varoitetaan ja makro jätetään näkyviin.
    """
    includes = 0

    def expand(match: re.Match) -> str:
        nonlocal includes
        path, _, selector = match["spec"].partition(":")
        target = page.parent / path.strip()
        if not target.is_file():
            print(f"varoitus: {page.name}: sisällytettävä tiedosto puuttuu: "
                  f"{path.strip()}", file=sys.stderr)
            return match[0]
        content = take_lines(target.read_text(encoding="utf-8"), selector.strip())
        if content is None:
            print(f"varoitus: {page.name}: tuntematon rivivalinta: "
                  f"{match['spec']}", file=sys.stderr)
            return match[0]
        includes += 1
        return content

    return INCLUDE_RE.sub(expand, text), includes


def convert_anchors(text: str) -> tuple[str, int, int]:
    """Ankkurit Zensicalin muotoon. -> (teksti, linkkiä, otsikkoa).

    1. Ääkköset pois linkin ankkurista ("#käyttö" -> "#kaytto"): Python-Markdownin
       slugify pudottaa ei-ascii-merkit, mdBook ei. Vain sivuston omiin
       linkkeihin; skeemallisen osoitteen ankkurista päättää toinen sivusto.
    2. Välilyönti otsikon oman tunnuksen eteen ("## Otsikko {#tunnus}"), jota
       attr_list vaatii; muuten tunnukseksi tulisi "otsikkotunnus".
    Koodiaidat ohitetaan: aidassa näytetty linkki on esimerkki.
    """
    links = headings = 0

    def fold(match: re.Match) -> str:
        nonlocal links
        if "://" in match["target"]:
            return match[0]
        folded = (unicodedata.normalize("NFKD", match["fragment"])
                  .encode("ascii", "ignore").decode("ascii"))
        if folded == match["fragment"]:
            return match[0]
        links += 1
        return f']({match["target"]}#{folded})'

    out: list[str] = []
    open_fence: str | None = None
    for line in text.split("\n"):
        match = CODE_FENCE_RE.match(line)
        if match and open_fence is None:
            open_fence = match["fence"]
        elif (match and not match["info"].strip()
                and len(match["fence"]) >= len(open_fence)):
            open_fence = None
        elif open_fence is None:
            line, spaced = HEADING_ANCHOR_RE.subn(
                r"\g<heading> \g<anchor>", line)
            headings += spaced
            line = ANCHOR_LINK_RE.sub(fold, line)
        out.append(line)
    return "\n".join(out), links, headings


def read_tab_set(lines: list[str],
                 start: int) -> tuple[list[tuple[str, str, list[str]]], int]:
    """Lue yksi välilehtijoukko riviltä start alkaen.

    Palauttaa osiot (tunnus, otsikko, sisältörivit) ja ensimmäisen rivin
    joukon jälkeen. Osion sisältö päättyy "***"-riviin tai — jos se puuttuu —
    seuraavaan välilehtiotsikkoon, jottei rikkinäinen lohko niele loppusivua.
    """
    sections: list[tuple[str, str, list[str]]] = []
    index = start
    while index < len(lines):
        heading = TAB_HEADING_RE.match(lines[index])
        if not heading:
            break
        index += 1
        body: list[str] = []
        while (index < len(lines) and lines[index].strip() != TAB_END
               and not TAB_HEADING_RE.match(lines[index])):
            body.append(lines[index])
            index += 1
        if index < len(lines) and lines[index].strip() == TAB_END:
            index += 1
        sections.append((heading["id"], heading["label"].strip(), body))
        while index < len(lines) and not lines[index].strip():
            index += 1
    return sections, index


def indent_block(body: list[str]) -> list[str]:
    """Rivit sisäkkäisen lohkon sisällöksi: tyhjät päät pois, muu 4 välilyöntiä
    sisemmäs. Suhteelliset sisennykset säilyvät, joten listat, koodiaidat ja
    raaka HTML pysyvät ennallaan. Sama sisennys kelpaa välilehdelle
    (convert_tabs, convert_files) ja admonitionille (convert_alerts)."""
    while body and not body[0].strip():
        body = body[1:]
    while body and not body[-1].strip():
        body = body[:-1]
    return [f"    {line}" if line.strip() else "" for line in body]


def fence_language(info: str) -> str:
    """Aidan otsikon kieli mdBookin muodossa: "java,ignore" -> "java".

    Valmiiksi pymdownx:n muodossa oleva otsikko ("{ .java .multifile }") ei
    palauta kieltä. Ne kirjoittaa convert_files, joka on käsitellyt oman
    lohkonsa piilorivit jo itse, eikä samaa runkoa pidä käsitellä kahdesti.
    """
    info = info.strip()
    return "" if info.startswith("{") else info.split(",")[0].strip()


def rendered_body(body: list[str]) -> tuple[int, int]:
    """Piirtyvän rungon rajat aidan sisällä. -> (ensimmäinen, viimeisen jälkeinen).

    Markdown pudottaa aidan alun ja lopun tyhjät rivit, joten rivinumerot on
    laskettava jäljelle jäävästä rungosta. Pelkkä "> " on tyhjä, koska
    lainausmerkki katoaa myöhemmin (convert_alerts).
    """
    first, last = 0, len(body)
    while first < last and not body[first].strip(" \t>"):
        first += 1
    while last > first and not body[last - 1].strip(" \t>"):
        last -= 1
    return first, last


def hide_lines(body: list[str], language: str) -> tuple[list[str], list[int]]:
    """Piiloriveiltä etuliite pois. -> (rivit, piilorivien numerot).

    Etuliite on riisuttava, koska ajonappi lähettää koodin sellaisenaan ja
    "//-" tekisi rivistä kommentin; myös korostus menisi väärin. Piilotus
    tapahtuu selaimessa: numerot menevät aidan attribuutiksi (fence_info) ja
    assets/js/hidelines.js merkitsee rivit.
    """
    if language not in HIDELINE_LANGUAGES:
        return body, []
    first, _ = rendered_body(body)
    lines: list[str] = []
    hidden: list[int] = []
    for index, line in enumerate(body):
        stripped = HIDELINE_RE.sub(r"\1", line, count=1)
        if stripped != line:
            hidden.append(index - first + 1)
        lines.append(stripped)
    return lines, hidden


def mark_highlights(body: list[str],
                    language: str) -> tuple[list[str], dict[str, list[int]]]:
    """Korostusmerkinnät pois. -> (rivit, {väri: rivinumerot}).

    Sama työnjako kuin hide_lines: merkintärivit pois, numerot aidan
    attribuutiksi (fence_info). Alue päättyy ensimmäiseen END-riviin väristä
    riippumatta, kuten mdBookissa; sulkematon alue jatkuu lohkon loppuun.
    """
    if language not in HIGHLIGHT_LANGUAGES:
        return body, {}
    lines: list[str] = []
    marked: list[str | None] = []
    active: str | None = None
    for line in body:
        match = HIGHLIGHT_RE.match(line)
        if not match:
            lines.append(line)
            marked.append(active)
            continue
        color = match["color"].lower()
        if color not in HIGHLIGHT_COLORS:
            print(f"varoitus: tuntematon korostusväri, rivi jää värittömäksi: "
                  f"{line.strip()}", file=sys.stderr)
        active = color if match["edge"] == "BEGIN" else None
    # Rungon rajat vasta merkintärivien poiston jälkeen: BEGIN-rivi aidan
    # alussa ei ole tyhjä rivi.
    first, last = rendered_body(lines)
    colors: dict[str, list[int]] = {}
    for index in range(first, last):
        if marked[index]:
            colors.setdefault(marked[index], []).append(index - first + 1)
    return lines, colors


def fence_info(info: str, hidden: tuple[int, ...] | list[int] = (),
               colors: dict[str, list[int]] | None = None) -> str:
    """mdBookin aidan attribuuttilista -> pymdownx:n aitaotsikko.

    "java,ignore" -> "{ .java .ignore data-hidden="1 5" data-hl-green="2 3" }".
    pymdownx ei tunnista aitaa, jonka otsikossa on pilkku, ja tunnistamaton
    aita nielaisee seuraavan tekstin koodiksi. Määreet säilyvät luokkina
    (ajonappi ym. tarvitsevat niitä), rivinumerot data-attribuutteina.
    """
    parts = [part.strip() for part in info.strip().split(",")]
    language, attributes = parts[0], [part for part in parts[1:] if part]
    if not language or (not attributes and not hidden and not colors):
        return language
    written = [f".{name}" for name in [language, *attributes]]
    if hidden:
        written.append(f'data-hidden="{" ".join(str(number) for number in hidden)}"')
    for color, numbers in sorted((colors or {}).items()):
        written.append(f'data-hl-{color}="{" ".join(str(n) for n in numbers)}"')
    return "{ " + " ".join(written) + " }"


def convert_fences(text: str) -> tuple[str, int, int, int]:
    """Aitojen attribuuttilistat pymdownx:n muotoon, piilorivit ja korostukset
    talteen. -> (teksti, aitoja, piilorivilohkoja, korostuslohkoja).

    Otsikko kirjoitetaan vasta sulkevalla aidalla, koska rivinumerot selviävät
    rungosta; sulkematon aita jää ennalleen. Korostukset ennen piilorivejä,
    koska merkintärivien poisto muuttaa rivinumeroita.
    """
    out: list[str] = []
    open_fence: str | None = None
    opening = 0
    header = indent = ""
    fences = blocks = marked = 0
    for line in text.split("\n"):
        match = QUOTED_FENCE_RE.match(line)
        info = match["info"].strip() if match else ""
        if match and open_fence is None:
            open_fence, opening = match["fence"], len(out)
            header, indent = info, match["indent"]
        elif match and not info and len(match["fence"]) >= len(open_fence):
            language = fence_language(header)
            body, colors = mark_highlights(out[opening + 1:], language)
            body, hidden = hide_lines(body, language)
            out[opening + 1:] = body
            blocks += bool(hidden)
            marked += bool(colors)
            if "," in header or hidden or colors:
                fences += 1
                out[opening] = (
                    f"{indent}{open_fence}{fence_info(header, hidden, colors)}")
            open_fence = None
        out.append(line)
    return "\n".join(out), fences, blocks, marked


def read_alert(lines: list[str], start: int) -> tuple[list[str], int]:
    """Lue yhden alertin sisältö riviltä start alkaen (tunnusrivi on start).

    -> (lainauslohkon loput rivit, ensimmäinen rivi lohkon jälkeen). Lohko
    loppuu ensimmäiseen riviin, joka ei ala ">"-merkillä; laiskoja jatkorivejä
    ei tueta.
    """
    index = start + 1
    while index < len(lines) and lines[index].startswith(">"):
        index += 1
    return lines[start + 1:index], index


def alert_body(body: list[str]) -> list[str]:
    """Lainauslohkon rivit admonitionin sisällöksi: ">" ja yksi välilyönti pois,
    neljä välilyöntiä sisemmäs. Lohkon omat sisennykset säilyvät."""
    return indent_block([line[1:].removeprefix(" ") for line in body])


def convert_alerts(text: str) -> tuple[str, int, set[str]]:
    """mdBookin alertit -> admonitionit. -> (teksti, lohkoja, tuntemattomat).

    "> [!VINKKI]" -> '!!! tip "Vinkki"'. Otsikko aina näkyviin, koska muuten
    Material näyttää tyypin englanninkielisen nimen.
    """
    lines = text.split("\n")
    out: list[str] = []
    unknown: set[str] = set()
    alerts = 0
    index = 0
    while index < len(lines):
        match = ALERT_RE.match(lines[index])
        if not match:
            out.append(lines[index])
            index += 1
            continue
        label = match["label"].strip()
        known = ALERT_KINDS.get(label.lower())
        if known is None:
            unknown.add(label)
        kind, title = known or (ALERT_FALLBACK, label)
        body, index = read_alert(lines, index)
        alerts += 1
        if out and out[-1].strip():
            out.append("")
        out.append(f'!!! {kind} "{title}"')
        # Pelkkä tunnusrivi (oppaiden merkinnät) on otsikollinen laatikko ilman
        # sisältöä; tyhjä rivi kuuluu vain otsikon ja sisällön väliin.
        if body:
            out.append("")
            out.extend(alert_body(body))
        # Tyhjä rivi perään vain jos lähteessä ei jo ollut.
        if index < len(lines) and lines[index].strip():
            out.append("")
    return "\n".join(out), alerts, unknown


def plantuml_encode(source: str) -> str:
    """Kaavion lähde -> PlantUML-palvelimen osoitepala.

    Raaka deflate (zlib-otsikko ja tarkiste pois) ja base64 PlantUMLin omalla
    aakkostolla ilman "="-täytettä.
    """
    data = zlib.compress(source.encode("utf-8"), 9)[2:-4]
    encoded: list[str] = []
    for start in range(0, len(data), 3):
        chunk = data[start:start + 3]
        chunk += bytes(3 - len(chunk))
        bits = chunk[0] << 16 | chunk[1] << 8 | chunk[2]
        encoded += [PLANTUML_ALPHABET[(bits >> shift) & 63]
                    for shift in (18, 12, 6, 0)]
    return "".join(encoded)[:(len(data) * 8 + 5) // 6]


def plantuml_svg(source: str) -> str | None:
    """Kaavion lähde -> tiedostonimi cache/plantuml/:ssä, tai None.

    Nimi on lähteen sha1, joten muuttunut kaavio hakee itsensä uudelleen ja
    muuttumaton luetaan levyltä. None tarkoittaa, ettei kaaviota saatu: silloin
    aita jätetään ennalleen eikä käännös kaadu.
    """
    name = hashlib.sha1(source.encode("utf-8")).hexdigest() + ".svg"
    path = PLANTUML_DIR / name
    if path.is_file():
        return name
    request = urllib.request.Request(PLANTUML_URL + plantuml_encode(source),
                                     headers={"User-Agent": PLANTUML_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            svg = response.read()
    except (urllib.error.URLError, OSError) as error:
        print(f"varoitus: plantuml-palvelin ei vastannut: {error}",
              file=sys.stderr)
        FAILED.add("plantuml")
        return None
    # Syntaksivirheestä palvelin vastaa 200:lla ja virhekuvalla; se kelpaa,
    # mutta muu kuin SVG ei.
    if b"<svg" not in svg[:1000]:
        print("varoitus: plantuml-palvelin ei palauttanut SVG:tä",
              file=sys.stderr)
        FAILED.add("plantuml")
        return None
    PLANTUML_DIR.mkdir(parents=True, exist_ok=True)
    path.write_bytes(svg)
    RENDERED["plantuml"] += 1
    return name


def convert_plantuml(text: str, page: Path) -> tuple[str, int, set[str]]:
    """```plantuml-aidat kuviksi. -> (teksti, kaavioita, käytetyt tiedostot).

    Kuvan osoite on suhteellinen sivun sijaintiin docs/:ssä.
    """
    depth = len(page.relative_to(DOCS).parent.parts)
    prefix = "../" * depth
    lines = text.split("\n")
    out: list[str] = []
    used: set[str] = set()
    diagrams = 0
    number = 0
    while number < len(lines):
        match = PLANTUML_FENCE_RE.match(lines[number])
        if not match:
            out.append(lines[number])
            number += 1
            continue
        end = number + 1
        while end < len(lines) and lines[end].strip() != match["fence"]:
            end += 1
        if end == len(lines):  # sulkematon aita: jätetään rauhaan
            out.append(lines[number])
            number += 1
            continue
        name = plantuml_svg("\n".join(lines[number + 1:end]).strip() + "\n")
        if name is None:
            out.extend(lines[number:end + 1])
        else:
            used.add(name)
            diagrams += 1
            out.append(f'{match["indent"]}![{PLANTUML_ALT}]'
                       f"({prefix}assets/plantuml/{name})"
                       "{ .uml }")
        number = end + 1
    return "\n".join(out), diagrams, used


def svgbob_svg(art: str) -> str | None:
    """ASCII-piirros -> SVG:n rivit yhtenä merkkijonona, tai None.

    Nimi on piirroksen sha1, joten muuttunut piirros piirretään uudelleen ja
    muuttumaton luetaan välimuistista. None tarkoittaa, ettei svgbobia ole
    asennettu: silloin aita jätetään ennalleen eikä käännös kaadu.
    """
    path = SVGBOB_DIR / (hashlib.sha1(art.encode("utf-8")).hexdigest() + ".svg")
    if path.is_file():
        return path.read_text(encoding="utf-8")
    command = shutil.which("svgbob_cli") or install_svgbob()
    if command is None:
        print("varoitus: svgbob_cli puuttuu, ascii-kaaviot jäävät koodilohkoiksi"
              f" (cargo install svgbob_cli@{SVGBOB_VERSION})", file=sys.stderr)
        FAILED.add("svgbob")
        return None
    try:
        result = subprocess.run([command, *SVGBOB_OPTIONS], input=art,
                                capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as error:
        print(f"varoitus: svgbob epäonnistui: {error.stderr.strip()}",
              file=sys.stderr)
        FAILED.add("svgbob")
        return None
    SVGBOB_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(result.stdout, encoding="utf-8")
    RENDERED["svgbob"] += 1
    return result.stdout


@functools.cache
def install_svgbob() -> str | None:
    """Asenna svgbob_cli cargolla, kerran prosessia kohden. -> polku tai None.

    Ei asenneta --strict-ajossa eikä ilman cargoa. Polku haetaan cargon
    asennushakemistosta, jos se ei ole PATHissa.
    """
    cargo = shutil.which("cargo")
    if STRICT or cargo is None:
        return None
    print("svgbob_cli puuttuu, asennetaan: cargo install"
          f" svgbob_cli@{SVGBOB_VERSION} (kääntyy noin minuutissa)", file=sys.stderr)
    if subprocess.run([cargo, "install", "--locked",
                       f"svgbob_cli@{SVGBOB_VERSION}"]).returncode:
        return None
    root = Path(os.environ.get("CARGO_INSTALL_ROOT") or os.environ.get("CARGO_HOME")
                or Path.home() / ".cargo")
    return shutil.which("svgbob_cli") or shutil.which("svgbob_cli",
                                                      path=str(root / "bin"))


def prefix_svg_ids(svg: str, prefix: str) -> str:
    """Kaavion tunnisteet ja niiden viittaukset omaan nimiavaruuteensa.

    Ks. SVG_ID_RE: ilman tätä saman sivun kaavioilla on samat tunnisteet.
    """
    svg = SVG_ID_RE.sub(lambda m: f'id="{prefix}-{m["name"]}"', svg)
    return SVG_REF_RE.sub(lambda m: f'url(#{prefix}-{m["name"]})', svg)


def svgbob_fit_text(svg: str) -> str:
    """Kuvan koko niin suureksi, että kaikki teksti mahtuu.

    svgbob 0.7.6 laskee koon viivoista ja lainaamattomasta tekstistä, joten
    oikean tai alareunan lainattu teksti leikkautuisi pois. Reunaan jää sama
    6 px kuin svgbobin omassa laskennassa.
    """
    size = SVGBOB_SIZE_RE.search(svg)
    if not size:
        return svg
    width, height = int(size["width"]), int(size["height"])
    fit_width, fit_height = width, height
    for match in SVGBOB_TEXT_RE.finditer(svg):
        end = int(match["x"]) + len(unescape(match["text"])) * SVGBOB_CHAR_WIDTH
        fit_width = max(fit_width, math.ceil(end) + 6)
        fit_height = max(fit_height, ((int(match["y"]) - 12) // 16 + 2) * 16)
    if (fit_width, fit_height) == (width, height):
        return svg
    return svg.replace(size[0], f'width="{fit_width}" height="{fit_height}"')


def svgbob_problems(art: str, svg: str) -> list[str]:
    """Kaavion rivit, jotka svgbob 0.7.6 piirtää eri tavalla kuin ne lukevat.

    Peräkkäiset ääkköset hajoavat päällekkäisiksi paloiksi (Käännä -> "Kän"
    ja "änä"), ja kirjaimen vieressä oleva sulku piirtyy kaarena (Main()).
    Kumpikin korjaantuu lainausmerkeillä, joita svgbob ei piirrä.
    """
    lines = art.split("\n")
    problems: dict[str, None] = {}
    for match in SVGBOB_TEXT_RE.finditer(svg):
        text = unescape(match["text"])
        row, col = (int(match["y"]) - 12) // 16, (int(match["x"]) - 2) // 8
        line = lines[row] if row < len(lines) else ""
        # Lainattu teksti alkaa lainausmerkin sarakkeesta.
        if text not in (line[col:col + len(text)],
                        line[col + 1:col + 1 + len(text)]):
            problems[f"teksti sotkeutuu: {line.strip()}"] = None
    for line in lines:
        bare = SVGBOB_QUOTED_RE.sub(lambda m: " " * len(m[0]), line)
        bare = SVGBOB_OVAL_RE.sub(lambda m: " " * len(m[0]), bare)
        if SVGBOB_PAREN_RE.search(bare):
            problems[f"sulut piirtyvät kaarina: {line.strip()}"] = None
    return list(problems)


def convert_svgbob(text: str, source_path: str = "") -> tuple[str, int, set[str]]:
    """```bob-aidat upotetuiksi SVG-kaavioiksi. -> (teksti, kaavioita, nimet).

    Ajetaan convert_divsin jälkeen, jottei kääre saisi markdown="1":tä.
    Tyhjät rivit pois, koska ne päättäisivät raa'an HTML-lohkon.
    """
    lines = text.split("\n")
    out: list[str] = []
    used: set[str] = set()
    diagrams = 0
    number = 0
    while number < len(lines):
        match = SVGBOB_FENCE_RE.match(lines[number])
        if not match:
            out.append(lines[number])
            number += 1
            continue
        end = number + 1
        while end < len(lines) and lines[end].strip() != match["fence"]:
            end += 1
        if end == len(lines):  # sulkematon aita: jätetään rauhaan
            out.append(lines[number])
            number += 1
            continue
        art = "\n".join(lines[number + 1:end]) + "\n"
        svg = svgbob_svg(art)
        if svg is None:
            out.extend(lines[number:end + 1])
        else:
            for problem in svgbob_problems(art, svg):
                print(f"varoitus: {source_path}: svgbob-kaavio, {problem}"
                      " (kirjoita teksti lainausmerkkeihin)", file=sys.stderr)
            used.add(hashlib.sha1(art.encode("utf-8")).hexdigest() + ".svg")
            diagrams += 1
            svg = prefix_svg_ids(svgbob_fit_text(svg), f"bob{diagrams}")
            indent = match["indent"]
            out.append(f'{indent}<div class="svgbob">')
            out += [indent + line for line in svg.split("\n") if line.strip()]
            out.append(f"{indent}</div>")
        number = end + 1
    return "\n".join(out), diagrams, used


@functools.cache
def mermaid_renderer() -> str:
    """Piirtäjän tunniste kaavion nimeen (mermaid_name): beautiful-mermaidin ja
    elkjs:n versiot lukitustiedostosta, omat korjaukset ja render.mjs. Kaikki
    ovat työkalujen tiedostoja, joten nimen laskeminen ei tarvitse Nodea."""
    packages = json.loads((MERMAID_TOOL / "package-lock.json")
                          .read_text(encoding="utf-8"))["packages"]
    parts = [f"{name}@{packages['node_modules/' + name]['version']}"
             for name in ("beautiful-mermaid", "elkjs")]
    parts += [path.read_text(encoding="utf-8")
              for path in [*sorted(MERMAID_PATCHES.glob("*.patch")), MERMAID_RENDER]]
    return "\n".join(parts)


def mermaid_name(source: str) -> str:
    """Kaavion tiedosto välimuistissa: lähteen ja piirtäjän sha1."""
    key = f"{mermaid_renderer()}\n{source}".encode("utf-8")
    return hashlib.sha1(key).hexdigest() + ".svg"


def mermaid_installed() -> bool:
    """Onko piirtäjä asennettu nykyisestä lukitustiedostosta ja korjauksista?
    npm ci kirjoittaa node_modules/.package-lock.json:n; jos lukitustiedosto
    tai korjaus on sitä uudempi (git pull), asennus on vanha, eikä sillä
    piirretty kaavio vastaisi nimeään."""
    marker = MERMAID_MODULES / ".package-lock.json"
    if not marker.is_file():
        return False
    installed = marker.stat().st_mtime
    return all(path.stat().st_mtime <= installed for path in
               [MERMAID_TOOL / "package-lock.json", *MERMAID_PATCHES.glob("*.patch")])


def mermaid_svg(source: str) -> str | None:
    """Mermaid-kaavio -> SVG piirtäjän tulosteena, tai None.

    Nimi on lähteen ja piirtäjän sha1 (mermaid_name), joten muuttunut kaavio
    tai piirtäjä piirretään uudelleen ja muuttumaton luetaan välimuistista.
    None tarkoittaa, ettei piirtäjää ole tai kaavio ei piirry (syntaksivirhe):
    silloin aita jätetään ennalleen eikä käännös kaadu.
    """
    path = MERMAID_DIR / mermaid_name(source)
    if path.is_file():
        return path.read_text(encoding="utf-8")
    node = shutil.which("node")
    if node is None or not (mermaid_installed() or install_mermaid()):
        print("varoitus: mermaid-piirtäjä puuttuu tai on vanha, mermaid-kaaviot jäävät"
              f" koodilohkoiksi (node ja npm ci {repo_relative(MERMAID_TOOL)}:ssä)",
              file=sys.stderr)
        FAILED.add("mermaid")
        return None
    try:
        result = subprocess.run([node, str(MERMAID_RENDER)], input=source,
                                capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as error:
        print(f"varoitus: mermaid-kaavio ei piirry: {error.stderr.strip()}",
              file=sys.stderr)
        FAILED.add("mermaid")
        return None
    MERMAID_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(result.stdout, encoding="utf-8")
    RENDERED["mermaid"] += 1
    return result.stdout


@functools.cache
def install_mermaid() -> bool:
    """Asenna piirtäjän paketit npm:llä (mermaid/package-lock.json, korjaukset
    postinstall-vaiheessa), kerran prosessia kohden. -> onnistuiko. Ei
    asenneta --strict-ajossa eikä ilman npm:ää."""
    npm = shutil.which("npm")
    if STRICT or npm is None:
        return False
    print("mermaid-piirtäjä puuttuu tai on vanha, asennetaan: npm ci"
          f" ({repo_relative(MERMAID_TOOL)})", file=sys.stderr)
    return subprocess.run([npm, "ci", "--no-audit", "--no-fund"],
                          cwd=MERMAID_TOOL).returncode == 0


def mermaid_clean(svg: str) -> str:
    """Piirtäjän SVG sivulle: kirjasin ja värit sivun muuttujista.

    beautiful-mermaid tuo kirjasimensa Google Fontsista @importilla ja
    kirjoittaa värit juurielementin style-attribuuttiin; molemmat pois, jotta
    kirjasin on teeman ja värit diagrams.css:n (tumma teema vaihtuu CSS:llä,
    ja attribuutti voittaisi tyylitiedoston). Ks. MERMAID_TEXT_RE.
    """
    svg = MERMAID_IMPORT_RE.sub("", svg)
    svg = MERMAID_FONT_RE.sub(
        r"\g<indent>text { font-family: var(--md-text-font-family); }", svg)
    svg = MERMAID_MONO_RE.sub(
        r"\g<indent>.mono { font-family: var(--md-code-font-family); }", svg)
    svg = MERMAID_STYLE_ATTR_RE.sub(r"\g<svg>", svg, count=1)
    svg = MERMAID_MARKER_RE.sub(
        lambda m: f'{m["colon"]}<tspan{m["attrs"]}>{m["rest"]}</tspan>' if m["rest"] else "",
        svg)
    svg = MERMAID_CLASS_RE.sub(lambda m: m["open"] + mermaid_hide_empty(m["body"]), svg)
    return MERMAID_TEXT_RE.sub(
        lambda m: MERMAID_GENERIC_RE.sub(r"&lt;\g<type>&gt;", m[0]), svg)


def mermaid_hide_empty(body: str) -> str:
    """Luokan tyhjät osastot pois näkyvistä, ks. MERMAID_CLASS_RE.

    Laatikon koko pysyy, koska viivat päättyvät sen reunaan. Jäsenettömässä
    luokassa otsikon tausta täyttää laatikon ja nimi on keskellä; jos vain
    toinen osasto on tyhjä, sen rajaviiva lähtee ja jäsenet siirtyvät puolet
    tyhjästä tilasta, jolloin ylä- ja alareunaan jää yhtä paljon tilaa.
    """
    rects = list(MERMAID_RECT_RE.finditer(body))
    lines = list(MERMAID_LINE_RE.finditer(body))
    if len(rects) != 2 or len(lines) != 2:
        return body
    top, height = float(rects[0]["y"]), float(rects[0]["height"])
    header = float(rects[1]["height"])
    attributes_empty = math.isclose(float(lines[1]["y"]) - float(lines[0]["y"]),
                                    MERMAID_EMPTY_SECTION, abs_tol=0.01)
    methods_empty = math.isclose(top + height - float(lines[1]["y"]),
                                 MERMAID_EMPTY_SECTION, abs_tol=0.01)

    def shift(text: str, mono: bool, amount: float) -> str:
        """Jäsenten (mono) tai nimen ja stereotyypin tekstit pystysuunnassa."""
        def move(m: re.Match) -> str:
            if ('class="mono"' in m[0]) != mono:
                return m[0]
            y = f"{float(m['y']) + amount:.3f}".rstrip("0").rstrip(".")
            return f'{m["start"]}{y}{m["end"]}'
        return MERMAID_TEXT_Y_RE.sub(move, text)

    if attributes_empty and methods_empty:
        body = (body[:rects[1].start("height")] + rects[0]["height"]
                + body[rects[1].end("height"):lines[0].start()]
                + body[lines[0].end():lines[1].start()] + body[lines[1].end():])
        return shift(body, mono=False, amount=(height - header) / 2)
    if attributes_empty or methods_empty:
        body = body[:lines[1].start()] + body[lines[1].end():]
        half = MERMAID_EMPTY_SECTION / 2
        return shift(body, mono=True, amount=-half if attributes_empty else half)
    return body


def mermaid_zoom(svg: str, name: str) -> str:
    """Kaavio linkiksi, jonka klikkaus avaa sen suurennettuna.

    Zensicalin GLightbox-laajennus käärii vain <img>-kuvat, mutta teema
    alustaa GLightboxin kaikille sivun .glightbox-linkeille, ja sen inline-tila
    kloonaa linkin osoittaman elementin (tässä SVG, tunniste name). Klooni
    näkee sivun CSS-muuttujat, joten värit seuraavat teemaa (diagrams.css).
    Leveys ks. MERMAID_ZOOM; GLightboxin oletuskorkeus 506 px pois. Dia ei
    peri sivun em-leveyttä (diagrams.css: width: 100 %), joten koko on
    pikseleinä.
    """
    size = MERMAID_VIEWBOX_RE.search(svg)
    width = (f"min(95vw, {round(float(size['width']) * MERMAID_ZOOM)}px)"
             if size else "95vw")
    svg = MERMAID_ROOT_RE.sub(f'<svg id="{name}"', svg, count=1)
    return (f'<a class="glightbox" href="#{name}" data-type="inline"'
            f' data-width="{width}" data-height="auto">\n{svg}\n</a>')


def convert_mermaid(text: str) -> tuple[str, int, set[str]]:
    """```mermaid-aidat upotetuiksi SVG-kaavioiksi. -> (teksti, kaavioita, nimet).

    Kuten convert_svgbob: convert_divsin jälkeen, tyhjät rivit pois.
    """
    lines = text.split("\n")
    out: list[str] = []
    used: set[str] = set()
    diagrams = 0
    number = 0
    while number < len(lines):
        match = MERMAID_FENCE_RE.match(lines[number])
        if not match:
            out.append(lines[number])
            number += 1
            continue
        end = number + 1
        while end < len(lines) and lines[end].strip() != match["fence"]:
            end += 1
        if end == len(lines):  # sulkematon aita: jätetään rauhaan
            out.append(lines[number])
            number += 1
            continue
        indent = match["indent"]
        source = "\n".join(line.removeprefix(indent)
                           for line in lines[number + 1:end]) + "\n"
        svg = mermaid_svg(source)
        if svg is None:
            out.extend(lines[number:end + 1])
        else:
            used.add(mermaid_name(source))
            diagrams += 1
            svg = prefix_svg_ids(mermaid_clean(svg), f"mm{diagrams}")
            if IMAGE_ZOOM:
                svg = mermaid_zoom(svg, f"mm{diagrams}-kaavio")
            size = MERMAID_VIEWBOX_RE.search(svg)
            style = (f' style="{MERMAID_WIDTH_VAR}: {float(size["width"]):g}"'
                     if size else "")
            out.append(f'{indent}<div class="jyu-mermaid"{style}>')
            out += [indent + line for line in svg.split("\n") if line.strip()]
            out.append(f"{indent}</div>")
        number = end + 1
    return "\n".join(out), diagrams, used


def summary_has_blank_line(lines: list[str], number: int) -> bool:
    """Onko rivillä alkavassa yhteenvedossa tyhjä rivi ennen </summary>:ä?

    Se on raja, jonka takana yhteenveto on Markdownia myös kirjassa, ks.
    SUMMARY_RE. Yhden rivin yhteenveto ja sulkematta jäänyt tagi vastaavat
    molemmat ei.
    """
    line = INLINE_CODE_RE.sub("", lines[number])
    start = line.find("<summary")
    if start < 0 or SUMMARY_END in line[start:]:
        return False
    for line in lines[number + 1:]:
        if SUMMARY_END in line:
            return False
        if not line.strip():
            return True
    return False


def convert_details(text: str) -> tuple[str, int, int]:
    """<details> ja monirivinen <summary> markdown-attribuutilla.
    -> (teksti, details-tageja, summary-tageja). Ks. DETAILS_RE ja SUMMARY_RE.
    Koodiaidat ja rivinsisäinen koodi ohitetaan, jottei koodissa näytetty
    HTML-esimerkki muuttuisi.
    """
    lines = text.split("\n")
    out: list[str] = []
    open_fence: str | None = None
    tags = summaries = 0

    def outside_code(pattern: re.Pattern, replace: Callable[[re.Match], str],
                     line: str) -> tuple[str, int]:
        parts = INLINE_CODE_RE.split(line)
        found = 0
        for index in range(0, len(parts), 2):
            parts[index], count = pattern.subn(replace, parts[index])
            found += count
        return "".join(parts), found

    for number, line in enumerate(lines):
        match = CODE_FENCE_RE.match(line)
        if match and open_fence is None:
            open_fence = match["fence"]
        elif (match and not match["info"].strip()
                and len(match["fence"]) >= len(open_fence)):
            open_fence = None
        elif open_fence is None:
            line, found = outside_code(
                DETAILS_RE, lambda m: f'<details{m["attrs"]} markdown="1">', line)
            tags += found
            if summary_has_blank_line(lines, number):
                line, found = outside_code(
                    SUMMARY_RE, lambda m: f'<summary{m["attrs"]} markdown="block">', line)
                summaries += found
        out.append(line)
    return "\n".join(out), tags, summaries


def drop_breaks(text: str) -> tuple[str, int]:
    """Omaksi kappaleekseen jäänyt <br />-rivi pois. -> (teksti, rivejä).

    Ks. BREAK_LINE_RE. Ehtona tyhjä rivi kummallakin puolella (se tekee
    rivistä kappaleen); toinen tyhjä poistetaan tagin mukana. Koodiaidat
    ohitetaan.
    """
    lines = text.split("\n")
    out: list[str] = []
    open_fence: str | None = None
    breaks = 0
    drop_blank = False
    for number, line in enumerate(lines):
        match = CODE_FENCE_RE.match(line)
        if match and open_fence is None:
            open_fence = match["fence"]
        elif (match and not match["info"].strip()
                and len(match["fence"]) >= len(open_fence)):
            open_fence = None
        elif open_fence is None and BREAK_LINE_RE.match(line):
            before = out[-1].strip() if out else ""
            after = lines[number + 1].strip() if number + 1 < len(lines) else ""
            if not before and not after:
                breaks += 1
                drop_blank = True
                continue
        if drop_blank:
            drop_blank = False
            if not line.strip():
                continue
        out.append(line)
    return "\n".join(out), breaks


def convert_divs(text: str) -> tuple[str, int]:
    """Rivin aloittava <div> -> <div markdown="1">. -> (teksti, tageja).

    Ks. DIV_RE. Vain rivin aloittava tagi, koska Python-Markdown tunnistaa
    lohkotason HTML:n vain omana kappaleenaan. Ajetaan ennen convert_tasksia,
    jotta tehtäväkorttien divit jäävät tämän ulkopuolelle. Koodiaidat ohitetaan.
    """
    out: list[str] = []
    open_fence: str | None = None
    tags = 0
    for line in text.split("\n"):
        match = CODE_FENCE_RE.match(line)
        if match and open_fence is None:
            open_fence = match["fence"]
        elif (match and not match["info"].strip()
                and len(match["fence"]) >= len(open_fence)):
            open_fence = None
        elif open_fence is None and line.lstrip().startswith("<div"):
            line, found = DIV_RE.subn(
                lambda m: f'<div{m["attrs"]} markdown="1">', line)
            tags += found
        out.append(line)
    return "\n".join(out), tags


def bonus_mark(labelled: bool) -> str:
    """Bonusmerkki inline-SVG:nä. -> merkin HTML.

    labelled=True antaa merkille nimen ruudunlukijalle, ks. BONUS_WORD_RE.
    """
    attrs = ' role="img" aria-label="Bonus"' if labelled else ' aria-hidden="true"'
    return (f'<span class="twemoji jyu-bonus"{attrs}>'
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
            f'<path d="{BONUS_MARK_PATH}"/></svg></span>')


def convert_bonus_marks(text: str) -> tuple[str, int]:
    """<i class="jyu-star"> -> bonusmerkki. -> (teksti, merkkejä).

    Tehtäväkorttien merkit on jo käsitelty (task_head). Nimeäminen ratkaistaan
    riveittäin (BONUS_WORD_RE). Koodiaidat ohitetaan.
    """
    out: list[str] = []
    open_fence: str | None = None
    marks = 0
    for line in text.split("\n"):
        match = CODE_FENCE_RE.match(line)
        if match and open_fence is None:
            open_fence = match["fence"]
        elif (match and not match["info"].strip()
                and len(match["fence"]) >= len(open_fence)):
            open_fence = None
        elif open_fence is None and BONUS_TAG_RE.search(line):
            rest = BONUS_TAG_RE.sub("", line)
            mark = bonus_mark(BONUS_WORD_RE.search(rest) is None)
            line, count = BONUS_TAG_RE.subn(mark, line)
            marks += count
        out.append(line)
    return "\n".join(out), marks


def icon_mark(icon: str) -> str | None:
    """Kuvake inline-SVG:nä. -> merkin HTML, tai None jos glyfiä ei ole.

    Kääre .twemoji kuten bonusmerkissä. Aina koriste (aria-hidden), koska
    nappi on lähteessä nimetty samalla rivillä sanoina. Glyfi luetaan joka
    kerta tiedostosta; välimuisti pitäisi tyhjentää testien välissä.
    """
    path = ICONS / f"{icon}.svg"
    if not path.is_file():
        print(f"varoitus: glyfi puuttuu: {path}", file=sys.stderr)
        return None
    svg = path.read_text(encoding="utf-8").strip()
    return f'<span class="twemoji" aria-hidden="true">{svg}</span>'


def convert_icons(text: str) -> tuple[str, int, int, set[str]]:
    """Ikonitagit merkeiksi ja kuvakkeiksi. -> (teksti, nuolia, kuvakkeita,
    tuntemattomia).

    Valikkopolun nuolesta ja suoraan kirjoitetusta ›:stä PATH_ARROW, muista
    ICON_MAPin glyfi. Tuntematon tagi jää näkyviin ja palautuu kutsujalle
    varoitettavaksi. Teksti käsitellään aitojen välisinä paloina eikä
    riveittäin, koska tagi voi olla rivitetty.
    """
    parts: list[tuple[bool, list[str]]] = [(False, [])]
    open_fence: str | None = None
    for line in text.split("\n"):
        fence = CODE_FENCE_RE.match(line)
        if fence and open_fence is None:
            open_fence = fence["fence"]
            parts.append((True, [line]))
            continue
        if (fence and open_fence is not None and not fence["info"].strip()
                and len(fence["fence"]) >= len(open_fence)):
            open_fence = None
            parts[-1][1].append(line)
            parts.append((False, []))
            continue
        parts[-1][1].append(line)
    # Aidan rajalle syntyvä tyhjä pala ei saa muuttua riviksi yhdistettäessä.
    parts = [part for part in parts if part[1]]

    arrows = icons = 0
    unknown: set[str] = set()

    def replace(match: re.Match[str]) -> str:
        nonlocal arrows, icons
        name = f'{match["prefix"]}-{match["name"]}'
        if name in PATH_ARROW_ICONS:
            arrows += 1
            return PATH_ARROW
        mark = icon_mark(ICON_MAP[name]) if name in ICON_MAP else None
        if mark is None:
            unknown.add(name)
            return match[0]
        icons += 1
        return mark

    def wrap(match: re.Match[str]) -> str:
        nonlocal arrows
        if match["skip"]:
            return match[0]
        arrows += 1
        return PATH_ARROW

    out: list[str] = []
    for fenced, lines in parts:
        chunk = "\n".join(lines)
        if not fenced:
            chunk = PATH_ARROW_CHAR_RE.sub(wrap, ICON_TAG_RE.sub(replace, chunk))
        out.append(chunk)
    return "\n".join(out), arrows, icons, unknown


def task_head(match: re.Match[str]) -> str:
    """<task-title num="2.1">Kello<points>1 p.</points></task-title> -> tunnusrivi.

    Bonusliuska jää nimen sisään, jotta se seuraa viimeistä sanaa rivittyessä.
    """
    inner = match["inner"]
    points = TASK_POINTS_RE.search(inner)
    inner = TASK_POINTS_RE.sub("", inner)
    bonus = BONUS_TAG_RE.search(inner) is not None
    name = BONUS_TAG_RE.sub("", inner).strip()
    if bonus:
        name += f' <span class="task-bonus">{bonus_mark(False)}Bonus</span>'
    parts = [f'<span class="task-num">{match["num"]}</span>',
             f'<span class="task-name">{name}</span>']
    if points:
        parts.append(f'<span class="task-points">{points["points"].strip()}</span>')
    return '<div class="task-head">' + "".join(parts) + "</div>"


def convert_tasks(text: str) -> tuple[str, int]:
    """<task>-kortit diveiksi. -> (teksti, kortteja). Ks. TASK_TAG_RE.

    Tagirivien sisennys pois ja tyhjä rivi väliin: Python-Markdown tunnistaa
    lohkotason HTML:n vain omana kappaleenaan, ja neljän välilyönnin sisennys
    olisi koodilohko. Koodiaidat ohitetaan.
    """
    out: list[str] = []
    open_fence: str | None = None
    cards = 0
    skip_blank = False
    for line in text.split("\n"):
        match = CODE_FENCE_RE.match(line)
        if match and open_fence is None:
            open_fence = match["fence"]
        elif (match and not match["info"].strip()
                and len(match["fence"]) >= len(open_fence)):
            open_fence = None
        elif open_fence is None and TASK_TAG_RE.search(line):
            cards += line.count("<task>")
            converted = TASK_TITLE_RE.sub(task_head, line.strip())
            for tag, replacement in TASK_TAGS:
                converted = converted.replace(tag, replacement)
            if out and out[-1].strip():
                out.append("")
            out.append(converted)
            out.append("")
            # Lähteen oma tyhjä rivi tagin perässä ei tule toiseen kertaan.
            skip_blank = True
            continue
        if skip_blank and not line.strip():
            skip_blank = False
            continue
        skip_blank = False
        out.append(line)
    return "\n".join(out), cards


# Testaa tietosi -visat (assets/js/visa.js): <visa>-kääreessä <vaittama
# vastaus="totta|tarua"> ja <kysymys>, jonka vaihtoehdot ovat tehtävälistan
# rivejä (- [x] oikea, - [ ] väärä). Kummankin lopussa <perustelu>. Kukin tagi
# omalla rivillään.
QUIZ_OPEN_RE = re.compile(
    r'^\s*<(?P<tag>visa|kysymys|perustelu|vaittama)'
    r'(?:\s+vastaus="(?P<answer>[^"]*)")?\s*>\s*$')
QUIZ_CLOSE_RE = re.compile(r"^\s*</(?P<tag>visa|vaittama|kysymys|perustelu)>\s*$")
QUIZ_OPTION_RE = re.compile(r"^- \[(?P<mark>[ xX])\] (?P<text>.*)$")
QUIZ_CLAIM_OPTIONS = (("totta", "Totta"), ("tarua", "Tarua"))
QUIZ_SUMMARY = "Näytä vastaus"


def trim_blank(lines: list[str]) -> list[str]:
    """Tyhjät rivit pois alusta ja lopusta."""
    start, end = 0, len(lines)
    while start < end and not lines[start].strip():
        start += 1
    while end > start and not lines[end - 1].strip():
        end -= 1
    return lines[start:end]


def quiz_question(answer: str | None, body: list[tuple[str, bool]],
                  explanation: list[str]) -> tuple[list[str], str | None]:
    """Yksi kysymys HTML-riveiksi. -> (rivit, virhe).

    answer: väittämän vastaus, monivalinnalla None (oikea on [x]-rivi).
    body: (rivi, onko koodiaidassa) ennen perustelua. Vaihtoehdot tulevat
    ensimmäisen vaihtoehtorivin paikalle, sisennetty jatkorivi kuuluu
    edelliseen vaihtoehtoon. Tunniste on kysymyksen tekstin tiiviste, joten
    muuttunut kysymys unohtaa selaimeen tallennetun vastauksen.
    """
    question: list[str] = []
    options: list[list] = []
    place = None
    for line, fenced in body:
        match = None if fenced else QUIZ_OPTION_RE.match(line)
        if match:
            if place is None:
                place = len(question)
            options.append([match["mark"] != " ", match["text"].strip()])
        elif (options and not fenced and line[:1].isspace() and line.strip()
              and place == len(question)):
            options[-1][1] += " " + line.strip()
        else:
            question.append(line)
    problem = None
    if answer is None:
        right = [number for number, (correct, _) in enumerate(options) if correct]
        if len(options) < 2 or len(right) != 1:
            problem = "kysymyksessä pitää olla vaihtoehdot ja täsmälleen yksi [x]"
        answer = "abcdefgh"[right[0]] if len(right) == 1 and right[0] < 8 else ""
        items = ['<ol class="jyu-visa-vaihtoehdot" type="a" markdown="1">']
        items += [f'<li data-arvo="{"abcdefgh"[number]}" markdown="1">{text}</li>'
                  for number, (_, text) in enumerate(options[:8])]
        items.append("</ol>")
    else:
        if options:
            problem = "väittämällä ei ole vaihtoehtoja, vastaus on tagissa"
        place = None
        items = ['<ul class="jyu-visa-vaihtoehdot jyu-visa-tt">']
        items += [f'<li data-arvo="{value}">{label}</li>'
                  for value, label in QUIZ_CLAIM_OPTIONS]
        items.append("</ul>")
    identity = "\n".join(line for line, _ in body).strip()
    digest = hashlib.sha1(identity.encode("utf-8")).hexdigest()[:8]
    if place is None:
        place = len(question)
    out = [f'<div class="jyu-visa-q" data-vastaus="{escape(answer)}"'
           f' data-id="{digest}" markdown="1">', ""]
    out += trim_blank(question[:place]) + ["", *items, ""]
    if rest := trim_blank(question[place:]):
        out += rest + [""]
    if explanation := trim_blank(explanation):
        out += ['<details markdown="1">', f"<summary>{QUIZ_SUMMARY}</summary>", "",
                *explanation, "", "</details>", ""]
    return out + ["</div>"], problem


def convert_quizzes(text: str, source_path: str = "") -> tuple[str, int]:
    """<visa>-lohkot HTML:ksi. -> (teksti, kysymyksiä). Ks. QUIZ_OPEN_RE.

    Ilman skriptiä kysymys on tekstiä, vaihtoehdot lista ja perustelu
    <details>-lohko; visa.js tekee vaihtoehdoista napit. Tyhjät rivit kuten
    convert_tasksissa. Koodiaidat ohitetaan, mutta kysymyksen sisällä ne
    kulkevat mukana.
    """
    out: list[str] = []
    open_fence: str | None = None
    questions = 0
    skip_blank = False
    answer: str | None = None
    body: list[tuple[str, bool]] | None = None
    explanation: list[str] = []
    explaining = False

    def emit(lines: list[str]) -> None:
        if out and out[-1].strip():
            out.append("")
        out.extend(lines)
        out.append("")

    for line in text.split("\n"):
        match = CODE_FENCE_RE.match(line)
        fenced = open_fence is not None
        tag = None
        if match and open_fence is None:
            open_fence = match["fence"]
        elif (match and not match["info"].strip()
                and len(match["fence"]) >= len(open_fence)):
            open_fence = None
        elif open_fence is None:
            tag = QUIZ_OPEN_RE.match(line) or QUIZ_CLOSE_RE.match(line)
        closing = tag is not None and line.lstrip().startswith("</")
        if tag and tag["tag"] == "visa":
            emit(["</div>"] if closing else ['<div class="jyu-visa" markdown="1">'])
            skip_blank = True
            continue
        if tag and tag["tag"] in ("vaittama", "kysymys") and not closing:
            answer = tag["answer"] if tag["tag"] == "vaittama" else None
            if tag["tag"] == "vaittama" and answer not in dict(QUIZ_CLAIM_OPTIONS):
                print(f'varoitus: {source_path}: <vaittama vastaus="{answer}">,'
                      " pitää olla totta tai tarua", file=sys.stderr)
                answer = answer or ""
            body, explanation, explaining = [], [], False
            continue
        if body is not None:
            if tag and tag["tag"] == "perustelu":
                explaining = not closing
            elif tag:
                lines, problem = quiz_question(answer, body, explanation)
                if problem:
                    print(f"varoitus: {source_path}: {problem}", file=sys.stderr)
                emit(lines)
                questions += 1
                body = None
                skip_blank = True
            elif explaining:
                explanation.append(line)
            else:
                body.append((line, fenced or match is not None))
            continue
        if skip_blank and not line.strip():
            skip_blank = False
            continue
        skip_blank = False
        out.append(line)
    if body is not None:
        print(f"varoitus: {source_path}: visan kysymys jää sulkematta",
              file=sys.stderr)
        emit(quiz_question(answer, body, explanation)[0])
    return "\n".join(out), questions


# Vaiheittainen ohje (assets/js/walkthrough.js): <walkthrough scenes="...">
# (valinnaisesti audio: vaiheet luetaan ääneen, ks. walkthrough_audio) ja sen
# sisällä <step scene="...">, kukin tagi omalla rivillään.
WALK_OPEN_RE = re.compile(r'^\s*<walkthrough\s+scenes="(?P<scenes>[^"]+)"'
                          r'(?P<audio>\s+audio)?\s*>\s*$')
STEP_OPEN_RE = re.compile(r'^\s*<step\s+scene="(?P<scene>[^"]+)"\s*>\s*$')
WALK_CLOSE_RE = re.compile(r"^\s*</(?P<tag>walkthrough|step)>\s*$")
WALK_CLOSING = {"walkthrough": "</div>", "step": "</section>"}


def walkthrough_scenes_path(scenes: str) -> str:
    """Kohtaustiedoston polku sivulta, normalisoituna, jotta
    sama tiedosto eri kirjoitusasuin tulee sivulle vain kerran."""
    if re.match(r"^(?:[a-z]+:|/)", scenes):
        return scenes
    return os.path.normpath(scenes).replace(os.sep, "/")


def walkthrough_tag(line: str, source_path: str,
                    audio: dict[str, str] | None = None) -> list[str] | None:
    """Yksi tagirivi HTML-riveiksi; None, jos rivi ei ole tagi. audio:
    kohtaus -> leike (walkthrough_audio)."""
    if match := WALK_OPEN_RE.match(line):
        src = escape(walkthrough_scenes_path(match["scenes"]))
        return [f'<script src="{src}"></script>', "",
                '<div class="jyu-walk" markdown="1">']
    if match := STEP_OPEN_RE.match(line):
        scene = match["scene"]
        sound = (f' data-audio="{escape(clip_url(audio[scene], source_path))}"'
                 if audio and scene in audio else "")
        return [f'<section class="jyu-step" data-scene="{escape(scene)}"{sound}'
                ' markdown="1">']
    if match := WALK_CLOSE_RE.match(line):
        return [WALK_CLOSING[match["tag"]]]
    return None


def convert_walkthroughs(text: str, source_path: str,
                         audio: dict[str, str] | None = None) -> tuple[str, int]:
    """<walkthrough>- ja <step>-tagit HTML:ksi. -> (teksti, ohjeita).

    audio: kohtaus -> leike vaiheille, joiden leike on äänivarastossa
    (walkthrough_audio); vaihe saa sen osoitteen data-audio-attribuuttina.

    Ohjeesta tulee div ja vaiheesta section, molemmat markdown="1", joten
    sisältö käännetään Markdownina ja ohje on ilman skriptiä tavallista tekstiä.
    Kohtaustiedosto tulee ohjeen eteen <script>-tagina. Sen polku on lähteessä
    sivun hakemistosta kuten linkeissä, ja hakemisto-osoitteen askeleen
    lisää Zensical kuten <asciinema src>:lle. Tyhjät rivit ja koodiaidat
    kuten convert_tasksissa.
    """
    out: list[str] = []
    open_fence: str | None = None
    walkthroughs = 0
    skip_blank = False
    for line in text.split("\n"):
        match = CODE_FENCE_RE.match(line)
        tag = None
        if match and open_fence is None:
            open_fence = match["fence"]
        elif (match and not match["info"].strip()
                and len(match["fence"]) >= len(open_fence)):
            open_fence = None
        elif open_fence is None:
            tag = walkthrough_tag(line, source_path, audio)
        if tag:
            walkthroughs += WALK_OPEN_RE.match(line) is not None
            if out and out[-1].strip():
                out.append("")
            out.extend(tag)
            out.append("")
            # Lähteen oma tyhjä rivi tagin perässä ei tule toiseen kertaan.
            skip_blank = True
            continue
        if skip_blank and not line.strip():
            skip_blank = False
            continue
        skip_blank = False
        out.append(line)
    return "\n".join(out), walkthroughs


# Yksittäinen animaatio tavallisella sivulla (assets/js/walkthrough.js:
# animate): <animation scenes="..." scene="..."> ja </animation>, kumpikin
# omalla rivillään. Tagien välissä on varasisältö, esim. kuvakaappaukset.
ANIM_OPEN_RE = re.compile(r'^(?P<indent>\s*)<animation\s+scenes="(?P<scenes>[^"]+)"'
                          r'\s+scene="(?P<scene>[^"]+)"\s*>\s*$')
ANIM_CLOSE_RE = re.compile(r"^(?P<indent>\s*)</animation>\s*$")


def convert_animations(text: str, source_path: str) -> tuple[str, int]:
    """<animation>-tagit HTML:ksi. -> (teksti, animaatioita).

    Tagista tulee div markdown="1". Sen sisältö näkyy ilman skriptiä ja
    tulosteessa; skripti piirtää kohtauksen sen tilalle. Toisin kuin
    convert_walkthroughs, tagia ei nosteta sarakkeeseen 0, koska animaatio on
    usein välilehdellä tai listan kohdassa, ja nosto katkaisisi ne. Sisennetty
    div ei ole Python-Markdownille HTML-lohko, mutta omana kappaleenaan se
    tulee ulos ilman <p>:tä, ja sisältö käännetään tavallisena Markdownina
    (markdown="1" jää vaikutuksettomaksi attribuutiksi). Siksi tagin ympärille
    tulee tyhjät rivit.

    Ajetaan convert_tabsin jälkeen, jotta kohtaustiedostojen <script>-tagit
    tulevat sivun loppuun sarakkeeseen 0 eivätkä viimeisen välilehden
    sisään. Polku kuten convert_walkthroughsissa, sama tiedosto kerran.
    Koodiaidat ohitetaan.
    """
    out: list[str] = []
    open_fence: str | None = None
    scripts: list[str] = []
    animations = 0
    skip_blank = False
    for line in text.split("\n"):
        match = CODE_FENCE_RE.match(line)
        tag = None
        if match and open_fence is None:
            open_fence = match["fence"]
        elif (match and not match["info"].strip()
                and len(match["fence"]) >= len(open_fence)):
            open_fence = None
        elif open_fence is None:
            if opening := ANIM_OPEN_RE.match(line):
                animations += 1
                src = walkthrough_scenes_path(opening["scenes"])
                if src not in scripts:
                    scripts.append(src)
                tag = (f'{opening["indent"]}<div class="jyu-anim"'
                       f' data-scene="{escape(opening["scene"])}" markdown="1">')
            elif closing := ANIM_CLOSE_RE.match(line):
                tag = f'{closing["indent"]}</div>'
        if tag:
            if out and out[-1].strip():
                out.append("")
            out.extend([tag, ""])
            # Lähteen oma tyhjä rivi tagin perässä ei tule toiseen kertaan.
            skip_blank = True
            continue
        if skip_blank and not line.strip():
            skip_blank = False
            continue
        skip_blank = False
        out.append(line)
    if scripts:
        while out and not out[-1].strip():
            out.pop()
        out.append("")
        out.extend(f'<script src="{escape(src)}"></script>' for src in scripts)
        out.append("")
    return "\n".join(out), animations


# Ääneen luettava vaihe (walkthrough.js: kaiutin, leikkeet tekee puhe.py
# äänivarastoon kuten koko sivun ääneenluvussa).
SPEECH_KEYS = {"Ctrl": "Control", "Cmd": "Command"}
SPEECH_HEADING_RE = re.compile(r"^#{1,6}\s+(?P<text>.*?)(?:\s*\{[^}]*\})?\s*$")
SPEECH_ITEM_RE = re.compile(r"^(?:[-*+]|\d+\.)\s+(?P<text>.*)$")
SPEECH_ALERT_RE = re.compile(r"^\[!(?P<label>[^\]]+)\]$")
# Kuvakkeen lyhytkoodi (:material-menu:) on koriste kuten valmis SVG-kuvake;
# joukot kuten Zensicalin templates/.icons/. Koodin sisällä se on tekstiä.
SPEECH_ICON_RE = re.compile(
    r"(`[^`]*`)|:(?:fontawesome|lucide|material|octicons|simple)-[\w-]+:")


def speech_code(code: str) -> str:
    """Koodin pätkä luettavaksi: osoite ja pelkkä ~ pois, polun erottimet ja
    asema sanoina (ohje vertaa Windowsin ja Git Bashin polkuja), valitsimen
    viivat pois ja kulmasulkeista sisältö (<käyttäjänimi>, List<T>, </summary>).
    Tulos on HTML-koodattu, jottei speech_inline poista koodin merkkejä
    tageina; se purkaa koodauksen."""
    if "://" in code or code == "~":
        return ""
    if re.search(r"\\|(?<!<)/(?!>)", code) and " " not in code:
        code = re.sub(r"^([A-Za-z]):", r"\1-asema", code.rstrip("\\/"))
        code = re.sub(r"^~(?=/)", "kotikansio", code)
        code = code.replace("\\", " kenoviiva ").replace("/", " kauttaviiva ")
    else:
        code = re.sub(r"(?<![\w-])--?(?=\w)", "", code)
    code = re.sub(r"</?([^<>]*?)/?>", r" \1 ", code)
    return escape(re.sub(r"\s+", " ", code).strip(), quote=False)


def speech_inline(text: str) -> str:
    """Kappaleen Markdown luettavaksi: linkeistä teksti, osoitteet ja merkinnät
    pois, näppäimet sanoina ja valikkopolun › taukona."""
    text = SPEECH_ICON_RE.sub(lambda m: m[1] or "", text)
    text = re.sub(r"</kbd>\s*\+\s*<kbd>", " plus ", text)
    text = re.sub(r"<kbd>([^<]*)</kbd>",
                  lambda m: " ".join(SPEECH_KEYS.get(word, word) for word in m[1].split()), text)
    text = re.sub(r"`([^`]*)`", lambda m: speech_code(m[1]), text)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    # Alaviiteviittaukset ja attr_list-attribuutit ({: .luokka }, { #tunnus }).
    text = re.sub(r"\[\^[^\]]+\]", "", text)
    text = re.sub(r"\{:?\s*[#.][^}]*\}|\{:[^}]*\}", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = unescape(text)
    text = re.sub(r"\b[a-z]+://\S+", "", text)
    text = text.replace("*", "").replace("_", " ")
    text = text.replace("›", ",").replace("→", " ").replace("▶", "kolmio").replace("×", "kertaa")
    text = re.sub(r"\(\s*\)", "", text)
    text = re.sub(r"\s+", " ", text)
    # Välilyönti pois välimerkin edestä, ei tiedostonimen pisteen (vain .gitignore).
    text = re.sub(r"\s+([,.:;!?])(?=[\s,.:;!?)]|$)", r"\1", text)
    text = re.sub(r"\s+\)", ")", text)
    return re.sub(r"\(\s+", "(", text).strip()


def speech_line(text: str) -> str:
    """Kappaleen tai otsikon Markdown yhdeksi luettavaksi riviksi, lopussa
    välimerkki (tauko). Tyhjä, jos luettavaa ei jää."""
    text = speech_inline(text)
    if not text or text[-1] in ".!?:;":
        return text
    return f"{text}."


def speech_text(block: str) -> str:
    """Vaiheen Markdown ääneen luettavaksi: kappale, otsikko, luettelon kohta
    ja alertin otsikko kukin omalle rivilleen (puhe.py: tauko); koodilohkot pois."""
    lines: list[str] = []
    paragraph: list[str] = []
    fence: str | None = None

    def flush() -> None:
        text = speech_line(" ".join(paragraph))
        paragraph.clear()
        if text:
            lines.append(text)

    for raw in block.split("\n"):
        line = re.sub(r"^\s*>\s?", "", raw).strip()
        match = CODE_FENCE_RE.match(line)
        if fence is not None:
            if match and not match["info"].strip() and len(match["fence"]) >= len(fence):
                fence = None
            continue
        if match:
            flush()
            fence = match["fence"]
        elif alert := SPEECH_ALERT_RE.match(line):
            flush()
            label = alert["label"]
            lines.append(ALERT_KINDS.get(label.lower(), ("", label.capitalize()))[1] + ".")
        elif heading := SPEECH_HEADING_RE.match(line):
            flush()
            paragraph.append(heading["text"])
            flush()
        elif item := SPEECH_ITEM_RE.match(line):
            flush()
            paragraph.append(item["text"])
        elif line:
            paragraph.append(line)
        else:
            flush()
    flush()
    return "\n".join(lines)


def walkthrough_speech(text: str) -> tuple[bool, dict[str, str]]:
    """Sivun lähteestä vaiheiden luettavat tekstit. -> (luetaanko ääneen,
    kohtaus -> teksti).

    Vaiheet luetaan ääneen, jos jossakin <walkthrough>-tagissa on audio.
    Koodiaidan sisällä tagit ohitetaan kuten convert_walkthroughsissa.
    """
    audio = False
    speech: dict[str, str] = {}
    scene: str | None = None
    body: list[str] = []
    fence: str | None = None
    for line in text.split("\n"):
        match = CODE_FENCE_RE.match(line)
        if match and fence is None:
            fence = match["fence"]
        elif match and not match["info"].strip() and len(match["fence"]) >= len(fence):
            fence = None
        elif fence is None:
            if opening := WALK_OPEN_RE.match(line):
                audio = audio or opening["audio"] is not None
            if step := STEP_OPEN_RE.match(line):
                scene, body = step["scene"], []
                continue
            closing = WALK_CLOSE_RE.match(line)
            if closing and closing["tag"] == "step" and scene is not None:
                speech[scene] = speech_text("\n".join(body))
                scene = None
                continue
        if scene is not None:
            body.append(line)
    return audio, speech


def walkthrough_audio(text: str, clips: set[str]) -> tuple[dict[str, str], list[str]]:
    """Vaiheiden leikkeet. -> (kohtaus -> leike, kohtaukset, joiden leike puuttuu).

    Vaiheen leike on koko sivun ääneenluvun tapaan tiiviste luettavasta
    tekstistä (speech_clip) äänivarastossa (clips: available_clips). Muuttunut
    vaihe jää siis äänettömäksi, kunnes puhe.py tekee sen leikkeen, eikä
    vanhaa ohjetta lukeva ääni johda harhaan; main varoittaa.
    """
    if "<walkthrough" not in text:
        return {}, []
    audio, speech = walkthrough_speech(text)
    if not audio:
        return {}, []
    found = {scene: speech_clip(spoken) for scene, spoken in speech.items()}
    return ({scene: clip for scene, clip in found.items() if clip in clips},
            [scene for scene, clip in found.items() if clip not in clips])


def clip_url(clip: str, source_path: str) -> str:
    """Leikkeen osoite sivulta. Mukana on hakemisto-osoitteen askel (sivu.md
    -> sivu/), koska Zensical ei korjaa data-attribuutteja."""
    depth = source_path.count("/") + (Path(source_path).name != "index.md")
    return "../" * depth + f"{SPEECH_ASSETS}/{clip}.mp3"


# --- Koko sivun ääneenluku ----------------------------------------------------
#
# Sivun lopullinen Markdown (convert_page) paloitellaan lohkoiksi, joista
# kukin luetaan omana leikkeenään (speech_units), ja luettavaan lohkoon tulee
# näkymätön merkki, jonka arvo on leikkeen tunniste (mark_speech).
# assets/js/puhe.js soittaa merkityt lohkot järjestyksessä. Leikkeet tekee
# puhe.py äänivarastoon (SPEECH_STORE), josta main kopioi sivuston käyttämät
# docs/:iin. Paloittelu jäljittelee Python-Markdownin lohkojäsennystä vain sen
# verran, että merkki osuu oikeaan lohkoon; tests/test_puhe.py tarkistaa
# oikealla jäsentimellä, ettei merkki muuta sivua.

# Azuren äänimuoto: puhe on kapeakaistaista, 48 kbit/s mono on noin 6 kt
# sekunnissa. Leikkeen tunnisteessa, joten vaihto tekee kaikki uudelleen.
SPEECH_FORMAT = "audio-24khz-48kbitrate-mono-mp3"

# Leikkeiden paikka docs/:ssa ja sivustolla sekä luettelo sivuston käyttämistä
# leikkeistä (tunniste riveittäin), jotta varaston siivous tietää, mitä
# julkaistut sivustot tarvitsevat.
SPEECH_ASSETS = "assets/puhe"
SPEECH_INDEX = "leikkeet.txt"

# Lohkot, joita ei lueta: niiden kohdalla sanotaan, mikä jäi lukematta.
SPEECH_NOTICES = {
    "koodi": "Koodilohko, jota ei lueta ääneen.",
    "taulukko": "Taulukko, jota ei lueta ääneen.",
    "kaavio": "Kaavio, jota ei lueta ääneen.",
    "video": "Video, jota ei lueta ääneen.",
    "nauhoitus": "Terminaalinauhoitus, jota ei lueta ääneen.",
    "visa": "Testaa tietosi -kysymyksiä, joita ei lueta ääneen.",
    "ohje": "Vaiheittainen ohje, jota ei lueta ääneen.",
}

# Merkki kappaleen, luettelon kohdan, laatikon otsikon ja taulukon alkuun.
# Attribuutit ilman lainausmerkkejä, koska laatikon otsikko on itse
# lainausmerkeissä (!!! note "...").
SPEECH_SPAN = "<span class=jyu-puhe data-puhe={clip}></span>"

# Python-Markdownin lohkotason tagit (md.block_level_elements): rivin alussa
# ne aloittavat raa'an HTML-lohkon, muut tagit ovat kappaleen tekstiä.
SPEECH_BLOCK_TAGS = frozenset((
    "address article aside blockquote body canvas center colgroup dd details "
    "div dl dt fieldset figcaption figure footer form group h1 h2 h3 h4 h5 h6 "
    "header hgroup hr html iframe legend li main map math menu nav noscript "
    "object ol option output p pre progress script section style summary "
    "table tbody td textarea tfoot th thead tr ul video").split())

# Aidat, joiden muotoilija ei kirjoita attribuutteja (Zensicalin custom_fences).
SPEECH_CUSTOM_FENCES = ("mermaid", "math")

# Lohkojen alut Python-Markdownin säännöin (markdown.blockprocessors ja
# laajennukset admonition, pymdownx.tabbed, tables, footnotes, abbr).
SPEECH_ATX_RE = re.compile(r"^#{1,6}")
SPEECH_SETEXT_RE = re.compile(r"^[=-]+ *$")
SPEECH_HR_RE = re.compile(
    r"^ {0,3}(?:(?:-+ {0,2}){3,}|(?:_+ {0,2}){3,}|(?:\*+ {0,2}){3,}) *$")
SPEECH_LIST_RE = re.compile(r"^ {0,3}(?:\d+\.|[*+-]) +(?P<text>.*)$")
SPEECH_NESTED_RE = re.compile(r"^ {4,7}(?:\d+\.|[*+-]) +")
SPEECH_TASK_RE = re.compile(r"^\[[ xX]\]\s+")
SPEECH_QUOTE_RE = re.compile(r"^ {0,3}> ?")
SPEECH_BOX_RE = re.compile(
    r'^(?P<kind>!!!|\?\?\?\+?) ?[\w-]+(?: +[\w-]+)*(?: +"(?P<title>.*?)")? *$')
SPEECH_TAB_RE = re.compile(r'^={3}(?P<mode>\+|\+!|!\+|!)? +"(?P<label>.*?)" *$')
SPEECH_DEFINITION_RE = re.compile(
    r"^(?:(?P<note>\[\^[^\]]+\]:)| {0,3}\[[^\]]+\]: *\S|\*\[[^\]]+\]:)")
SPEECH_TABLE_SEPARATOR_RE = re.compile(r"^[|:\- ]*-[|:\- ]*$")
SPEECH_TAG_RE = re.compile(
    r"^ {0,3}<(?P<close>/?)(?P<tag>[A-Za-z][A-Za-z0-9-]*)(?=[\s/>]|$)")
SPEECH_COMMENT_RE = re.compile(r"^ {0,3}<!--")
SPEECH_MARKDOWN_ATTR_RE = re.compile(r'\bmarkdown(?:=["\']?(?P<mode>\w+))?')
SPEECH_CLASS_RE = re.compile(r'\bclass="(?P<names>[^"]*)"')
SPEECH_IMAGE_RE = re.compile(
    r"\[?!\[(?P<alt>[^\]]*)\]\([^)]*\)(?:\]\([^)]*\))?(?:\{[^}]*\})?"
    r"|<img\b(?P<attrs>[^>]*)>")
SPEECH_ALT_RE = re.compile(r'\balt="(?P<alt>[^"]*)"')
SPEECH_ASCIINEMA_RE = re.compile(r"^<asciinema\b[^>]*>\s*(?:</asciinema>)?$")
SPEECH_POINTS_RE = re.compile(r"^(?P<number>\d+(?:[,.]\d+)?)\s*p\.?$")


class SpeechUnit(NamedTuple):
    """Ääneen luettava lohko. line ja column: merkin paikka sivun
    lopullisessa Markdownissa (sarkaimet laajennettuina, ks. speech_units);
    marker: merkin muoto (SPEECH_MARKERS); kind: lohkon laji; text: luettava
    teksti, josta leike tehdään."""
    line: int
    column: int
    marker: str
    kind: str
    text: str


class SpeechLine(NamedTuple):
    """Säiliön (luettelon kohta, laatikko, välilehti, lainaus) rivi ilman
    säiliön sisennystä: number on sivun rivi, offset sarake, josta text alkaa."""
    number: int
    offset: int
    text: str


def _indent(text: str) -> int:
    return len(text) - len(text.lstrip(" "))


def _dedent(line: SpeechLine, width: int = 4) -> SpeechLine:
    """Säiliön sisennys pois: enintään width välilyöntiä."""
    cut = min(width, _indent(line.text))
    return SpeechLine(line.number, line.offset + cut, line.text[cut:])


def _next_filled(lines: list[SpeechLine], index: int) -> int | None:
    """Ensimmäinen ei-tyhjä rivi indexistä alkaen."""
    while index < len(lines):
        if lines[index].text.strip():
            return index
        index += 1
    return None


def _fence_end(lines: list[SpeechLine], index: int, opening: re.Match) -> int | None:
    """Riviltä index alkavan aidan sulkeva rivi; None, jos aita jää auki."""
    fence = opening["fence"]
    for end in range(index + 1, len(lines)):
        closing = CODE_FENCE_RE.match(lines[end].text)
        if (closing and not closing["info"].strip() and closing["fence"][0] == fence[0]
                and len(closing["fence"]) >= len(fence)):
            return end
    return None


def _fence_markable(info: str) -> bool:
    """Saako aidan otsikkoon attribuutin (_mark_fence)? Tuntemattomat muodot
    ja muotoilijat, jotka eivät kirjoita attribuutteja, jäävät merkitsemättä."""
    info = info.strip()
    if info.lstrip(".") in SPEECH_CUSTOM_FENCES:
        return False
    return (not info or re.fullmatch(r"\.?[\w#.+-]+", info) is not None
            or (info.endswith("}") and "{" in info))


def _html_end(lines: list[SpeechLine], index: int, tag: str, markdown: bool) -> int:
    """Riviltä index alkavan HTML-elementin viimeinen rivi (sisäkkäiset
    samannimiset lasketaan). Markdown-sisällön aidat ohitetaan, koska niissä
    voi olla HTML-esimerkkejä. Sulkematon jatkuu loppuun."""
    opening = re.compile(rf"<{tag}(?=[\s>/])[^>]*?(?<!/)>", re.IGNORECASE)
    closing = re.compile(rf"</{tag}\s*>", re.IGNORECASE)
    depth = 0
    skip = index
    for number in range(index, len(lines)):
        text = lines[number].text
        if number < skip:
            continue
        if markdown and number > index and (fence := CODE_FENCE_RE.match(text)):
            end = _fence_end(lines, number, fence)
            if end is not None:
                skip = end + 1
                continue
        depth += len(opening.findall(text)) - len(closing.findall(text))
        if depth <= 0:
            return number
    return len(lines) - 1


def _strip_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)


def _heading_body(text: str) -> tuple[str, int]:
    """ATX-otsikon teksti ja merkin sarake: sulkevat risuaidat pois kuten
    Python-Markdownissa, ja merkki niiden eteen."""
    hashes = len(text) - len(text.lstrip("#"))
    body = re.match(r"^(?P<text>.*?)#*\s*$", text[hashes:])
    return body["text"], hashes + body.end("text")


def _starts_block(text: str) -> bool:
    """Alkaako luettelon kohdan teksti omalla lohkollaan (otsikko, lainaus,
    aita, sisäluettelo...)? Silloin merkki ei voi mennä tekstin eteen."""
    text = text.lstrip()
    tag = SPEECH_TAG_RE.match(text)
    return (text.startswith(("#", ">", "!!!", "???", "===", "$$", "|"))
            or CODE_FENCE_RE.match(text) is not None
            or SPEECH_LIST_RE.match(text) is not None
            or (tag is not None and tag["tag"].lower() in SPEECH_BLOCK_TAGS))


def _paragraph_speech(text: str) -> tuple[str, str]:
    """Kappaleen laji ja luettava teksti: pelkistä kuvista niiden
    vaihtoehtoiset tekstit, pelkästä nauhoituksesta ilmoitus."""
    text = text.strip()
    if SPEECH_ASCIINEMA_RE.match(text):
        return "nauhoitus", SPEECH_NOTICES["nauhoitus"]
    if text and not SPEECH_IMAGE_RE.sub("", text).strip():
        alts = []
        for image in SPEECH_IMAGE_RE.finditer(text):
            alt = image["alt"]
            if image["attrs"] is not None:
                found = SPEECH_ALT_RE.search(image["attrs"])
                alt = unescape(found["alt"]) if found else ""
            if alt.strip():
                alts.append(speech_line(f"Kuva: {alt.strip()}"))
        return "kuva", " ".join(alts)
    return "kappale", speech_line(text)


def _task_speech(head: str) -> str:
    """Tehtäväkortin tunnusrivi (task_head) luettavaksi."""
    parts = {name: _strip_tags(value).strip() for name, value in re.findall(
        r'<span class="task-(num|name|points)">(.*)?</span>', re.sub(
            r'(</span>)(?=<span class="task-)', r"\1\n", head))}
    text = f"Tehtävä {parts.get('num', '')}: {parts.get('name', '')}"
    if points := SPEECH_POINTS_RE.match(parts.get("points", "")):
        number = points["number"]
        text += f", {number} {'piste' if number == '1' else 'pistettä'}"
    return speech_line(text)


def tab_set_speech(labels: list[str]) -> tuple[str, dict[str, str]]:
    """Välilehtijoukon ilmoitus ja valinnan ilmoitus kullekin otsikolle.
    Otsikot perusmuodossa, jottei niitä tarvitse taivuttaa."""
    names = [speech_inline(label) for label in labels]
    listed = ", ".join(names[:-1]) + f" ja {names[-1]}" if len(names) > 1 else names[0]
    announcement = speech_line(f"{len(names)} välilehteä otsikoilla {listed}")
    return announcement, {label: speech_line(f"Luetaan välilehti {name}, mutta ei muita")
                          for label, name in zip(labels, names)}


class _SpeechScan:
    """speech_unitsin työtila: yksiköt ja proosavälilehtien otsikot
    järjestyksessä. top: ollaanko sivun tai md_in_html-lohkon ylätasolla,
    jossa rivin aloittava lohkotason tagi aloittaa HTML-lohkon (säiliöiden
    sisällä Python-Markdown ei tunnista sitä, koska rivi on sisennetty)."""

    def __init__(self) -> None:
        self.units: list[SpeechUnit] = []
        self.tab_sets: list[list[str]] = []

    def add(self, line: SpeechLine, column: int, marker: str, kind: str, text: str) -> None:
        """Yksikkö, jos luettavaa jää. column: sarake line.textissä."""
        if text:
            self.units.append(SpeechUnit(line.number, line.offset + column, marker, kind, text))

    def blocks(self, lines: list[SpeechLine], top: bool) -> None:
        index = 0
        while index < len(lines):
            index = self.block(lines, index, top)

    def block(self, lines: list[SpeechLine], index: int, top: bool) -> int:
        """Yksi lohko riviltä index. -> ensimmäinen rivi lohkon jälkeen."""
        text = lines[index].text
        if not text.strip():
            return index + 1
        if fence := CODE_FENCE_RE.match(text):
            return self.fence(lines, index, fence)
        if _indent(text) >= 4:
            # Sisennetty koodi: sitä ei voi merkitä, joten ei lueta.
            end = index
            while end < len(lines) and (not lines[end].text.strip()
                                        or _indent(lines[end].text) >= 4):
                end += 1
            return end
        if SPEECH_COMMENT_RE.match(text):
            end = index
            while end < len(lines) - 1 and "-->" not in lines[end].text:
                end += 1
            return end + 1
        tag = SPEECH_TAG_RE.match(text)
        if tag and tag["tag"].lower() in SPEECH_BLOCK_TAGS:
            if top:
                return self.html(lines, index, tag)
            return self.raw(lines, index)
        if SPEECH_ATX_RE.match(text):
            body, column = _heading_body(text)
            self.add(lines[index], column, "otsikko", "otsikko", speech_line(body))
            return index + 1
        if SPEECH_HR_RE.match(text):
            return index + 1
        if box := SPEECH_BOX_RE.match(text):
            return self.box(lines, index, box)
        if SPEECH_TAB_RE.match(text):
            return self.tabs(lines, index)
        if SPEECH_LIST_RE.match(text):
            return self.listing(lines, index)
        if SPEECH_QUOTE_RE.match(text):
            return self.quote(lines, index)
        if definition := SPEECH_DEFINITION_RE.match(text):
            return self.definition(lines, index, definition["note"] is not None)
        if index + 1 < len(lines) and self.is_table(text, lines[index + 1].text):
            return self.table(lines, index)
        return self.paragraph(lines, index, top)

    def ends_paragraph(self, text: str, top: bool) -> bool:
        """Katkaiseeko rivi kappaleen (Python-Markdown jakaa lohkon)?"""
        if not text.strip():
            return True
        tag = SPEECH_TAG_RE.match(text)
        return (CODE_FENCE_RE.match(text) is not None or SPEECH_ATX_RE.match(text) is not None
                or SPEECH_HR_RE.match(text) is not None or SPEECH_QUOTE_RE.match(text) is not None
                or SPEECH_BOX_RE.match(text) is not None or SPEECH_TAB_RE.match(text) is not None
                or (top and (SPEECH_COMMENT_RE.match(text) is not None or (
                    tag is not None and tag["tag"].lower() in SPEECH_BLOCK_TAGS))))

    def paragraph_end(self, lines: list[SpeechLine], index: int, top: bool) -> int:
        end = index + 1
        while end < len(lines) and not self.ends_paragraph(lines[end].text, top):
            end += 1
        return end

    def paragraph(self, lines: list[SpeechLine], index: int, top: bool) -> int:
        first = lines[index]
        if (index + 1 < len(lines) and SPEECH_SETEXT_RE.match(lines[index + 1].text)):
            self.add(first, len(first.text.rstrip()), "otsikko", "otsikko",
                     speech_line(first.text))
            return index + 2
        end = self.paragraph_end(lines, index, top)
        if first.text.lstrip().startswith("$$"):
            return end
        kind, text = _paragraph_speech(" ".join(line.text.strip() for line in lines[index:end]))
        self.add(first, _indent(first.text), "span", kind, text)
        return end

    def fence(self, lines: list[SpeechLine], index: int, opening: re.Match) -> int:
        end = _fence_end(lines, index, opening)
        if end is None:
            # Sulkematon aita ei ole Python-Markdownille aita; ei merkitä.
            return len(lines)
        if _fence_markable(opening["info"]):
            self.add(lines[index], opening.end("fence"), "aita", "koodi", SPEECH_NOTICES["koodi"])
        return end + 1

    def box(self, lines: list[SpeechLine], index: int, box: re.Match) -> int:
        """Admonition: otsikko (vain !!!, ei avattava ???) ja sisennetty sisältö."""
        if box["kind"] == "!!!" and box["title"]:
            self.add(lines[index], box.start("title"), "span", "laatikko",
                     speech_line(box["title"]))
        end = index + 1
        while end < len(lines) and (not lines[end].text.strip() or _indent(lines[end].text) >= 4):
            end += 1
        self.blocks([_dedent(line) for line in lines[index + 1:end]], top=False)
        return end

    def tabs(self, lines: list[SpeechLine], index: int) -> int:
        """Välilehtijoukko: peräkkäiset === -lohkot sisältöineen. Monitiedosto-
        lohkosta (convert_files) luetaan vain ilmoitus ensimmäisestä aidasta."""
        tabs: list[tuple[str, list[SpeechLine]]] = []
        while index < len(lines):
            tab = SPEECH_TAB_RE.match(lines[index].text)
            if not tab or (tabs and "!" in (tab["mode"] or "")):
                break
            end = index + 1
            while end < len(lines) and (not lines[end].text.strip()
                                        or _indent(lines[end].text) >= 4):
                end += 1
            tabs.append((tab["label"], [_dedent(line) for line in lines[index + 1:end]]))
            index = end
        bodies = [[line for line in body if line.text.strip()] for _, body in tabs]
        if all(body and "multifile" in (CODE_FENCE_RE.match(body[0].text) or {"info": ""})["info"]
               for body in bodies):
            self.blocks(tabs[0][1], top=False)
            return index
        if len(tabs) > 1:
            self.tab_sets.append([label for label, _ in tabs])
        for _, body in tabs:
            self.blocks(body, top=False)
        return index

    def listing(self, lines: list[SpeechLine], index: int) -> int:
        """Luettelo: kohdat ja niiden sisältö Python-Markdownin säännöin
        (ListProcessor.get_items ja ListIndentProcessor)."""
        items: list[tuple[SpeechLine, list[SpeechLine], list[SpeechLine]]] = []
        end = self.collect_items(lines, index, items)
        for first, more, children in items:
            item = SPEECH_LIST_RE.match(first.text)
            column = item.start("text")
            if task := SPEECH_TASK_RE.match(item["text"]):
                column += task.end()
            if not _starts_block(first.text[column:]):
                kind, text = _paragraph_speech(" ".join(
                    [first.text[column:], *(line.text.strip() for line in more)]))
                self.add(first, column, "span", "kohta" if kind == "kappale" else kind, text)
            self.blocks(children, top=False)
        return end

    @staticmethod
    def collect_items(lines: list[SpeechLine], index: int,
                      items: list[tuple[SpeechLine, list[SpeechLine], list[SpeechLine]]]) -> int:
        """Luettelon kohdat: (ensimmäinen rivi, jatkorivit, sisältö ilman
        sisennystä). -> ensimmäinen rivi luettelon jälkeen."""
        while index < len(lines):
            line = lines[index]
            text = line.text
            if not text.strip():
                ahead = _next_filled(lines, index)
                if ahead is None:
                    return len(lines)
                if _indent(lines[ahead].text) >= 4:
                    end = ahead
                    while end < len(lines) and (not lines[end].text.strip()
                                                or _indent(lines[end].text) >= 4):
                        end += 1
                    items[-1][2].extend(_dedent(child) for child in lines[index:end])
                    index = end
                    continue
                if (SPEECH_LIST_RE.match(lines[ahead].text)
                        and not SPEECH_HR_RE.match(lines[ahead].text)):
                    index = ahead
                    continue
                return index
            if items and (fence := CODE_FENCE_RE.match(text)):
                end = _fence_end(lines, index, fence)
                stop = len(lines) if end is None else end + 1
                items[-1][2].extend(_dedent(child) for child in lines[index:stop])
                index = stop
                continue
            if SPEECH_LIST_RE.match(text) and not SPEECH_HR_RE.match(text):
                items.append((line, [], []))
            elif items[-1][2] or SPEECH_NESTED_RE.match(text):
                items[-1][2].append(_dedent(line))
            else:
                items[-1][1].append(line)
            index += 1
        return index

    def quote(self, lines: list[SpeechLine], index: int) -> int:
        """Lainaus: ">" pois kultakin riviltä (laiskat jatkorivit sellaisinaan)."""
        end = index
        inner: list[SpeechLine] = []
        while end < len(lines) and lines[end].text.strip():
            line = lines[end]
            prefix = SPEECH_QUOTE_RE.match(line.text)
            cut = prefix.end() if prefix else 0
            inner.append(SpeechLine(line.number, line.offset + cut, line.text[cut:]))
            end += 1
        self.blocks(inner, top=False)
        return end

    def definition(self, lines: list[SpeechLine], index: int, note: bool) -> int:
        """Viite-, lyhenne- tai alaviitemäärittely: ei luettavaa. Alaviite
        jatkuu tyhjään riviin ja sen perässä sisennettyihin lohkoihin."""
        if not note:
            return index + 1
        end = index + 1
        while end < len(lines) and (lines[end].text.strip() or (
                (ahead := _next_filled(lines, end)) is not None
                and _indent(lines[ahead].text) >= 4)):
            end += 1
        return end

    @staticmethod
    def is_table(text: str, following: str) -> bool:
        """tables-laajennuksen ehto: otsikkorivi ja erotinrivi, jossa yhtä monta solua."""
        def cells(row: str) -> list[str]:
            row = row.strip()
            row = row[1:] if row.startswith("|") else row
            row = row[:-1] if row.endswith("|") and not row.endswith("\\|") else row
            return re.split(r"(?<!\\)\|", row)
        if "|" not in text or not SPEECH_TABLE_SEPARATOR_RE.match(following.strip()):
            return False
        header, separator = cells(text), cells(following)
        return len(header) == len(separator) and (len(header) > 1 or "|" in following)

    def table(self, lines: list[SpeechLine], index: int) -> int:
        first = lines[index]
        column = re.match(r"^ *\|? *", first.text).end()
        self.add(first, column, "span", "taulukko", SPEECH_NOTICES["taulukko"])
        end = index
        while end < len(lines) and lines[end].text.strip():
            end += 1
        return end

    def raw(self, lines: list[SpeechLine], index: int) -> int:
        """Säiliön sisällä rivin aloittava lohkotason tagi: Python-Markdown
        jättää kappaleen HTML:ksi. Siitä luetaan vain <summary>."""
        end = self.paragraph_end(lines, index, top=False)
        self.summary(lines[index:end])
        return end

    def summary(self, lines: list[SpeechLine]) -> int | None:
        """<summary> riveillä: avattavan kohdan ilmoitus. -> rivi, jolla se
        päättyy (indeksi lines-listassa), tai None."""
        for start, line in enumerate(lines):
            if (column := line.text.find("<summary")) < 0:
                continue
            end = start
            while end < len(lines) - 1 and "</summary>" not in lines[end].text:
                end += 1
            inner = " ".join(item.text for item in lines[start:end + 1])
            inner = inner[inner.find(">", column) + 1:].split("</summary>")[0]
            title = re.sub(r"^\s*#+\s*", "", _strip_tags(inner).strip())
            self.add(line, column + len("<summary"), "tagi", "avattava",
                     speech_line(f"Avattava kohta: {title}") if title.strip() else "")
            return end
        return None

    def html(self, lines: list[SpeechLine], index: int, tag: re.Match) -> int:
        """Ylätason HTML-lohko. Kirjan omista elementeistä ilmoitus, markdown-
        attribuutillisen (md_in_html) sisältö luetaan kuin sivu."""
        name = tag["tag"].lower()
        if tag["close"]:
            return index + 1
        text = lines[index].text
        opening = text[tag.start():text.find(">", tag.end()) + 1 or len(text)]
        markdown = SPEECH_MARKDOWN_ATTR_RE.search(opening)
        mode = markdown and (markdown["mode"] or "1")
        block = mode in ("1", "block") and name not in ("p", "summary", "li", "td", "th", "dt", "dd")
        end = _html_end(lines, index, name, block)
        classes = set((SPEECH_CLASS_RE.search(opening) or {"names": ""})["names"].split())
        column = tag.end("tag")
        kind = next((kind for kind, found in (
            ("ohje", "jyu-walk" in classes), ("visa", "jyu-visa" in classes),
            ("kaavio", bool(classes & {"svgbob", "jyu-mermaid"})),
            ("taulukko", name == "table"),
            ("video", name == "video")) if found), None)
        if kind:
            self.add(lines[index], column, "tagi", kind, SPEECH_NOTICES[kind])
        elif "task-head" in classes:
            self.add(lines[index], column, "tagi", "tehtava", _task_speech(text))
        elif block and "task-link" not in classes:
            content = lines[index + 1:end]
            if name == "details":
                summary = self.summary(lines[index:end])
                if summary is not None:
                    content = lines[index + summary + 1:end]
            self.blocks(content, top=True)
        return end + 1


def speech_units(text: str) -> tuple[list[SpeechUnit], list[list[str]]]:
    """Sivun lopullisesta Markdownista luettavat lohkot järjestyksessä ja
    proosavälilehtijoukkojen otsikot. -> (yksiköt, joukot).

    Sarkaimet laajennetaan neljään kuten Python-Markdownin
    NormalizeWhitespace, joten rivit ja sarakkeet viittaavat laajennettuun
    tekstiin (mark_speech kirjoittaa sen). Front matter ohitetaan.
    """
    lines = [SpeechLine(number, 0, line)
             for number, line in enumerate(text.expandtabs(4).split("\n"))]
    start = 0
    if lines and lines[0].text.rstrip() == "---":
        start = next((number + 1 for number, line in enumerate(lines[1:], 1)
                      if line.text.rstrip() in ("---", "...")), 0)
    scan = _SpeechScan()
    scan.blocks(lines[start:], top=True)
    return scan.units, scan.tab_sets


# Sanat, jotka puheääni sanoo väärin (C# "see risuaita"), ja miten ne
# sanotaan. Kirjainkoko ratkaisee (TIM mutta ei Timer). Vain puhepalvelulle:
# sivun ja --tekstin teksti pysyy ennallaan, ja leike vaihtuu vain, jos sen
# tekstissä on jokin näistä.
SPEECH_SAYINGS = {
    "C#": "see sharp",
    ".NET": "dotnet",
    "Rider": "raider",
    "rider": "raider",
    "Riderin": "raiderin",
    "riderin": "raiderin",
    "Riderissa": "raiderissa",
    "riderissa": "raiderissa",
    "Riderista": "raiderista",
    "riderista": "raiderista",
    "macOS": "mäk oo äs",
    "TIM": "Tim",  # sanana, ei kirjain kerrallaan
    "ohj1": "oo hoo jii yksi",
    "Ohj1": "oo hoo jii yksi",
    "IDE": "ide",  # sanana: kirjaimina ääni sanoi "i" tai "ie"
    "engl.": "englanniksi",  # ääni ei avaa lyhennettä
    # Javan sanat lausuttuina, ei suomen kirjainäänteillä ("tru-e"). Ei mainia:
    # kirjoitettu pääte tekisi mainittua-sanasta "meinittua".
    "Java": "jaava",
    "private": "praivet",
    "boolean": "buulean",
    "double": "dabl",
    "true": "truu",
    "false": "fols",
    "new": "njuu",
    "println": "print lain",
    "ArrayList": "eirei list",
    "<=": "pienempi tai yhtä suuri kuin",
    # Vakioiden nimet sanoina, ei kirjain kerrallaan (vrt. TIM).
    "NIMI": "nimi",
    "VIRTA": "virta",
    "SALASANA": "salasana",
    "KOKO": "koko",
    "DL-BONUS": "DL-bonus",
}
# Kaksoispisteellä taivutetun vartalo, jos se ei ole sanottu + i kuten
# lainasanoissa (C#:n -> see sharpin): kirjaimen nimeen tulee ä (äsässä).
SPEECH_STEMS = {"macOS": "mäk oo äsä"}
SPEECH_SAYING_RE = re.compile(
    r"(?<!\w)(?P<word>" + "|".join(map(re.escape, sorted(SPEECH_SAYINGS, key=len, reverse=True)))
    + r")(?::(?P<ending>\w+)|(?<=[^\W\d])(?P<attached>[a-zäö]+))?(?!\w)")
SPEECH_BACK_VOWELS = str.maketrans("äöy", "aou")
SPEECH_FRONT_VOWELS = str.maketrans("aou", "äöy")


def speech_say(text: str) -> str:
    """SPEECH_SAYINGSin sanat niin kuin ne sanotaan. Suoraan kirjoitettu pääte
    liitetään sellaisenaan (Riderissa -> raiderissa), kaksoispisteellä
    taivutettuun vartalo (SPEECH_STEMS) ja pääte vokaalisointuun: C#:n -> see
    sharpin, C#:ia -> see sharpia, macOS:lla -> mäk oo äsällä."""
    def say(match: re.Match) -> str:
        word, ending = match["word"], match["ending"]
        said = SPEECH_SAYINGS[word]
        if not ending:
            return said + (match["attached"] or "")
        stem = SPEECH_STEMS.get(word) or (said if said[-1] in "aeiouyäö" else f"{said}i")
        if stem.endswith("i") and ending.startswith("i"):
            ending = ending[1:]
        back = re.search(r"[aou]", stem.split()[-1]) is not None
        return stem + ending.translate(SPEECH_BACK_VOWELS if back else SPEECH_FRONT_VOWELS)
    return SPEECH_SAYING_RE.sub(say, text)


def ssml(text: str, voice: str | None = None) -> str:
    """Luettava teksti SSML:ksi: jokainen rivi omana kappaleenaan (tauko),
    sanat niin kuin ne sanotaan (speech_say)."""
    paragraphs = "".join(f"<p>{escape(speech_say(line), quote=False)}</p>"
                         for line in text.split("\n") if line)
    return ('<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis"'
            f' xml:lang="fi-FI"><voice name="{escape(voice or SPEECH_VOICE)}">'
            f"{paragraphs}</voice></speak>")


def speech_clip(text: str, voice: str | None = None) -> str:
    """Leikkeen tunniste ja tiedostonimi: tiiviste siitä, mitä puhepalvelulle
    lähetetään. Äänen, muodon tai SSML:n muutos vaihtaa tunnisteen itsestään,
    ja sama teksti eri sivuilla on yksi leike."""
    request = f"{SPEECH_FORMAT}\n{ssml(text, voice)}"
    return hashlib.sha256(request.encode("utf-8")).hexdigest()[:16]


def speech_texts(text: str) -> list[str]:
    """Kaikki sivun lopullisen Markdownin leikkeiden tekstit (puhe.py)."""
    units, tab_sets = speech_units(text)
    texts = [unit.text for unit in units]
    for labels in tab_sets:
        announcement, choices = tab_set_speech(labels)
        texts += [announcement, *choices.values()]
    return texts


def available_clips() -> set[str] | None:
    """Äänivaraston leikkeet; None, jos varastoa ei ole."""
    if not SPEECH_STORE.is_dir():
        return None
    return {clip.stem for clip in SPEECH_STORE.glob("*.mp3")}


def _mark_span(line: str, column: int, clip: str) -> str:
    return line[:column] + SPEECH_SPAN.format(clip=clip) + line[column:]


def _mark_heading(line: str, column: int, clip: str) -> str:
    """Otsikon attribuuttilistaan (attr_list), olemassa olevaan tai uuteen."""
    head, tail = line[:column].rstrip(), line[column:]
    if re.search(r" +\{:?[ ]*[^} \n][^\n]*\}$", head):
        return f'{head[:-1].rstrip()} data-puhe="{clip}" }}{tail}'
    return f'{head} {{ data-puhe="{clip}" }}{tail}'


def _mark_fence(line: str, column: int, clip: str) -> str:
    """Aidan otsikkoon (pymdownx.superfences), kieli luokaksi tarvittaessa."""
    head, info = line[:column], line[column:].strip()
    attribute = f'data-puhe="{clip}"'
    if info.endswith("}"):
        brace = line.rindex("}")
        return f"{line[:brace].rstrip()} {attribute} {line[brace:]}"
    language = f".{info.lstrip('.')} " if info else ""
    return f"{head}{{ {language}{attribute} }}"


def _mark_tag(line: str, column: int, clip: str) -> str:
    return f'{line[:column]} data-puhe="{clip}"{line[column:]}'


SPEECH_MARKERS = {"span": _mark_span, "otsikko": _mark_heading,
                  "aita": _mark_fence, "tagi": _mark_tag}


def mark_speech(text: str, clips: set[str]) -> tuple[str, list[str], list[str]]:
    """Merkit lohkoihin, joiden leike on olemassa, ja välilehtijoukkojen
    ilmoitukset sivun loppuun. -> (teksti, käytetyt leikkeet, puuttuvien tekstit).

    Ilmoitusleikkeet menevät <script type="application/json" id="jyu-puhe">
    -lohkoon: {"valilehdet": {"Windows\\nmacOS": {"joukko": leike, "valinta":
    {"Windows": leike, ...}}}}. Avain on joukon otsikot rivinvaihdoin, jotta
    puhe.js löytää joukon sen välilehtien otsikoista.
    """
    units, tab_sets = speech_units(text)
    lines = text.expandtabs(4).split("\n")
    marked = [(unit, speech_clip(unit.text)) for unit in units]
    used = [clip for _, clip in marked if clip in clips]
    missing = [unit.text for unit, clip in marked if clip not in clips]
    # Lopusta alkuun, jotta saman rivin aiemmat sarakkeet pysyvät paikallaan.
    for unit, clip in sorted(marked, key=lambda pair: pair[0][:2], reverse=True):
        if clip in clips:
            lines[unit.line] = SPEECH_MARKERS[unit.marker](lines[unit.line], unit.column, clip)
    sets: dict[str, dict] = {}
    for labels in tab_sets:
        announcement, choices = tab_set_speech(labels)
        entry: dict = {}
        for label, spoken in [(None, announcement), *choices.items()]:
            clip = speech_clip(spoken)
            if clip not in clips:
                missing.append(spoken)
            elif label is None:
                entry["joukko"] = clip
            else:
                entry.setdefault("valinta", {})[label] = clip
            used += [clip] if clip in clips else []
        sets["\n".join(labels)] = entry
    if sets:
        data = json.dumps({"valilehdet": sets}, ensure_ascii=False).replace("<", "\\u003c")
        while lines and not lines[-1].strip():
            lines.pop()
        lines += ["", f'<script type="application/json" id="jyu-puhe">{data}</script>', ""]
    return "\n".join(lines), used, missing


def split_files(body: list[str]) -> list[tuple[str, list[str]]]:
    """Koodiaidan rivit -> [(tiedostonimi, rivit)] FILE-merkintöjen mukaan.

    Merkintöjen ulkopuoliset rivit putoavat pois; convert_files tarkistaa ne
    ennen kutsua. Tyhjä lista = lohkossa ei ole merkintöjä.
    """
    files: list[tuple[str, list[str]]] = []
    name: str | None = None
    content: list[str] = []
    for line in body:
        begin = FILE_BEGIN_RE.match(line)
        if begin:
            if name is not None:
                files.append((name, content))
            name, content = begin["name"], []
        elif FILE_END_RE.match(line):
            if name is not None:
                files.append((name, content))
            name, content = None, []
        elif name is not None:
            content.append(line)
    if name is not None:
        files.append((name, content))
    return files


def convert_files(text: str) -> tuple[str, int, int, int, int]:
    """mdBookin monitiedostolohkot -> pymdownx.tabbed.
    -> (teksti, lohkot, tiedostot, piilorivitiedostot, korostustiedostot).

    Jokainen tiedosto omaksi välilehdekseen ja aidakseen, jossa alkuperäiset
    määreet ja lisäksi "multifile": ajonappi lähettää tällaisen joukon yhtenä
    ohjelmana, eikä sitä voi päätellä DOM:sta. Piilorivit ja korostukset
    käsitellään tässä, koska rivinumerot lasketaan tiedoston omasta aidasta;
    convert_fences ei enää koske valmiisiin aitoihin (fence_language).
    """
    lines = text.split("\n")
    out: list[str] = []
    blocks = files = 0
    index = 0
    hidden_files = marked_files = 0
    while index < len(lines):
        fence = CODE_FENCE_RE.match(lines[index])
        if not fence:
            out.append(lines[index])
            index += 1
            continue
        marker = fence["fence"]
        close_re = re.compile(rf"^{marker[0]}{{{len(marker)},}}\s*$")
        end = index + 1
        while end < len(lines) and not close_re.match(lines[end]):
            end += 1
        body = lines[index + 1:end]
        begins = [i for i, line in enumerate(body) if FILE_BEGIN_RE.match(line)]
        # Sulkematon aita, tavallinen lohko tai koodia ennen ensimmäistä
        # merkintää: jätetään ennalleen. Viimeisestä varoitetaan, koska
        # split_files pudottaisi rivit hiljaa pois.
        if begins and any(line.strip() for line in body[:begins[0]]):
            print(f"varoitus: koodia ennen ensimmäistä // FILE: -merkintää, "
                  f"lohko jätetään ennalleen: {lines[index]}", file=sys.stderr)
        if end >= len(lines) or not begins or any(line.strip()
                                                  for line in body[:begins[0]]):
            out.extend(lines[index:end + 1])
            index = end + 1
            continue
        language = fence_language(fence["info"])
        if out and out[-1].strip():
            out.append("")
        blocks += 1
        for name, content in split_files(body):
            files += 1
            content, colors = mark_highlights(content, language)
            content, hidden = hide_lines(content, language)
            hidden_files += bool(hidden)
            marked_files += bool(colors)
            info = fence_info(fence["info"] + ",multifile", hidden, colors)
            out.append(f'=== "{name}"')
            out.append("")
            out.extend(indent_block([f"{marker}{info}", *content, marker]))
            out.append("")
        index = end + 1
    return "\n".join(out), blocks, files, hidden_files, marked_files


def convert_tabs(text: str) -> tuple[str, int, set[str]]:
    """mdBookin #tab/-lohkot -> pymdownx.tabbed. -> (teksti, joukkoja, otsikot).

    Saman tunnuksen välilehdet saavat saman otsikon ensimmäisen esiintymän
    mukaan, koska Material yhdistää sivun välilehtijoukot otsikkotekstistä,
    mdBook tunnuksesta.
    """
    lines = text.split("\n")
    labels: dict[str, str] = {}
    out: list[str] = []
    sets = 0
    index = 0
    while index < len(lines):
        if not TAB_HEADING_RE.match(lines[index]):
            out.append(lines[index])
            index += 1
            continue
        sections, index = read_tab_set(lines, index)
        # Tyhjä rivi joukon eteen, jottei edellinen kappale liimaudu siihen.
        if out and out[-1].strip():
            out.append("")
        sets += 1
        for tab_id, label, body in sections:
            out.append(f'=== "{labels.setdefault(tab_id, label)}"')
            out.append("")
            out.extend(indent_block(body))
            out.append("")
    return "\n".join(out), sets, set(labels.values())


def sync_docs() -> set[Path]:
    """Kopioi ../src:n muut kuin Markdown-tiedostot docs/:iin. -> edellisen ajon jäänteet.

    docs/:ia ei tyhjennetä eikä hakemistoja poisteta: `zensical serve` vahtii
    hakemistoa ja kaatuu tai unohtaa docs/assets/:n, jos tiedosto katoaa kesken
    rakennuksen. Siksi kaikki kirjoitetaan suoraan lopulliseen paikkaansa,
    vain muuttunut (copy_if_changed), ja
    Markdown-sivut jätetään mainille kirjoitettaviksi muunnettuina. Jäänteet
    (poistetut sivut) main poistaa vasta lopuksi.
    """
    before = ({f for f in DOCS.rglob("*") if f.is_file()}
              if DOCS.exists() else set())
    fresh: set[Path] = set()
    for file in SRC.rglob("*"):
        if not file.is_file():
            continue
        relative = file.relative_to(SRC).as_posix()
        if file.suffix == ".md" and not is_page(relative):
            continue
        target = DOCS / relative
        fresh.add(target)
        if file.suffix == ".md":
            # Sivun kirjoittaa main muunnettuna, ks. write_if_changed.
            continue
        copy_if_changed(file, target)
    fresh |= {DOCS / "assets" / f.relative_to(ASSETS)
              for f in ASSETS.rglob("*") if f.is_file()}
    if PLANTUML_DIR.is_dir():
        fresh |= {DOCS / "assets" / "plantuml" / f.name
                  for f in PLANTUML_DIR.iterdir() if f.is_file()}
    fresh.add(DOCS / PRINT_PAGE)
    return before - fresh


def copy_if_changed(source: Path, target: Path) -> None:
    """Kopioi vain jos kohde puuttuu tai eroaa lähteestä, ks. write_if_changed.

    Vertailu koosta ja ajasta, ei sisällöstä: copy2 kopioi ajan lähteestä, ja
    sisällön lukeminen maksaisi koko puun joka ajolla.
    """
    if target.is_file() and filecmp.cmp(source, target, shallow=True):
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def write_if_changed(path: Path, text: str) -> None:
    """Kirjoita vain jos sisältö muuttuu: turha kirjoitus on vahdille tapahtuma.

    `zensical serve` lataa sivun selaimessa uudelleen jokaisesta docs/:n
    muutoksesta, ja nav.yml:n muutoksesta se rakentaa koko sivuston alusta.
    """
    if path.is_file() and path.read_text(encoding="utf-8") == text:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def copy_clips(clips: set[str]) -> set[Path]:
    """Sivuston käyttämät leikkeet varastosta docs/:iin ja niiden luettelo.
    -> kirjoitetut polut (ne eivät ole jäänteitä, ks. sync_docs)."""
    if not clips:
        return set()
    folder = DOCS / SPEECH_ASSETS
    written = {folder / SPEECH_INDEX}
    for clip in sorted(clips):
        copy_if_changed(SPEECH_STORE / f"{clip}.mp3", folder / f"{clip}.mp3")
        written.add(folder / f"{clip}.mp3")
    write_if_changed(folder / SPEECH_INDEX, "".join(f"{clip}\n" for clip in sorted(clips)))
    return written


class PageResult(NamedTuple):
    """convert_pagen tulos: sivun lopullinen Markdown ja mainin koottavat joukot.
    clips: vaiheittaisen ohjeen käyttämät leikkeet, silent_steps: vaiheet,
    joiden leike puuttuu."""
    text: str
    labels: set[str]
    unknown_icons: set[str]
    diagrams: set[str]
    drawings: set[str]
    graphs: set[str]
    unknown_alerts: set[str]
    clips: set[str]
    silent_steps: list[str]


def convert_page(origin: Path, source_path: str, clips: set[str] | None = None) -> PageResult:
    """Lähdepuun sivu muunnosten läpi lopulliseksi Markdowniksi, vielä ilman
    ääneenluvun merkkejä (mark_speech). puhe.py paloittelee saman tekstin.
    Kaaviot haetaan ja piirretään tarvittaessa (cache/) kuten mainissa.
    clips: äänivaraston leikkeet vaiheittaisen ohjeen äänille."""
    page = DOCS / source_path
    source = origin.read_text(encoding="utf-8")
    # Järjestys: sisällytykset ensin, jotta muut muunnokset näkevät
    # lopullisen tekstin (sisällytyksissä on koodiaitoja ja
    # FILE-merkintöjä). Ankkurit ennen kuin mikään muunnos kirjoittaa
    # omia linkkejään tai SVG-tunnuksiaan. Muunnosten laskurit jäävät
    # käyttämättä.
    # Sisennetyt otsikot ensin, jotta convert_anchors tunnistaa ne
    # otsikoiksi.
    converted, _ = dedent_headings(source)
    converted, _ = convert_includes(converted, origin)
    converted, _, _ = convert_anchors(converted)
    # Visat ennen aitoja: kysymyksen tunniste lasketaan lähteen tekstistä.
    converted, _ = convert_quizzes(converted, source_path)
    # Monitiedostolohkot ennen convert_fencesiä: convert_fences ei koske
    # niiden valmiisiin aitoihin. Aidat, kaaviot, alertit ja tehtäväkortit
    # ennen convert_tabsia, koska se sisentää välilehden sisällön, eikä
    # sisennettyä aitaa, ">":tä tai HTML-lohkoa enää tunnisteta.
    converted, *_ = convert_files(converted)
    converted, *_ = convert_fences(converted)
    converted, _, page_used = convert_plantuml(converted, page)
    converted, _, page_unknown = convert_alerts(converted)
    # details ja drop_breaks: paikalla ei ole väliä.
    converted, *_ = convert_details(converted)
    converted, _ = drop_breaks(converted)
    # Divit ennen tehtäväkortteja (näkee vain lähteen divit) ja ennen
    # svgbobia (kääre ei saa markdown="1":tä).
    converted, _ = convert_divs(converted)
    converted, _, page_art = convert_svgbob(converted, source_path)
    converted, _, page_graphs = convert_mermaid(converted)
    # Tehtäväkortit ennen bonusmerkkejä (task_head lukee kortin tagin itse).
    converted, _ = convert_tasks(converted)
    # Vaiheittainen ohje ennen convert_tabsia kuten tehtäväkortit: tagit
    # nostetaan sarakkeeseen 0, eikä sisennettyä HTML-lohkoa tunnisteta.
    # Äänet lähteestä kuten puhe.py, ei muunnetusta tekstistä.
    audio, silent = walkthrough_audio(source, clips or set())
    converted, _ = convert_walkthroughs(converted, source_path, audio)
    converted, _ = convert_bonus_marks(converted)
    converted, _, _, page_unknown_icons = convert_icons(converted)
    converted, _, page_labels = convert_tabs(converted)
    # Animaatiot välilehtien jälkeen, ks. convert_animations.
    converted, _ = convert_animations(converted, source_path)
    return PageResult(converted, page_labels, page_unknown_icons, page_used, page_art,
                      page_graphs, page_unknown, set(audio.values()), silent)


def report_diagrams(pruned: dict[str, int]) -> None:
    """Rivi piirtäjää kohti, jos kaavioita piirrettiin tai poistettiin: ne ovat
    kirjan versionhallinnassa (cache/), joten muutos pitää committoida."""
    folders = {"plantuml": PLANTUML_DIR, "svgbob": SVGBOB_DIR, "mermaid": MERMAID_DIR}
    for tool, folder in folders.items():
        drawn, removed = RENDERED[tool], pruned.get(tool, 0)
        if not drawn and not removed:
            continue
        count = lambda n: f"{n} kaavio{'ta' if n != 1 else ''}"  # noqa: E731
        parts = [f"piirretty {count(drawn)}"] if drawn else []
        parts += [f"poistettu {count(removed)}"] if removed else []
        print(f"{tool}: {', '.join(parts)} ({repo_relative(folder)}/"
              " on versionhallinnassa, committoi)", file=sys.stderr)


def main(strict: bool = False) -> int:
    global STRICT
    STRICT = strict
    if not (BOOK / CONFIG_NAME).is_file():
        print(f"{CONFIG_NAME} puuttuu: aja kirjan hakemistossa (esim. zensical/),"
              f" jossa se on; etsitty: {Path.cwd()}, {TOOL.parent}", file=sys.stderr)
        return 1
    if not SRC.is_dir():
        print(f"lähdepuu puuttuu: {SRC}", file=sys.stderr)
        return 1
    FAILED.clear()
    RENDERED.clear()
    stale = sync_docs()
    used_diagrams: set[str] = set()
    used_drawings: set[str] = set()
    used_graphs: set[str] = set()
    tab_labels: set[str] = set()
    unknown_alerts: set[str] = set()
    unknown_icons: set[str] = set()
    clips = available_clips()
    used_clips: set[str] = set()
    silent: dict[str, int] = {}
    silent_steps: dict[str, list[str]] = {}
    # Silmukka käy lähdepuun eikä docs/:n, jottei sivua tarvitse ensin kopioida
    # raakana paikalleen (turha kirjoitus on vahdille tapahtuma).
    for origin in sorted(SRC.rglob("*.md")):
        source_path = origin.relative_to(SRC).as_posix()
        if not is_page(source_path):
            continue
        page = convert_page(origin, source_path, clips)
        converted = page.text
        used_clips |= page.clips
        if page.silent_steps:
            silent_steps[source_path] = page.silent_steps
        if is_speech_page(source_path):
            converted, page_clips, missing = mark_speech(converted, clips or set())
            used_clips.update(page_clips)
            if missing:
                silent[source_path] = len(missing)
        write_if_changed(DOCS / source_path, converted)
        tab_labels |= page.labels
        unknown_icons |= page.unknown_icons
        used_diagrams |= page.diagrams
        used_drawings |= page.drawings
        used_graphs |= page.graphs
        unknown_alerts |= page.unknown_alerts
    for asset in ASSETS.rglob("*"):
        if asset.is_file():
            copy_if_changed(asset, DOCS / "assets" / asset.relative_to(ASSETS))
    # Luokkakaaviot sivujen jälkeen: convert_plantuml haki juuri puuttuvat.
    if PLANTUML_DIR.is_dir():
        for diagram in PLANTUML_DIR.iterdir():
            if diagram.is_file():
                copy_if_changed(diagram, DOCS / "assets" / "plantuml" / diagram.name)
    nav = build_nav()
    write_if_changed(BOOK / "nav.yml", build_base() + nav + build_extra(tab_labels))
    write_if_changed(DOCS / PRINT_PAGE, build_print_page(nav))
    pruned = {
        "plantuml": prune_diagrams(PLANTUML_DIR, used_diagrams, "plantuml" not in FAILED),
        "svgbob": prune_diagrams(SVGBOB_DIR, used_drawings, "svgbob" not in FAILED),
        "mermaid": prune_diagrams(MERMAID_DIR, used_graphs, "mermaid" not in FAILED),
    }
    report_diagrams(pruned)
    stale -= copy_clips(used_clips)
    # Jäänteet viimeisenä, kun kaikki muu on jo paikallaan (ks. sync_docs).
    for file in sorted(stale):
        file.unlink()
    if unknown_icons:
        print(f"varoitus: tuntematon ikoni: {', '.join(sorted(unknown_icons))}",
              file=sys.stderr)
    if unknown_alerts:
        print("varoitus: tuntematon alertin tunnus: "
              f"{', '.join(sorted(unknown_alerts))}", file=sys.stderr)
    # Ilman varastoa jokaisen ääneen luettavan vaiheen leike puuttuu, joten
    # silent_steps kertoo, tarvitaanko varastoa vaiheittaisille ohjeille.
    no_store = clips is None and bool(SPEECH_PAGES or silent_steps)
    if no_store:
        print(f"{'virhe' if strict else 'varoitus'}: äänivarasto puuttuu"
              f" ({repo_relative(SPEECH_STORE)}), sivut ovat äänettömiä;"
              " aja ./run.sh puhe", file=sys.stderr)
    else:
        if silent:
            names = ", ".join(sorted(silent)[:5]) + (", ..." if len(silent) > 5 else "")
            print(f"varoitus: {sum(silent.values())} kappaleen ääni puuttuu ({names});"
                  " aja ./run.sh puhe", file=sys.stderr)
        for source_path, scenes in silent_steps.items():
            names = ", ".join(scenes[:5]) + (", ..." if len(scenes) > 5 else "")
            print(f"varoitus: {source_path}: {len(scenes)} vaiheen ääni puuttuu ({names});"
                  f" aja ./run.sh puhe ../src/{source_path}", file=sys.stderr)
    # --strict: julkaisussa puuttuva kaavio on virhe, ei varoitus. Paikallisesti
    # pehmeä riippuvuus säilyy, ks. svgbob_svg.
    if strict and FAILED:
        print(f"virhe: kaavioita jäi piirtämättä ({', '.join(sorted(FAILED))});"
              " aja muunnos paikallisesti ja committoi syntyneet kuvat",
              file=sys.stderr)
        return 1
    # Myös äänivaraston puuttuminen: julkaisu kadottaisi äänet hiljaa.
    return 1 if strict and no_store else 0


# --- Vahti ------------------------------------------------------------------

# Kyselyväli sekunteina; tiheämpi ei näkyisi kierrosajassa, muunnos on hitaampi.
WATCH_INTERVAL = 0.3


def watch_paths() -> tuple[Path, ...]:
    """Vahdittavat puut: lähdepuu ja assetit (nekin päätyvät sivustolle vain
    tätä kautta). Funktio eikä vakio, jotta testien vaihtama SRC näkyy."""
    return (SRC, ASSETS)


def snapshot() -> dict[str, int]:
    """Vahdittavien tiedostojen polut ja muokkausajat.

    Kysely eikä inotify, koska inotify ei saa tapahtumia 9p-liitoksen takaa
    (WSL, README: Käyttö kirjassa). os.scandir on rglobia nopeampi ja st_mtime_ns ei
    vaadi tiedostojen lukemista.
    """
    state: dict[str, int] = {}
    stack = [str(path) for path in watch_paths() if path.is_dir()]
    while stack:
        try:
            with os.scandir(stack.pop()) as entries:
                for entry in entries:
                    if entry.is_dir(follow_symlinks=False):
                        stack.append(entry.path)
                    elif entry.is_file(follow_symlinks=False):
                        state[entry.path] = entry.stat().st_mtime_ns
        except OSError:
            # Tiedosto katosi kesken kyselyn (editorin tallennus); seuraava
            # kysely näkee lopputilan.
            continue
    return state


def changed_files(before: dict[str, int], after: dict[str, int]) -> list[str]:
    """Muuttuneet, lisätyt ja poistetut tiedostot."""
    names = set(before) ^ set(after)
    names |= {name for name in before.keys() & after.keys()
              if before[name] != after[name]}
    return sorted(names)


def repo_relative(path: str | Path) -> str:
    """Polku repon juuresta lukien; juuren ulkopuolinen sellaisenaan."""
    try:
        return Path(path).relative_to(BOOK.parent).as_posix()
    except ValueError:
        return str(path)


def watch_label(changed: list[str]) -> str:
    """Muuttuneet tiedostot yhden rivin nimeksi: polku ja monelleko muulle."""
    name = repo_relative(changed[0])
    return name if len(changed) == 1 else f"{name} (+{len(changed) - 1})"


def watch() -> int:
    """Aja muunnos aina kun lähdepuu tai assetit muuttuvat. -> paluuarvo.

    Ensimmäistä muunnosta ei tehdä: run.sh ajaa sen ennen vahtia, jotta
    `zensical serve` näkee valmiin docs/:n heti. Käynnistyksestä ei tulosteta
    mitään: run.sh kertoo osoitteen ja Ctrl-C:n, ja jokainen muunnos tulostaa
    oman rivinsä.
    """
    state = snapshot()
    try:
        while True:
            time.sleep(WATCH_INTERVAL)
            fresh = snapshot()
            if fresh == state:
                continue
            # Odota, että tallennus on ohi: yksi tallennus tai `git checkout`
            # näkyy monena muutoksena.
            while True:
                time.sleep(WATCH_INTERVAL)
                settled = snapshot()
                if settled == fresh:
                    break
                fresh = settled
            changed = changed_files(state, fresh)
            started = time.monotonic()
            try:
                with only_one_run():
                    status = main()
            except Exception:
                # Virhe ei saa tappaa vahtia; se näkyy ja seuraava tallennus
                # yrittää uudelleen.
                traceback.print_exc()
                status = 1
            elapsed = f"{time.monotonic() - started:.1f}".replace(".", ",")
            print(f"{time.strftime('%H:%M:%S')} {watch_label(changed)} -> "
                  + (f"muunnettu {elapsed} s" if status == 0
                     else "muunnos epäonnistui"), flush=True)
            # Ajon aikana tehty tallennus näkyy seuraavalla kierroksella:
            # muunnos ei itse kirjoita vahdittuihin puihin.
            state = fresh
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    arguments = sys.argv[1:]
    if arguments == ["--watch"]:
        raise SystemExit(watch())
    if arguments not in ([], ["--strict"]):
        print(f"käyttö: {Path(__file__).name} [--watch | --strict]",
              file=sys.stderr)
        raise SystemExit(2)
    with only_one_run():
        raise SystemExit(main(strict=bool(arguments)))
