#!/usr/bin/env bash
# One manually selected scope scale, several frequencies and power settings.
# The Python capture owns RTS timeout, RX cleanup and rig setting restoration.
set -euo pipefail
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
python_bin=${PYTHON:-python3}
load=50
levels=5,10,15,20
frequencies=1850000,3600000,7100000,14100000,28100000,50100000
tag=low_20Vdiv
output_dir=""
run=0
extra=()
usage() {
  cat <<'EOF'
Usage: bash tools/powermeter_series.sh [options]
  --run                   Transmit and capture; otherwise check connections only
  --load-ohms 50|25        Actual switched load (default 50)
  --levels 5,10,15,20      Icom RF percentages, NOT reference watts
  --frequencies Hz,Hz     Default: 1.85,3.6,7.1,14.1,28.1,50.1 MHz
  --tag low_20Vdiv         Filename label for the manually selected scope scale
  --output-dir DIR         New directory; default cal_series_TIMESTAMP
  --port DEVICE           Icom serial port; baud stays 19200
  --pico HOST             Default 192.168.178.98
  --settle SECONDS         Default 1
  --pause SECONDS          Default 5 between points
  --scope-command CMD      Default 'sds status'
  --auto-scope             Set scope timebase and channel V/div in RX
  --scope-control CMD      Default sds; optional global --ip etc.
  --scope-vdiv-map MAP     Default 5:10,20:20,100:50 (percent:V/div)
  --timebase-factors LIST  Default 1; diagnostic example 0.5,1,2
  --plan                   Show all capture settings, no device access
  --help
Keep tuner OFF. Select actual load and scope scale before --run.
EOF
}
settle=1
pause=5
while (($#)); do
  case "$1" in
    --run) run=1;shift;;
    --auto-scope|--plan) extra+=("$1");shift;;
    --help|-h) usage;exit 0;;
    --load-ohms|--levels|--frequencies|--tag|--output-dir|--settle|--pause|--port|--pico|--scope-command|--scope-control|--scope-vdiv-map|--timebase-factors|--channel)
      (($#>=2)) || { echo "Missing value: $1" >&2;exit 2; }
      case "$1" in
        --load-ohms) load=$2;; --levels) levels=$2;;
        --frequencies) frequencies=$2;; --tag) tag=$2;;
        --output-dir) output_dir=$2;; --settle) settle=$2;; --pause) pause=$2;;
        *) extra+=("$1" "$2");;
      esac
      shift 2;;
    *) echo "Unknown option: $1" >&2;usage >&2;exit 2;;
  esac
done
[[ "$load" == 50 || "$load" == 25 ]] || { echo 'Load must be 50 or 25 ohms' >&2;exit 2; }
[[ "$tag" =~ ^[a-zA-Z0-9_-]+$ ]] || { echo 'Tag: letters, digits, _ or - only' >&2;exit 2; }
# Validate the entire plan before any RF or output mutation.
"$python_bin" - "$frequencies" "$levels" "$settle" "$pause" <<'PY'
import math,sys
bands=((1800000,1999000),(3500000,3800000),(7000000,7200000),(10100000,10150000),(14000000,14350000),(18068000,18168000),(21000000,21450000),(24890000,24990000),(28000000,29700000),(50000000,52000000))
try:
    freq=[int(x) for x in sys.argv[1].split(',')]
    levels=[float(x) for x in sys.argv[2].split(',')]
    settle,pause=map(float,sys.argv[3:5])
    assert freq and len(set(freq))==len(freq) and all(any(a<=f<=b for a,b in bands) for f in freq)
    assert levels and all(math.isfinite(x) and 1<=x<=100 for x in levels)
    assert math.isfinite(settle) and 0<=settle<8 and math.isfinite(pause) and pause>=0
except (ValueError,AssertionError):
    sys.exit('Invalid frequency/levels/timing plan; use IC-7300 amateur-band frequencies')
PY
IFS=',' read -r -a freq_list <<< "$frequencies"
common=(--baud 19200 --key-line rts --load-ohms "$load" --levels "$levels" --settle "$settle" --pause "$pause" "${extra[@]}")
printf 'Load: %s ohms; scope label: %s; levels: %s; frequencies Hz: %s\n' "$load" "$tag" "$levels" "$frequencies"
if [[ " ${extra[*]} " == *" --plan "* ]]; then
  for frequency in "${freq_list[@]}";do
    "$python_bin" "$script_dir/powermeter_calibrate.py" "${common[@]}" --frequency "$frequency"
  done
  exit 0
fi
# Preflight all scope options before creating files or touching devices.
for frequency in "${freq_list[@]}";do
  "$python_bin" "$script_dir/powermeter_calibrate.py" "${common[@]}" --plan --frequency "$frequency" >/dev/null
done
if (( !run )); then
  "$python_bin" "$script_dir/powermeter_calibrate.py" "${common[@]}" --frequency "${freq_list[0]}"
  exit 0
fi
if [[ -z "$output_dir" ]]; then output_dir="cal_series_$(date +%Y%m%d_%H%M%S)_${load}ohm_${tag}";fi
# Refuse existing directories, so no calibration records are overwritten.
mkdir -- "$output_dir"
printf 'Each frequency has its own CSV in %s. Stop with Ctrl+C.\n' "$output_dir"
for frequency in "${freq_list[@]}"; do
  printf '\n=== %s Hz / %s ohms / %s ===\n' "$frequency" "$load" "$tag"
  "$python_bin" "$script_dir/powermeter_calibrate.py" "${common[@]}" --run --frequency "$frequency" --output "$output_dir/cal_${load}ohm_${frequency}Hz_${tag}.csv"
done
printf '\nSeries completed: %s\n' "$output_dir"
