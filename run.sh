#!/usr/bin/env bash
# Kirjan Zensical-sivuston ajo. Kirjan oma zensical/run.sh kutsuu tätä:
#   ./run.sh              -> kopioi ../src -> docs/, vahdi muutoksia ja tarjoile
#                            portissa 8001 tai seuraavassa vapaassa
#   ./run.sh 8003         -> sama, alkaen portista 8003
#   ./run.sh build        -> pelkkä rakennus site/-hakemistoon
#   ./run.sh test         -> testit
#   ./run.sh puhe         -> ääneenluvun leikkeet ja vaiheittaisen ohjeen äänet
#                            (puhe.py); ./run.sh puhe ../src/sivu.md vain sivulle,
#                            ./run.sh puhe --teksti näyttää luettavan
# Kirjan hakemisto (kirja.toml, mkdocs.yml, .venv, docs/) on tämän hakemiston
# ylähakemisto. Ilman kirjaa (työkalurepo yksinään) toimii vain test.
set -euo pipefail
TOOL=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
BOOK=$(dirname "$TOOL")
[[ -f $BOOK/kirja.toml ]] || BOOK=$TOOL
cd "$BOOK"
source "$TOOL/vaihe.sh"

# Asenna, jos .venv puuttuu, sen Zensical ei ole requirements.txt:n versio tai
# se on siirretty: skriptien #!-rivi osoittaa silloin vanhaan polkuun.
pin=$(sed -n 's/^zensical==//p' "$TOOL/requirements.txt")
if [[ ! -x .venv/bin/zensical ]] ||
   [[ ! -x $(sed -n '1s/^#!//p' .venv/bin/zensical) ]] ||
   ! compgen -G ".venv/lib/python*/site-packages/zensical-$pin.dist-info" >/dev/null; then
    "$TOOL/setup.sh" --run
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
        vaihe "Asennetaan testien riippuvuudet" \
            .venv/bin/pip install -r "$TOOL/requirements-dev.txt"
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

# Ensimmäinen vapaa portti pyydetystä (oletus 8001) ylöspäin, jotta usean kirjan
# voi tarjoilla yhtä aikaa. Kokeilu sitoo saman osoitteen kuin zensical serve, ja
# SO_REUSEADDR on päällä kuten sillä: suljetun palvelimen TIME_WAIT-yhteydet eivät
# vie porttia. Kontissa näkyvät vain kontin portit; VS Code välittää portin
# koneelle ja valitsee siellä toisen, jos se on varattu.
want=${1:-8001}
port=$(python3 - "$want" <<'EOF'
import socket, sys
start = int(sys.argv[1])
for port in range(start, start + 20):
    with socket.socket() as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("0.0.0.0", port))
        except OSError:
            continue
    print(port)
    break
else:
    sys.exit(f"portit {start}–{start + 19} ovat kaikki varattuja")
EOF
)
if [[ $port != "$want" ]]; then
    echo "Portti $want on varattu, käytetään porttia $port."
fi
echo "Kirja: http://localhost:$port"
if [[ -f /.dockerenv || -f /run/.containerenv ]]; then
    echo "Dev containerissa koneen osoite voi olla eri: katso VS Coden Ports-välilehti."
fi

# Vahti palvelimen rinnalle: `zensical serve` seuraa docs/:ia, ei ../src:iä
# (convert.py: watch). Palvelinta ei exec:ata, jotta trap ehtii lopettaa vahdin.
python3 "$TOOL/convert.py" --watch &
watcher=$!
trap 'kill "$watcher" 2>/dev/null' EXIT INT TERM
.venv/bin/zensical serve --dev-addr "0.0.0.0:$port"
