#!/usr/bin/env python3
"""Compare detector voltage without/with an RF scope probe. No scope access.
Sweep defaults to read-only; --run enables IC-7300 CW RTS keying at 19200 baud.
Old firmware watts/SWR are deliberately ignored for a changed coupler.
"""
import argparse
import csv
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import statistics
import sys
import threading
import time
from urllib.request import urlopen
from powermeter_calibrate import Rig, encode_bcd
from icom7300_read import DEFAULT_PORT, bcd

BANDS = ((1800000, 1999000), (3500000, 3800000), (7000000, 7200000),
         (10100000, 10150000), (14000000, 14350000), (18068000, 18168000),
         (21000000, 21450000), (24890000, 24990000), (28000000, 29700000),
         (50000000, 52000000))
FIELDS = ['timestamp_utc', 'probe', 'notes', 'frequency_hz', 'rf_setting_pct',
          'rf_power_raw', 'sample_count', 'forward_mean_v', 'forward_std_v',
          'forward_min_v', 'forward_max_v', 'forward_zero_v', 'forward_net_v',
          'forward_raw_samples', 'forward_range_mv_samples', 'reverse_mean_v',
          'po_raw', 'swr_raw', 'alc_raw', 'vd_raw', 'id_raw', 'capture_seconds']


def levels_parse(text):
    if ':' in text:
        start, stop, step = map(int, text.split(':'))
        if step <= 0 or start > stop:
            raise ValueError('Range must be start:stop:positive_step')
        levels = list(range(start, stop + 1, step))
    else:
        levels = [float(x) for x in text.split(',')]
    if not levels or len(set(levels)) != len(levels) or any(
            not math.isfinite(x) or not 1 <= x <= 100 for x in levels):
        raise ValueError('Unique levels from 1 to 100 required')
    raw = [round(x * 255 / 100) for x in levels]
    if len(set(raw)) != len(raw):
        raise ValueError('Levels map to duplicate ICOM settings')
    return levels


def read_detector(host, deadline):
    errors = []
    for attempt in range(3):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError('TX/read deadline reached')
        try:
            with urlopen('http://' + host + ':8080/api/v1/measure',
                         timeout=min(2, remaining)) as response:
                data = json.load(response)
            channels = data.get('channels', [])
            a = next(c for c in channels if c.get('input') == 'A0-A3')
            v = a.get('voltage_v')
            if (not a.get('valid') or a.get('overrange') or
                    not isinstance(v, (int, float)) or not math.isfinite(v)):
                raise ValueError('Invalid/overrange A0: ' + json.dumps(a))
            return channels
        except (OSError, ValueError, StopIteration) as exc:
            errors.append(str(exc))
            if attempt < 2:
                time.sleep(min(.15, max(0, deadline - time.monotonic())))
    raise ValueError('Pico read failed: ' + '; '.join(errors))


def capture(args, deadline):
    forwards, reverses, raws, ranges = [], [], [], []
    for i in range(args.samples):
        if i:
            time.sleep(min(args.sample_interval,
                           max(0, deadline - time.monotonic())))
        channels = read_detector(args.pico, deadline)
        a = next(c for c in channels if c['input'] == 'A0-A3')
        forwards.append(a['voltage_v'])
        raws.append(a['raw'])
        ranges.append(a['range_mv'])
        for c in channels:
            v = c.get('voltage_v')
            if (c.get('input') == 'A1-A3' and c.get('valid') and
                    not c.get('overrange') and isinstance(v, (int, float)) and
                    math.isfinite(v)):
                reverses.append(v)
    return dict(sample_count=len(forwards), forward_mean_v=statistics.mean(forwards),
                forward_std_v=statistics.stdev(forwards) if len(forwards) > 1 else 0,
                forward_min_v=min(forwards), forward_max_v=max(forwards),
                forward_raw_samples=json.dumps(raws),
                forward_range_mv_samples=json.dumps(ranges),
                reverse_mean_v=statistics.mean(reverses) if reverses else '')


def sweep(args, capture_fn=capture, fields=FIELDS):
    levels = levels_parse(args.levels)
    if (not any(lo <= args.frequency <= hi for lo, hi in BANDS) or
            not 1 <= args.samples <= 10 or not 0 < args.max_tx <= 15 or
            not all(math.isfinite(x) for x in
                    (args.settle, args.pause, args.sample_interval, args.max_tx)) or
            not 0 <= args.settle < args.max_tx or args.pause < 0 or
            args.sample_interval < 0):
        raise ValueError('Invalid band, samples or timing')
    if args.settle + (args.samples - 1) * args.sample_interval >= args.max_tx:
        raise ValueError('Sampling plan exceeds TX window')
    if args.plan:
        print(json.dumps(dict(frequency_hz=args.frequency, levels=levels,
                              samples=args.samples, probe=args.probe,
                              max_tx=args.max_tx, scope_access=False)))
        return 0
    out = Path(args.output) if args.output else None
    if args.run and (out is None or not args.probe or out.exists()):
        raise ValueError('--run needs --probe and a new --output CSV')
    if out and args.run and not out.parent.exists():
        raise ValueError('Output directory missing')
    rig = None
    original_freq = original_power = None
    try:
        rig = Rig(args.port, 19200, 0x94, .7, False)
        if args.run:
            rig.rx()
        original_freq = bcd(rig.query(b'\x03')[::-1])
        original_power = bcd(rig.query(b'\x14\x0a'))
        mode = rig.query(b'\x04')[0]
        print(json.dumps(dict(frequency_hz=original_freq, mode_code=mode,
                              rf_power_raw=original_power,
                              channels=read_detector(args.pico, time.monotonic()+6)),
                         indent=2))
        if not args.run:
            print('Connection check only; no TX/settings writes, no scope access.')
            return 0
        if mode != 3:
            raise ValueError('Set IC-7300 to CW; tuner OFF; keep USB CW RTS setting')
        rig.write_setting(b'\x05', encode_bcd(args.frequency, 5)[::-1])
        if bcd(rig.query(b'\x03')[::-1]) != args.frequency:
            raise ValueError('Frequency readback mismatch')
        with out.open('x', newline='') as file:
            writer = csv.DictWriter(file, fields)
            writer.writeheader()
            # RF OFF baseline for each independent run; never used as RF watts.
            zero = capture_fn(args, time.monotonic()+max(8, args.max_tx))
            offset = zero['forward_mean_v']
            base = dict(timestamp_utc=datetime.now(timezone.utc).isoformat(),
                        probe=args.probe, notes=args.notes,
                        frequency_hz=args.frequency, rf_setting_pct=0,
                        rf_power_raw=original_power, forward_zero_v=offset,
                        forward_net_v=0, **zero)
            writer.writerow(base)
            file.flush()
            for level in levels:
                raw = round(level * 255 / 100)
                rig.write_setting(b'\x14\x0a', encode_bcd(raw, 2))
                if bcd(rig.query(b'\x14\x0a')) != raw:
                    raise ValueError('Power setting readback mismatch')
                expired = threading.Event()
                def stop_rf():
                    expired.set()
                    try:
                        rig.io.rts = False
                    except Exception as exc:
                        print('RTS timeout cleanup failed: ' + str(exc), file=sys.stderr)
                timer = threading.Timer(args.max_tx, stop_rf)
                timer.daemon = True
                started = time.monotonic()
                try:
                    rig.io.rts = True
                    timer.start()
                    time.sleep(args.settle)
                    values = capture_fn(args, started + args.max_tx)
                    indicators = {k: bcd(rig.query(bytes((0x15, sub))))
                                  for k, sub in [('po_raw', 0x11), ('swr_raw', 0x12),
                                                 ('alc_raw', 0x13), ('vd_raw', 0x15),
                                                 ('id_raw', 0x16)]}
                    if expired.is_set() or time.monotonic() >= started+args.max_tx:
                        raise TimeoutError('TX limit reached; point discarded')
                finally:
                    try:
                        rig.io.rts = False
                    finally:
                        timer.cancel()
                        if timer.ident is not None:
                            timer.join()
                        rig.rx()
                row = dict(timestamp_utc=datetime.now(timezone.utc).isoformat(),
                           probe=args.probe, notes=args.notes,
                           frequency_hz=args.frequency, rf_setting_pct=level,
                           rf_power_raw=raw, forward_zero_v=offset,
                           forward_net_v=values['forward_mean_v']-offset,
                           capture_seconds=round(time.monotonic()-started, 3),
                           **values, **indicators)
                writer.writerow(row)
                file.flush()
                print(f'{level:g}%: A0={values["forward_mean_v"]:.7f} V '
                      f'±{values["forward_std_v"]:.7f} V (sample SD)', flush=True)
                if 'current_mean_v' in values:
                    master=values['master_mean_w']
                    print('  A2='+format(values['current_mean_v'],'.7f')+' V · A0 master '+
                          (format(master,'.3f')+' W' if isinstance(master,(int,float)) else
                           'outside calibration; point not usable for alignment'),flush=True)
                time.sleep(args.pause)
        print('Saved ' + str(out))
        return 0
    finally:
        if rig:
            if args.run:
                actions = [lambda: setattr(rig.io, 'rts', False), rig.rx]
                if original_power is not None:
                    actions.append(lambda: rig.write_setting(b'\x14\x0a', encode_bcd(original_power, 2)))
                if original_freq is not None:
                    actions.append(lambda: rig.write_setting(b'\x05', encode_bcd(original_freq, 5)[::-1]))
                for action in actions:
                    try:
                        action()
                    except Exception as exc:
                        print('RX/restore failed: ' + str(exc), file=sys.stderr)
            rig.io.close()


def load_run(path, probe):
    with Path(path).open(newline='') as f:
        rows = list(csv.DictReader(f))
    zeros = [r for r in rows if float(r['rf_setting_pct']) == 0]
    points = [r for r in rows if float(r['rf_setting_pct']) > 0]
    if len(zeros) != 1 or not points or any(r['probe'] != probe for r in rows):
        raise ValueError('Expected one RF-OFF baseline and correctly labeled points: ' + path)
    result = {}
    for row in points:
        key = (int(row['frequency_hz']), int(row['rf_power_raw']))
        if key in result:
            raise ValueError('Duplicate point: ' + path)
        for col in ('forward_mean_v', 'forward_std_v', 'forward_net_v'):
            if not math.isfinite(float(row[col])):
                raise ValueError('Nonfinite measurement: ' + path)
        result[key] = row
    return zeros[0], result


def compare(args):
    za, a = load_run(args.without, 'without')
    zb, b = load_run(args.with_probe, 'with')
    if set(a) != set(b):
        raise ValueError('Runs must contain exactly the same frequencies/settings; incomplete sweep?')
    out = Path(args.output)
    png = out.with_suffix('.png')
    if out.exists() or (args.plot and png.exists()):
        raise ValueError('Output exists; use a new filename')
    plt = None
    if args.plot:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    results = []
    for key in sorted(a):
        aa, bb = a[key], b[key]
        if float(aa['rf_setting_pct']) != float(bb['rf_setting_pct']):
            raise ValueError('RF percentages differ')
        va, vb = float(aa['forward_mean_v']), float(bb['forward_mean_v'])
        na, nb = float(aa['forward_net_v']), float(bb['forward_net_v'])
        sd = float(aa['forward_std_v'])
        floor = max(1e-6, 3*sd, 3*float(za['forward_std_v']), 3*float(zb['forward_std_v']))
        results.append(dict(frequency_hz=key[0], rf_setting_pct=aa['rf_setting_pct'],
                            rf_power_raw=key[1], without_v=va, with_v=vb,
                            difference_v=vb-va,
                            difference_pct=100*(vb-va)/va if abs(va)>floor else '',
                            without_net_v=na, with_net_v=nb,
                            net_difference_pct=100*(nb-na)/na if na>floor else '',
                            without_std_v=aa['forward_std_v'], with_std_v=bb['forward_std_v']))
    with out.open('x', newline='') as f:
        writer = csv.DictWriter(f, results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    finite = [r for r in results if isinstance(r['net_difference_pct'], (int, float))]
    if finite:
        print(f'Largest absolute baseline-corrected VOLTAGE change: '
              f'{max(abs(r["net_difference_pct"]) for r in finite):.2f}%')
    print('Positive difference = detector voltage higher WITH probe. Not a watt error or accuracy claim.')
    if plt:
        fig, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
        x = [float(r['rf_setting_pct']) for r in results]
        for col, sd, label, color in [('without_v', 'without_std_v', 'Ohne Tastkopf', '#167b54'),
                                      ('with_v', 'with_std_v', 'Mit Tastkopf', '#2364b0')]:
            axes[0].errorbar(x, [r[col] for r in results],
                            yerr=[float(r[sd]) for r in results], label=label,
                            color=color, marker='.', capsize=2)
        axes[0].set_ylabel('A0−A3 Detektorspannung [V]')
        axes[0].legend()
        axes[0].set_title('Tastkopfvergleich: neuer Koppler · kein Wattvergleich')
        axes[1].plot(x, [r['net_difference_pct'] if r['net_difference_pct'] != '' else math.nan
                         for r in results], 'o-', ms=3)
        axes[1].axhline(0, color='gray', lw=1)
        axes[1].set_ylabel('Spannungsänderung mit Tastkopf [%]\nRuheoffset abgezogen')
        axes[1].set_xlabel('ICOM-Leistungsstellung [%]')
        for ax in axes:
            ax.grid(alpha=.25)
        fig.text(.5, .015, 'Fehlerbalken: Streuung der Einzelabfragen; kein Nachweis absoluter Messgenauigkeit.',
                 ha='center', fontsize=9)
        fig.tight_layout(rect=(0, .04, 1, 1))
        fig.savefig(png, dpi=160)
        plt.close(fig)
        print('Saved ' + str(png))
    print('Saved ' + str(out))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='command', required=True)
    sw = sub.add_parser('sweep', help='Read-only check unless --run')
    sw.add_argument('--run', action='store_true')
    sw.add_argument('--plan', action='store_true')
    sw.add_argument('--probe', choices=('without', 'with'))
    sw.add_argument('--output')
    sw.add_argument('--notes', default='')
    sw.add_argument('--port', default=DEFAULT_PORT)
    sw.add_argument('--pico', default='192.168.178.98')
    sw.add_argument('--frequency', type=int, default=7100000)
    sw.add_argument('--levels', default='1:100:1')
    sw.add_argument('--samples', type=int, default=3)
    sw.add_argument('--sample-interval', type=float, default=.15)
    sw.add_argument('--settle', type=float, default=1)
    sw.add_argument('--pause', type=float, default=5)
    sw.add_argument('--max-tx', type=float, default=8)
    co = sub.add_parser('compare', help='Offline CSV voltage comparison')
    co.add_argument('--without', required=True)
    co.add_argument('--with-probe', required=True)
    co.add_argument('--output', default='probe_comparison.csv')
    co.add_argument('--plot', action='store_true')
    args = ap.parse_args(argv)
    try:
        return sweep(args) if args.command == 'sweep' else compare(args)
    except KeyboardInterrupt:
        print('Stopped; RX cleanup requested.', file=sys.stderr)
        return 130
    except Exception as exc:
        print('Error: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
