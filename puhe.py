"""Ääneenluvun äänet pilvipalvelun puhesynteesillä (Azure Speech).

    ./run.sh puhe                        # kaikki: valitut sivut ja vaiheittaiset ohjeet
    ./run.sh puhe ../src/tyokalut.md     # vain annetut sivut
    ./run.sh puhe --teksti               # luettavat tekstit ja hinta-arvio, ei ääniä
    ./run.sh puhe --ei-julkaisua         # äänet varastoon, mutta ei committia eikä pushia

Koko sivun ääneenluku (kirja.toml: [puhe] sivut): convert.py paloittelee
sivun lopullisen Markdownin lohkoiksi (speech_units), ja jokaisesta lohkosta
tulee oma leike äänivarastoon (convert.SPEECH_STORE): <tunniste>.mp3, jossa
tunniste on convert.speech_clip. Leike tehdään vain, jos sitä ei vielä ole,
joten korjauksen jälkeen syntetisoidaan vain muuttunut kappale. Varasto on
erillisen repon (kirja.toml: [puhe] repo) klooni, koska äänet kasvattaisivat
kirjan repoa; ajo kloonaa sen tarvittaessa, ja uudet leikkeet committoidaan
ja pushataan sinne heti, jotta seuraava julkaisu (pages.yml) saa ne.

Vaiheittainen ohje: sivun <walkthrough scenes="..." audio="kansio"> kertoo
kansion (lähteen sivun hakemistosta). Jokaisesta vaiheesta tulee sinne
<kohtaus>.mp3, ja puhe.json muistaa, millä äänellä ja mistä tekstistä
(tiiviste) kukin on tehty. Luettava teksti on convert.py:n walkthrough_speech:
sama, josta käännös tarkistaa, onko ääni ajan tasalla.

Avain ja alue ympäristömuuttujista AZURE_SPEECH_KEY ja AZURE_SPEECH_REGION
(Azure-portaalissa Speech-resurssin Keys and Endpoint -sivulta). Avainta ei
tallenneta mihinkään.
"""

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path

import convert

VOICE = convert.SPEECH_VOICE
FORMAT = convert.SPEECH_FORMAT
ssml = convert.ssml

# Hinta-arvio --tekstille: Azuren neuroäänet noin 15 dollaria miljoonalta
# merkiltä (tarkista hinnasto; ilmaistaso 0,5 miljoonaa merkkiä kuukaudessa).
PRICE_PER_MILLION = 15

# MP3:n koko merkkiä kohden FORMATilla, mitattu git-ht-ohjeen äänistä.
BYTES_PER_CHARACTER = 475


def azure(document: str) -> bytes:
    """SSML-dokumentti Azure Speechin REST-rajapinnalla MP3:ksi."""
    key = os.environ.get("AZURE_SPEECH_KEY")
    region = os.environ.get("AZURE_SPEECH_REGION")
    if not key or not region:
        raise SystemExit("aseta ympäristömuuttujat AZURE_SPEECH_KEY ja AZURE_SPEECH_REGION "
                         "(Azure-portaali: Speech-resurssi, Keys and Endpoint)")
    request = urllib.request.Request(
        f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1",
        data=document.encode("utf-8"),
        headers={
            "Ocp-Apim-Subscription-Key": key,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": FORMAT,
            "User-Agent": f"{convert.BOOK_NAME}-puhe",
        })
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


# --- Koko sivun ääneenluku -----------------------------------------------------

def page_text(source_path: str) -> str:
    """Sivun lopullinen Markdown kuten convert.py:n mainissa."""
    return convert.convert_page(convert.SRC / source_path, source_path).text


def refresh_clips(texts: list[str], synthesize: Callable[[str], bytes] = azure,
                  log: Callable[[str], None] = print) -> list[str]:
    """Tee puuttuvat leikkeet varastoon. -> tehtyjen tunnisteet.

    Tiedosto kirjoitetaan valmiina, joten keskeytynyt ajo ei menetä tehtyjä:
    tiedostot itse ovat tila.
    """
    convert.SPEECH_STORE.mkdir(parents=True, exist_ok=True)
    done: list[str] = []
    for text in dict.fromkeys(texts):
        clip = convert.speech_clip(text)
        file = convert.SPEECH_STORE / f"{clip}.mp3"
        if file.is_file():
            continue
        log(f"{clip}: {text[:70]}")
        partial = file.with_suffix(".osittainen")
        partial.write_bytes(synthesize(convert.ssml(text)))
        partial.replace(file)
        done.append(clip)
    return done


def show_texts(pages: list[str], log: Callable[[str], None] = print) -> tuple[int, int]:
    """--teksti: sivujen yksiköt ja yhteenveto. -> (uniikit merkit, puuttuvat merkit).

    Puuttuva leike merkitään tähdellä.
    """
    clips = convert.available_clips() or set()
    seen: dict[str, bool] = {}
    for source_path in pages:
        text = page_text(source_path)
        units, tab_sets = convert.speech_units(text)
        rows = [(unit.kind, unit.text) for unit in units]
        for labels in tab_sets:
            announcement, choices = convert.tab_set_speech(labels)
            rows += [("välilehdet", announcement)] + [("valinta", t) for t in choices.values()]
        log(f"== {source_path}")
        for kind, spoken in rows:
            missing = convert.speech_clip(spoken) not in clips
            seen[spoken] = missing
            log(f"{'*' if missing else ' '} [{kind}] {spoken}")
    total = sum(len(spoken) for spoken in seen)
    missing = sum(len(spoken) for spoken, absent in seen.items() if absent)
    log(f"\n{len(seen)} leikettä, {total} merkkiä; puuttuu {sum(seen.values())} leikettä, "
        f"{missing} merkkiä (noin {missing * PRICE_PER_MILLION / 1e6:.2f} $, "
        f"{missing * BYTES_PER_CHARACTER / 1e6:.1f} Mt)")
    return total, missing


# --- Äänivarasto ---------------------------------------------------------------

def run_git(*arguments: str) -> subprocess.CompletedProcess:
    """git varaston hakemistossa (kloonaus ylähakemistossa)."""
    folder = convert.SPEECH_STORE
    cwd = folder if (folder / ".git").exists() else folder.parent
    return subprocess.run(["git", *arguments], cwd=cwd, capture_output=True, text=True)


def ensure_store(git: Callable[..., subprocess.CompletedProcess] = run_git,
                 log: Callable[[str], None] = print) -> bool:
    """Varasto ajan tasalle: klooni, jos puuttuu, muuten pull. -> onko se repo."""
    folder = convert.SPEECH_STORE
    if (folder / ".git").exists():
        # Tyhjässä (juuri luodussa) repossa ei ole vielä mitään haettavaa.
        if git("rev-parse", "--verify", "--quiet", "HEAD").returncode == 0:
            pulled = git("pull", "--ff-only", "--quiet")
            if pulled.returncode:
                log(f"varoitus: varaston päivitys epäonnistui: {pulled.stderr.strip()}")
        return True
    if not convert.SPEECH_REPO:
        log(f"varoitus: kirja.toml:ssa ei ole [puhe] repo -osoitetta; äänet vain "
            f"paikallisesti kansioon {folder}")
        return False
    if folder.exists() and any(folder.iterdir()):
        raise SystemExit(f"{folder} on olemassa mutta ei ole git-repo; siirrä se pois")
    log(f"kloonataan {convert.SPEECH_REPO} -> {folder}")
    cloned = git("clone", "--depth", "1", convert.SPEECH_REPO, str(folder))
    if cloned.returncode:
        raise SystemExit(f"varaston kloonaus epäonnistui: {cloned.stderr.strip()}")
    return True


def publish(git: Callable[..., subprocess.CompletedProcess] = run_git,
            log: Callable[[str], None] = print) -> bool:
    """Varaston uudet leikkeet (myös keskeytyneen ajon) repoon: commit ja
    push. Leikkeet ovat sisällön mukaan nimettyjä, joten toisen tekijän samaan
    aikaan pushaamat eivät ole ristiriidassa: hylätty push yritetään kerran
    uudelleen rebasen jälkeen. -> onnistuiko."""
    listed = git("ls-files", "--others", "--exclude-standard", "--", "*.mp3")
    new = listed.stdout.split()
    if not new:
        return True
    git("add", "--", *new)
    committed = git("commit", "--quiet", "-m", f"{len(new)} uutta leikettä")
    if committed.returncode:
        log(f"varoitus: commit epäonnistui: {committed.stderr.strip()}")
        return False
    branch = git("branch", "--show-current").stdout.strip()
    for attempt in range(2):
        pushed = git("push", "--quiet", "origin", "HEAD")
        if not pushed.returncode:
            log(f"{len(new)} leikettä pushattu varastoon")
            return True
        if attempt == 0:
            git("pull", "--rebase", "--quiet", "origin", branch)
    log(f"varoitus: push epäonnistui: {pushed.stderr.strip()}; aja git push "
        f"kansiossa {convert.SPEECH_STORE}")
    return False


# --- Vaiheittainen ohje --------------------------------------------------------

def refresh(page: Path, synthesize: Callable[[str], bytes] = azure, voice: str = VOICE,
            log: Callable[[str], None] = print) -> list[str]:
    """Tee vaiheittaisen ohjeen puuttuvat ja vanhentuneet äänet. -> tehtyjen
    vaiheiden kohtaukset.

    Luettelo kirjoitetaan jokaisen äänen jälkeen, jotta keskeytynyt ajo ei tee
    valmiita uudelleen. Poistuneiden vaiheiden äänet poistetaan. Äänen vaihto
    tekee kaikki uudelleen.
    """
    audio, speech = convert.walkthrough_speech(page.read_text(encoding="utf-8"))
    if audio is None:
        raise SystemExit(f"{page}: <walkthrough>-tagissa ei ole audio-attribuuttia")
    folder = page.parent / audio
    manifest = folder / convert.SPEECH_MANIFEST
    try:
        previous = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        previous = {}
    made = previous.get("steps", {}) if previous.get("voice") == voice else {}
    current = {scene: digest for scene, digest in made.items() if scene in speech}
    folder.mkdir(parents=True, exist_ok=True)

    def save() -> None:
        manifest.write_text(json.dumps({"voice": voice, "steps": dict(sorted(current.items()))},
                                       ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    done: list[str] = []
    for scene, text in speech.items():
        digest = convert.speech_hash(text)
        file = folder / f"{scene}.mp3"
        if current.get(scene) == digest and file.is_file():
            continue
        log(f"{scene}: {len(text)} merkkiä")
        file.write_bytes(synthesize(ssml(text, voice)))
        current[scene] = digest
        done.append(scene)
        save()
    for file in folder.glob("*.mp3"):
        if file.stem not in speech:
            file.unlink()
            log(f"{file.stem}: vaihe poistunut, ääni poistettu")
    save()
    return done


# --- Komento -------------------------------------------------------------------

def source_path(page: Path) -> str:
    """Komentorivin sivu (esim. ../src/sivu.md) polkuna lähdepuusta."""
    try:
        return page.resolve().relative_to(convert.SRC.resolve()).as_posix()
    except ValueError:
        raise SystemExit(f"{page} ei ole lähdepuussa {convert.SRC}") from None


def all_pages() -> tuple[list[str], list[str]]:
    """Kirjan valitut sivut ja vaiheittaiset ohjeet, joilla on ääni.
    -> (sivut, ohjeiden sivut), polut lähdepuusta."""
    pages, walkthroughs = [], []
    for origin in sorted(convert.SRC.rglob("*.md")):
        path = origin.relative_to(convert.SRC).as_posix()
        if not convert.is_page(path):
            continue
        if convert.is_speech_page(path):
            pages.append(path)
        text = origin.read_text(encoding="utf-8")
        if "<walkthrough" in text and convert.walkthrough_speech(text)[0] is not None:
            walkthroughs.append(path)
    return pages, walkthroughs


def main() -> int:
    parser = argparse.ArgumentParser(description="Ääneenluvun äänet (Azure Speech)")
    parser.add_argument("pages", type=Path, nargs="*",
                        help="lähteen sivut, esim. ../src/tyokalut.md (oletus: kaikki)")
    parser.add_argument("--teksti", action="store_true",
                        help="näytä luettavat tekstit ja hinta-arvio tekemättä ääniä")
    parser.add_argument("--ei-julkaisua", action="store_true",
                        help="älä committoi äläkä pushaa uusia leikkeitä varastoon")
    args = parser.parse_args()
    pages, walkthroughs = all_pages()
    if args.pages:
        chosen = [source_path(page) for page in args.pages]
        for path in chosen:
            if path not in pages and path not in walkthroughs:
                print(f"{path}: ei kirja.toml:n [puhe] sivut -listalla eikä vaiheittaista "
                      "ohjetta, jolla on audio-attribuutti", file=sys.stderr)
                return 1
        pages = [path for path in pages if path in chosen]
        walkthroughs = [path for path in walkthroughs if path in chosen]
    if args.teksti:
        if pages:
            show_texts(pages)
        for path in walkthroughs:
            _, speech = convert.walkthrough_speech((convert.SRC / path).read_text(encoding="utf-8"))
            for scene, text in speech.items():
                print(f"[{path}: {scene}]\n{text}\n")
        return 0
    repo = ensure_store() if pages else False
    status = 0
    done: list[str] = []
    try:
        texts = [text for path in pages for text in convert.speech_texts(page_text(path))]
        done = refresh_clips(texts)
        for path in walkthroughs:
            refresh(convert.SRC / path)
    except urllib.error.HTTPError as error:
        print(f"puhepalvelu vastasi {error.code}: {error.read().decode(errors='replace')}",
              file=sys.stderr)
        status = 1
    print(f"tehty {len(done)} leikettä" if done else "sivujen äänet ovat ajan tasalla")
    # Keskeytyneenkin ajon valmiit leikkeet julkaistaan.
    if repo and not args.ei_julkaisua and not publish():
        status = 1
    return status


if __name__ == "__main__":
    sys.exit(main())
