#!/usr/bin/env python3
"""Record paired A0 master watts and A2 current-coupler voltage; no scope.

Read-only by default. --run enables a bounded IC-7300 CW RTS sweep at 19200
baud, with the existing probe-test tool's watchdog, RX cleanup and restoration.
This records data only: no firmware calibration is overwritten.
"""
import argparse
from datetime import datetime, timezone
import json
import math
import statistics
import sys
import time
from urllib.request import urlopen
import powermeter_probe_test as sweep_tool

EXTRA_FIELDS = ['current_mean_v', 'current_std_v', 'current_min_v',
                'current_max_v', 'current_raw_samples', 'current_range_mv_samples',
                'master_mean_w', 'master_std_w', 'master_valid_samples',
                'alignment_usable', 'master_calibration_frequency_hz',
                'paired_samples']


def read_pair(host, deadline):
    errors = []
    for attempt in range(3):
        remaining = deadline-time.monotonic()
        if remaining <= 0:
            raise TimeoutError('TX/read deadline reached')
        try:
            with urlopen('http://'+host+':8080/api/v1/measure',
                         timeout=min(2, remaining)) as response:
                data = json.load(response)
            if not data.get('measurement_valid'):
                raise ValueError('Pico measurement invalid')
            a = next(c for c in data['channels'] if c.get('input') == 'A0-A3')
            c = next(c for c in data['channels'] if c.get('input') == 'A2-A3')
            for channel in (a, c):
                v = channel.get('voltage_v')
                if (not channel.get('valid') or channel.get('overrange') or
                        not isinstance(v, (int, float)) or not math.isfinite(v)):
                    raise ValueError('Invalid ADC channel: '+json.dumps(channel))
            p = data['power']
            if p.get('calibration_frequency_hz') != 7031670:
                raise ValueError('Unexpected A0 master calibration frequency')
            if p.get('quality') == 'forward_frequency_not_calibrated':
                raise ValueError('Select hamlab calibration 7100000 before alignment')
            w = p.get('forward_w')
            valid = bool(p.get('forward_valid') and isinstance(w, (int, float))
                         and math.isfinite(w) and w > 0)
            reverse = next((x.get('voltage_v') for x in data['channels']
                            if x.get('input') == 'A1-A3' and x.get('valid')
                            and not x.get('overrange')), None)
            return dict(timestamp_utc=datetime.now(timezone.utc).isoformat(),
                        forward_v=a['voltage_v'], current_v=c['voltage_v'],
                        forward_raw=a['raw'], current_raw=c['raw'],
                        forward_range_mv=a['range_mv'], current_range_mv=c['range_mv'],
                        reverse_v=reverse, master_w=w if valid else None,
                        master_valid=valid, master_quality=p.get('quality'),
                        master_calibration_frequency_hz=p['calibration_frequency_hz'])
        except (OSError, ValueError, KeyError, StopIteration) as exc:
            errors.append(str(exc))
            if attempt < 2:
                time.sleep(min(.15, max(0, deadline-time.monotonic())))
    raise ValueError('Paired A0/A2 read failed: '+'; '.join(errors))


def capture(args, deadline):
    pairs = []
    for i in range(args.samples):
        if i:
            time.sleep(min(args.sample_interval, max(0, deadline-time.monotonic())))
        pairs.append(read_pair(args.pico, deadline))
    fv = [x['forward_v'] for x in pairs]
    cv = [x['current_v'] for x in pairs]
    watts = [x['master_w'] for x in pairs if x['master_valid']]
    reverse = [x['reverse_v'] for x in pairs if isinstance(x['reverse_v'], (int, float))
               and math.isfinite(x['reverse_v'])]
    usable = len(watts) == len(pairs)
    sd = lambda xs: statistics.stdev(xs) if len(xs) > 1 else 0
    return dict(sample_count=len(pairs), forward_mean_v=statistics.mean(fv),
                forward_std_v=sd(fv), forward_min_v=min(fv), forward_max_v=max(fv),
                forward_raw_samples=json.dumps([x['forward_raw'] for x in pairs]),
                forward_range_mv_samples=json.dumps([x['forward_range_mv'] for x in pairs]),
                reverse_mean_v=statistics.mean(reverse) if reverse else '',
                current_mean_v=statistics.mean(cv), current_std_v=sd(cv),
                current_min_v=min(cv), current_max_v=max(cv),
                current_raw_samples=json.dumps([x['current_raw'] for x in pairs]),
                current_range_mv_samples=json.dumps([x['current_range_mv'] for x in pairs]),
                master_mean_w=statistics.mean(watts) if usable else '',
                master_std_w=sd(watts) if usable else '',
                master_valid_samples=len(watts), alignment_usable=usable,
                master_calibration_frequency_hz=7031670,
                paired_samples=json.dumps(pairs, separators=(',', ':')))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--plan', action='store_true')
    parser.add_argument('--output')
    parser.add_argument('--notes', default='A0 master / A2 alignment; 50 ohms, no scope')
    parser.add_argument('--port', default=sweep_tool.DEFAULT_PORT)
    parser.add_argument('--baud', type=int, choices=(19200,), default=19200)
    parser.add_argument('--key-line', choices=('rts',), default='rts')
    parser.add_argument('--pico', default='192.168.178.98')
    parser.add_argument('--frequency', type=int, choices=(7031670, 7100000), default=7100000)
    parser.add_argument('--levels', default='1,2,3,4,5,10,15,20,30,40,50,60,70,80,90,100')
    parser.add_argument('--samples', type=int, default=3)
    parser.add_argument('--sample-interval', type=float, default=.15)
    parser.add_argument('--settle', type=float, default=1)
    parser.add_argument('--pause', type=float, default=5)
    parser.add_argument('--max-tx', type=float, default=8)
    args = parser.parse_args(argv)
    args.probe = 'a0_master'
    try:
        if not args.plan and not args.run:
            print(json.dumps(capture(args, time.monotonic()+8), indent=2))
        return sweep_tool.sweep(args, capture_fn=capture,
                                fields=sweep_tool.FIELDS+EXTRA_FIELDS)
    except KeyboardInterrupt:
        print('Stopped; RX cleanup requested.', file=sys.stderr)
        return 130
    except Exception as exc:
        print('Error: '+str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
