#!/usr/bin/env bash
set -euo pipefail

# Aufruf: messkopf_sweep.sh sweep MAX STEP (Volt)
# Kurzform MAX STEP und bisheriger Aufruf MAX bleiben möglich.
if [[ ${1:-} == sweep ]]; then shift; fi
MAX=${1:-10}
STEP=${2:-1}
PORT=/dev/ttyUSB1
PICO=http://192.168.178.98:8080

if (( $# > 2 )); then
  echo "Aufruf: $0 sweep [Maximalspannung 0..20] [Schrittweite >0]" >&2
  exit 1
fi
# Dezimalwerte ohne Bash-Ganzzahlarithmetik; keine aufsummierten Rundungsfehler.
values=$(awk -v max="$MAX" -v step="$STEP" 'BEGIN {
  number="^[0-9]+([.][0-9]+)?$";
  if (max !~ number || step !~ number || max+0>20 || step+0<=0 || max/step>10000) {
    print "Ungültiger Sweep: MAX 0..20 V, STEP >0, höchstens 10000 Schritte." > "/dev/stderr";
    exit 1;
  }
  for (i=0; i*step<=max+1e-9; i++) printf "%.9g\n", i*step;
}')

# Bei Ende oder Abbruch Generator ausschalten.
trap 'fy --port "$PORT" -c 2 off >&2' EXIT

sds tdiv 0.0000002 >&2

while IFS= read -r v; do
  if [[ "$v" == 0 ]]; then
    fy --port "$PORT" -c 2 off >&2
  else
    fy --port "$PORT" -c 2 set \
      --wave sine --freq 1000000 \
      --volts "$v" --offset 0 --on >&2
  fi

  # Vertikale Skalierung auch für kleine Signale (FY an 50 Ω etwa halbiert).
  if awk -v v="$v" 'BEGIN {exit !(v<=0.2)}'; then
    div=0.02
  elif awk -v v="$v" 'BEGIN {exit !(v<=0.5)}'; then
    div=0.05
  elif awk -v v="$v" 'BEGIN {exit !(v<=1)}'; then
    div=0.1
  elif awk -v v="$v" 'BEGIN {exit !(v<=2)}'; then
    div=0.2
  elif awk -v v="$v" 'BEGIN {exit !(v<=5)}'; then
    div=0.5
  elif awk -v v="$v" 'BEGIN {exit !(v<=10)}'; then
    div=1
  else
    div=2
  fi

  sds vdiv 1 "$div" >&2
  sds run >&2
  sleep 1

  scope=$(sds --json status)
  adc=""

  a2=""

  for attempt in 1 2 3 4 5; do
    if adc=$(curl -fsS --max-time 5 "$PICO/api/v1/state"); then
      if a2=$(jq -er '
        (.channels // [])[] |
        select(.input=="A2-A3"
          and .valid==true
          and .overrange==false) |
        .voltage_v |
        select(type=="number" and .>=0)
      ' <<<"$adc"); then
        break
      fi
    fi

    echo "A2 noch nicht gültig, Versuch $attempt/5" >&2
    sleep 0.2
  done

  if [[ -z "$a2" ]]; then
    echo "Abbruch: keine gültige A2-Messung. Letzte Antwort:" >&2
    printf '%s\n' "${adc:-Keine Antwort}" >&2
    exit 1
  fi

  if ! jq -e '. < 3.0' <<<"$a2" >/dev/null; then
    echo "Abbruch: A2 erreicht 3,0 V." >&2
    exit 1
  fi

  quality=baseline
  if [[ "$v" != 0 ]]; then
    quality=ok
    if ! jq -e '
      .channels["1"] |
      (.vpp_v | type)=="number" and
      (.freq_hz | type)=="number" and
      .vpp_v > 0 and
      .freq_hz >= 950000 and .freq_hz <= 1050000
    ' <<<"$scope" >/dev/null; then
      # Im kleinen Bereich ist die Frequenzmessung unter Umständen unzuverlässig.
      # Diese Punkte sind Rohdaten, keine bestätigten Kalibrierstützstellen.
      if awk -v v="$v" 'BEGIN {exit !(v<=0.5)}'; then
        quality=low_signal_unverified
        echo "Hinweis bei FY $v V: Scope-Signal/Frequenz nicht bestätigt; Rohdaten werden gespeichert." >&2
      else
        echo "Abbruch: Scope-Messung fehlt oder Frequenz passt nicht bei FY $v V." >&2
        exit 1
      fi
    fi
  fi

  scope_values=$(jq -r '
    .channels["1"] |
    "scope_vpp_v=\(.vpp_v); scope_freq_hz=\(.freq_hz)"
  ' <<<"$scope")
  printf 'fy_ch=2; fy_volts=%s; %s; a2_v=%s; scope_quality=%s\n' \
    "$v" "$scope_values" "$a2" "$quality"
done <<<"$values"
