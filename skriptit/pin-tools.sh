#!/bin/bash
# Kiinnittää kirjatyokalut-repon origin/mainin kirjan työkaluiksi
# (zensical/tyokalut) kirjan nykyiseen haaraan. Tekee commitin, ei pushaa.
#   ./pin-tools.sh [-m viesti] [kirja ...]    (oletus: kaikki kirjat)
# Ilman -m:ää viesti kootaan työkalujen committien otsikoista.
# Ajetaan kirjojen yhteisestä hakemistosta symlinkin kautta (ks. README).
cd "$(dirname "$0")"

msg=
if [[ ${1-} == -m ]]; then msg=$2; shift 2; fi
if (( $# )); then
    books=("${@%/}")
else
    books=()
    for t in */zensical/tyokalut; do books+=("${t%%/*}"); done
fi

rc=0
skip() { echo "   ohitetaan: $*" >&2; rc=1; }
pushes=()
for r in "${books[@]}"; do
    t="$r/zensical/tyokalut"
    [[ -e $r/.git ]] || { echo "== $r"; skip "ei ole git-repo"; continue; }
    branch=$(git -C "$r" branch --show-current)
    echo "== $r (haara: ${branch:-irrallinen HEAD})"
    [[ -e $t/.git ]] || { skip "$t puuttuu (aja ./pull-all.sh)"; continue; }
    [[ -n $branch ]] || { skip "kirja ei ole haarassa"; continue; }
    git -C "$t" switch -q main && git -C "$t" pull -q --ff-only \
        || { skip "työkalujen mainia ei saatu päivitettyä"; continue; }
    new=$(git -C "$t" rev-parse HEAD)
    [[ $new == "$(git -C "$t" rev-parse origin/main)" ]] \
        || { skip "työkalujen mainissa on pushaamattomia committeja"; continue; }
    old=$(git -C "$r" rev-parse HEAD:zensical/tyokalut)
    if [[ $old == "$new" ]]; then
        echo "   on jo kiinnitetty: $(git -C "$t" log -1 --format='%h %s')"
        continue
    fi
    git -C "$t" merge-base --is-ancestor "$old" "$new" 2>/dev/null \
        || { skip "kiinnitetty ${old:0:7} ei sisälly mainiin"; continue; }

    mapfile -t subjects < <(git -C "$t" log --no-merges --reverse --format=%s "$old..$new")
    n=${#subjects[@]}
    subject=$msg
    if [[ -z $subject ]]; then
        if (( n == 0 )); then subject="Työkalut: kirjatyokalut ${new:0:7}"
        elif (( n == 1 )); then subject="Työkalut: ${subjects[0]}"
        elif (( n == 2 )); then subject="Työkalut: ${subjects[1]} (+1 muu)"
        else subject="Työkalut: ${subjects[n-1]} (+$((n-1)) muuta)"
        fi
    fi
    body="kirjatyokalut ${old:0:7}..${new:0:7}:"
    for s in "${subjects[@]}"; do body+=$'\n'"- $s"; done

    git -C "$r" commit -q -m "$subject" -m "$body" -- zensical/tyokalut \
        || { skip "commit epäonnistui"; continue; }
    echo "   kiinnitetty haaraan $branch: ${old:0:7} → ${new:0:7}" \
         "(commit $(git -C "$r" rev-parse --short HEAD): $subject)"
    pushes+=("git -C $r push")
done

if (( ${#pushes[@]} )); then
    echo
    echo "Commitit on tehty, mutta niitä ei ole pushattu. Pushaa:"
    printf '  %s\n' "${pushes[@]}"
fi
exit $rc
