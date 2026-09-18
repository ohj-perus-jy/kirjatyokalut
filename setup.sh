#!/usr/bin/env bash
# Kertaluontoinen asennus; ajettavissa uudelleen turvallisesti. Devcontainer-
# imagessa on python3 mutta ei venv:iä eikä pip:iä, joten ne asennetaan tässä.
# .venv tulee kirjan hakemistoon (tämän ylähakemisto), ks. run.sh.
set -euo pipefail
TOOL=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
BOOK=$(dirname "$TOOL")
[[ -f $BOOK/kirja.toml ]] || BOOK=$TOOL
cd "$BOOK"

if ! python3 -c "import ensurepip" >/dev/null 2>&1; then
    echo "Asennetaan python3-venv ja python3-pip (vaatii sudon)..."
    sudo apt-get update -qq
    sudo apt-get install -y -qq python3-venv python3-pip
fi

[[ -d .venv ]] || python3 -m venv .venv
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -r "$TOOL/requirements.txt"

echo
echo "Valmis. Käynnistä:  ./zensical/run.sh"
