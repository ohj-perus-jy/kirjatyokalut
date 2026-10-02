#!/bin/bash
# Päivittää tämän hakemiston repot ja hakee kirjojen työkaluihin
# (zensical/tyokalut) kirjatyokalut-repon mainin. Jos kirjaan on kiinnitetty
# eri versio, siitä ilmoitetaan. Kiinnitys: ./pin-tools.sh [kirja ...]
# Ajetaan kirjojen yhteisestä hakemistosta symlinkin kautta (ks. README).
cd "$(dirname "$0")"

differ=()
for d in */.git; do
    r="${d%/.git}"; echo "== $r"
    # Ilman submodule.recurse=false pull --rebase rebasettaisi työkalujen
    # mainin kirjaan kiinnitetyn version päälle.
    git -C "$r" -c submodule.recurse=false pull --rebase || continue
    [[ -f $r/.gitmodules ]] || continue
    t="$r/zensical/tyokalut"
    [[ -e $t/.git ]] || git -C "$r" submodule update --init --recursive || continue
    [[ -e $t/.git ]] || continue

    before=$(git -C "$t" rev-parse HEAD)
    if ! { git -C "$t" switch -q main && git -C "$t" pull -q --ff-only; }; then
        echo "   HUOM: työkalujen mainia ei saatu päivitettyä ($t)" >&2
        continue
    fi
    head=$(git -C "$t" rev-parse HEAD)
    [[ $before != "$head" ]] && echo "   työkalut: ${before:0:7} → main ${head:0:7}"

    pinned=$(git -C "$r" rev-parse HEAD:zensical/tyokalut)
    [[ $pinned == "$head" ]] && continue
    branch=$(git -C "$r" branch --show-current)
    if git -C "$t" merge-base --is-ancestor "$pinned" "$head" 2>/dev/null; then
        why="main on $(git -C "$t" rev-list --count "$pinned..$head") commitia uudempi"
    else
        why="kiinnitetty versio ei ole mainissa"
    fi
    echo "   HUOM: työkalut ovat mainissa ${head:0:7}, haaraan ${branch:-(irrallinen HEAD)}" \
         "on kiinnitetty ${pinned:0:7} ($why)" >&2
    differ+=("$r")
done

if (( ${#differ[@]} )); then
    echo
    echo "Työkalut eri versiossa kuin kirjaan kiinnitetty: ${differ[*]}"
    echo "Kiinnitä: ./pin-tools.sh ${differ[*]}"
fi
