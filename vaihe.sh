# Ladataan (source) setup.sh:ssa ja run.sh:ssa.
#   vaihe KUVAUS KOMENTO...
# Ajaa komennon niin, että tuloste menee lokiin ja päätteessä näkyy pyörijä,
# kulunut aika ja lokin viimeisin rivi. Windowsin kansiossa (WSL:n 9p) pip voi
# asentaa minuutteja. Virheessä loki tulostetaan kokonaan.
vaihe() {
    local kuvaus=$1 loki pyorija= tila=0 alku=$SECONDS
    shift
    loki=$(mktemp)
    if [[ -t 1 ]]; then
        _vaihe_pyori "$kuvaus" "$loki" &
        pyorija=$!
    else
        echo "$kuvaus..."
    fi
    "$@" >"$loki" 2>&1 || tila=$?
    if [[ -n $pyorija ]]; then
        kill "$pyorija" 2>/dev/null || true
        wait "$pyorija" 2>/dev/null || true
        printf '\r\e[K'
    fi
    if ((tila == 0)); then
        echo "✓ $kuvaus ($((SECONDS - alku)) s)"
    else
        echo "✗ $kuvaus epäonnistui:" >&2
        cat "$loki" >&2
    fi
    rm -f "$loki"
    return "$tila"
}

# Päättyy myös, jos skripti keskeytetään (Ctrl-C): taustaprosessi ei saa SIGINTiä.
_vaihe_pyori() {
    set +e  # kutsujan set -e katkaisisi tyhjän lokin grepiin
    local kuvaus=$1 loki=$2 alku=$SECONDS i=0 leveys paa rivi
    local merkit=(⠋ ⠙ ⠹ ⠸ ⠼ ⠴ ⠦ ⠧ ⠇ ⠏)
    while kill -0 $$ 2>/dev/null; do
        leveys=$(stty size </dev/tty 2>/dev/null) && leveys=${leveys#* } || leveys=80
        # pipin edistymispalkit (━) ja tyhjät rivit ohitetaan
        rivi=$(grep -v -e '^[[:space:]]*$' -e '━' "$loki" | tail -n 1 |
               sed 's/^ *//; s/ (from .*//')
        paa="${merkit[i++ % ${#merkit[@]}]} $kuvaus ($((SECONDS - alku)) s)"
        rivi=${rivi:0:$((leveys - ${#paa} - 3 > 0 ? leveys - ${#paa} - 3 : 0))}
        printf '\r%s  \e[2m%s\e[0m\e[K' "$paa" "$rivi"
        sleep 0.2
    done
}
