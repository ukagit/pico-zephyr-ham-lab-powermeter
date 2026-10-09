#!/usr/bin/env python3
"""Short 50-ohm CW frequency-response test; read-only unless --run is supplied.
Uses the existing bounded RTS calibration capture and restores rig settings
between every point. Keep tuner OFF, dummy load and scope setup unchanged.
"""
import argparse
import csv
import math
from pathlib import Path
import subprocess
import sys
import tempfile

DEFAULT_FREQUENCIES='1850000,3600000,7031670,14100000,28100000,50100000'
# EU IC-7300 HF/50MHz transmitter bands, deliberately omit optional 5/70MHz.
BANDS=((1800000,1999000),(3500000,3800000),(7000000,7200000),
       (10100000,10150000),(14000000,14350000),(18068000,18168000),
       (21000000,21450000),(24890000,24990000),(28000000,29700000),(50000000,52000000))

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--frequencies',default=DEFAULT_FREQUENCIES)
    ap.add_argument('--level',type=float,default=20)
    ap.add_argument('--load-ohms',type=int,choices=(25,50),default=50)
    ap.add_argument('--output',default='frequency_test_50ohm.csv')
    ap.add_argument('--run',action='store_true')
    ap.add_argument('--settle',type=float,default=1)
    ap.add_argument('--pause',type=float,default=5)
    ap.add_argument('--port');ap.add_argument('--pico',default='192.168.178.98')
    args=ap.parse_args()
    try:frequencies=[int(x) for x in args.frequencies.split(',')]
    except ValueError:ap.error('Frequencies must be integer Hz, comma-separated')
    if not frequencies or any(not any(lo<=f<=hi for lo,hi in BANDS) for f in frequencies):ap.error('Use IC-7300 HF/50 MHz amateur-band frequencies')
    if not math.isfinite(args.level) or not 1<=args.level<=100:ap.error('Level must be 1..100 percent')
    if not math.isfinite(args.settle) or not 0<=args.settle<8 or not math.isfinite(args.pause) or args.pause<0:ap.error('Invalid timing')
    script=Path(__file__).with_name('powermeter_calibrate.py')
    base=[sys.executable,str(script),'--baud','19200','--key-line','rts','--pico',args.pico,'--load-ohms',str(args.load_ohms),'--levels',str(args.level),'--settle',str(args.settle),'--pause',str(args.pause)]
    if args.port:base+=['--port',args.port]
    if not args.run:
        print('Read-only check. Planned Hz:',frequencies,flush=True)
        return subprocess.run(base).returncode
    out=Path(args.output)
    if out.exists():ap.error('Output already exists; choose a new filename')
    print(f'{args.load_ohms}-ohm load, tuner OFF; RF setting is not reference watts.',flush=True)
    with tempfile.TemporaryDirectory(prefix='powermeter-frequency-') as tmp, out.open('x',newline='') as target:
        writer=None
        for i,f in enumerate(frequencies):
            point=Path(tmp)/f'point_{i}.csv'
            result=subprocess.run(base+['--run','--frequency',str(f),'--output',str(point)])
            if result.returncode:return result.returncode
            with point.open(newline='') as src:
                reader=csv.DictReader(src);rows=list(reader)
                if len(rows)!=1:raise ValueError('Expected exactly one capture per frequency')
                if writer is None:
                    writer=csv.DictWriter(target,reader.fieldnames+['forward_7mhz_w','forward_error_pct']);writer.writeheader()
                row=rows[0]
                # Reuse current firmware curve without changing its calibration.
                import re
                header=Path(__file__).resolve().parent.parent/'src'/'power_calibration.h'
                curve_text=header.read_text().split('forward_curve[] = {',1)[1].split('};',1)[0]
                curve=[(float(a),float(b)) for a,b in re.findall(r'\{\s*([\d.]+)\s*,\s*([\d.]+)\s*\}',curve_text)]
                voltage=float(row['forward_v']);estimated=None
                for (a,pa),(b,pb) in zip(curve,curve[1:]):
                    if a<=voltage<=b:estimated=pa+(voltage-a)*(pb-pa)/(b-a);break
                row['forward_7mhz_w']='' if estimated is None else estimated
                row['forward_error_pct']='' if estimated is None else 100*(estimated/float(row['reference_w'])-1)
                writer.writerow(row);target.flush()
        print('Saved '+str(out));return 0

if __name__=='__main__':
    try:sys.exit(main())
    except KeyboardInterrupt:sys.exit(130)
    except Exception as exc:print('Error: '+str(exc),file=sys.stderr);sys.exit(1)
