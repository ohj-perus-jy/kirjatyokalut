#!/usr/bin/env bash
# Kirjan Zensical-sivuston ajo. Kirjan oma zensical/run.sh kutsuu tätä:
#   ./run.sh              -> kopioi ../src -> docs/, vahdi muutoksia ja tarjoile
#                            portissa 8001
#   ./run.sh 8003         -> sama, eri portissa
#   ./run.sh build        -> pelkkä rakennus site/-hakemistoon
#   ./run.sh test         -> testit
#   ./run.sh puhe SIVU    -> vaiheittaisen ohjeen äänet, esim.
#                            ./run.sh puhe ../src/sivu.md (puhe.py)
# Kirjan hakemisto (kirja.toml, mkdocs.yml, .venv, docs/) on tämän hakemiston
# ylähakemisto. Ilman kirjaa (työkalurepo yksinään) toimii vain test.
set -euo pipefail
TOOL=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
BOOK=$(dirname "$TOOL")
[[ -f $BOOK/kirja.toml ]] || BOOK=$TOOL
cd "$BOOK"

# Asenna, jos .venv puuttuu tai sen Zensical ei ole requirements.txt:n versio.
pin=$(sed -n 's/^zensical==//p' "$TOOL/requirements.txt")
if [[ ! -x .venv/bin/zensical ]] ||
   ! compgen -G ".venv/lib/python*/site-packages/zensical-$pin.dist-info" >/dev/null; then
    "$TOOL/setup.sh"
fi

if [[ ${1:-} == puhe ]]; then
    shift
    exec .venv/bin/python "$TOOL/puhe.py" "$@"
fi

# Testit kääntävät itse sen mitä tarvitsevat, joten convert.py:tä ei ajeta.
# Selain tarkistetaan erikseen, koska se ei ole .venv:ssä vaan kotihakemistossa
# ja sen systeemikirjastot kontissa; uusi devcontainer aloittaa ilman molempia.
# Tarkistus on ldd, koska "playwright install-deps" ajaisi apt-get updaten joka ajolla.
if [[ ${1:-} == test ]]; then
    shift
    if ! .venv/bin/python -c "import pytest, playwright" 2>/dev/null; then
        .venv/bin/pip install --quiet -r "$TOOL/requirements-dev.txt"
    fi
    browser=$(.venv/bin/python -c 'from playwright.sync_api import sync_playwright
with sync_playwright() as play:
    path = play.chromium.executable_path
print(path)' 2>/dev/null)
    if [[ ! -x $browser ]] || ldd "$browser" | grep -q "not found"; then
        .venv/bin/playwright install chromium
        echo "Asennetaan selaimen systeemikirjastot (vaatii sudon)..."
        sudo .venv/bin/playwright install-deps chromium
    fi
    # Testit ajetaan työkalujen hakemistosta (pytest.ini, tests/); kirjan
    # convert.py löytää ylähakemistosta.
    cd "$TOOL"
    exec "$BOOK/.venv/bin/python" -m pytest "$@"
fi

python3 "$TOOL/convert.py"

if [[ ${1:-} == build ]]; then
    exec .venv/bin/zensical build
fi

# Vahti palvelimen rinnalle: `zensical serve` seuraa docs/:ia, ei ../src:iä
# (convert.py: watch). Palvelinta ei exec:ata, jotta trap ehtii lopettaa vahdin.
python3 "$TOOL/convert.py" --watch &
watcher=$!
trap 'kill "$watcher" 2>/dev/null' EXIT INT TERM
.venv/bin/zensical serve --dev-addr "0.0.0.0:${1:-8001}"
