#!/usr/bin/env python3
"""Validate/export/import four JSON curves and select named sensor profiles.
Import without --save only transfers and checks; it does not save/activate.
No radio, scope or TX access. USB filesystem is not implemented in step 1.
"""
import argparse
import json
import math
from pathlib import Path
import re
import socket
import sys
import time

MAX_JSON = 4096
EXPECTED = {
    'forward': ('A0-A3', 7031670, 'scope_vpp_sine_50ohm', 'scope'),
    'reverse_7mhz': ('A1-A3', 7100000, 'reversed_coupler_scope_vpp_50ohm', 'scope'),
    'reverse_50mhz': ('A1-A3', 50100000, 'reversed_coupler_scope_vpp_50ohm', 'scope'),
    'current': ('A2-A3', 7100000, 'a0_master_50ohm', 'A0'),
}


def unique_object(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError('Duplicate JSON key: '+key)
        out[key] = value
    return out


def validate(text):
    def bad_constant(value):
        raise ValueError('Invalid JSON number: '+value)
    data = json.loads(text, object_pairs_hook=unique_object, parse_constant=bad_constant)
    if not isinstance(data, dict) or set(data) != {'schema_version', 'curves'} or type(data['schema_version']) is not int or data['schema_version'] != 1:
        raise ValueError('Expected schema_version 1 and curves')
    if not isinstance(data['curves'], list) or len(data['curves']) != 4:
        raise ValueError('Exactly four curves required')
    seen = set()
    for c in data['curves']:
        if not isinstance(c, dict) or set(c) != {'id', 'input', 'frequency_hz', 'reference', 'master', 'load_ohms', 'points'}:
            raise ValueError('Unexpected/missing curve fields')
        identity = c['id']
        if not isinstance(identity, str) or identity not in EXPECTED or identity in seen:
            raise ValueError('Unknown/duplicate curve id')
        seen.add(identity)
        expected = EXPECTED[identity]
        if identity == 'current' and c['frequency_hz'] == 1000000:
            expected = ('A2-A3', 1000000, 'scope_vpp_sine_50ohm', 'scope')
        if (c['input'], c['frequency_hz'], c['reference'], c['master']) != expected or type(c['frequency_hz']) is not int or type(c['load_ohms']) not in (int, float) or c['load_ohms'] != 50:
            raise ValueError('Wrong input/frequency/reference/master/load: '+identity)
        pts = c['points']
        if not isinstance(pts, list) or not 2 <= len(pts) <= 24:
            raise ValueError('2..24 points required: '+identity)
        previous = None
        for p in pts:
            if not isinstance(p, list) or len(p) != 2 or any(type(x) not in (int, float) or not math.isfinite(x) for x in p):
                raise ValueError('Finite [voltage_v, power_w] pairs required')
            v, w = p
            if not 0 <= v <= 3.3 or not 0 < w <= 150 or previous and (v <= previous[0] or w < previous[1]):
                raise ValueError('Invalid point limits/order: '+identity)
            previous = p
    raw = json.dumps(data, ensure_ascii=True, separators=(',', ':'), allow_nan=False).encode('ascii')
    if len(raw) > MAX_JSON:
        raise ValueError('Compact JSON exceeds 4096 bytes')
    return data, raw


class Console:
    def __init__(self, args):
        self.serial = bool(args.serial)
        self.timeout = args.timeout
        if self.serial:
            import serial
            self.io = serial.Serial(args.serial, 115200, timeout=.2)
            self.io.write(b'\r\n')
        else:
            self.io = socket.create_connection((args.host, 23), args.timeout)
            self.io.settimeout(.2)
        try:
            self.prompt()
        except Exception:
            self.io.close()
            raise

    def prompt(self):
        end = time.monotonic()+self.timeout
        raw = bytearray()
        while time.monotonic() < end:
            try:
                chunk = self.io.read(1024) if self.serial else self.io.recv(4096)
            except socket.timeout:
                continue
            if not chunk:
                if not self.serial:
                    raise ConnectionError('Shell connection closed')
                continue
            raw.extend(chunk)
            if len(raw) > 16384:
                raise ValueError('Shell response too large')
            text = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', raw.decode('utf-8', errors='replace'))
            if re.search(r'(?:tcp|uart):~\$\s*$', text):
                return text
        raise TimeoutError('No shell prompt; check connection or reconnect terminal')

    def command(self, command):
        raw = (command+'\r\n').encode('ascii')
        if len(raw) > 240:
            raise ValueError('Shell command too long')
        self.io.write(raw) if self.serial else self.io.sendall(raw)
        response = self.prompt()
        if 'Curves error' in response or 'command returned' in response or 'not found' in response.lower() or 'Unknown command' in response:
            raise ValueError(response.strip())
        start = response.find('{')
        if start < 0:
            raise ValueError('Missing JSON acknowledgement: '+response.strip())
        return json.JSONDecoder().raw_decode(response[start:])[0]

    def close(self):
        self.io.close()


def transfer(console, raw, save, profile=None):
    owned = False
    try:
        reply = console.command('hamlab curves begin '+str(len(raw)))
        owned = True
        if reply.get('expected_bytes') != len(raw) or reply.get('received_bytes') != 0:
            raise ValueError('Begin acknowledgement mismatch')
        owned = True
        for offset in range(0, len(raw), 80):
            piece = raw[offset:offset+80]
            reply = console.command('hamlab curves chunk '+piece.hex())
            if reply.get('received_bytes') != offset+len(piece):
                raise ValueError('Chunk acknowledgement mismatch')
        reply = console.command('hamlab curves check')
        if reply.get('valid') is not True or reply.get('saved') is not False:
            raise ValueError('Check acknowledgement mismatch')
        if save:
            reply = console.command('hamlab curves store '+profile if profile else 'hamlab curves import')
            if reply.get('saved') is not True or (profile and (reply.get('profile') != profile or reply.get('activated') is not False)) or (not profile and reply.get('source') != 'flash'):
                raise ValueError('Import acknowledgement mismatch; inspect hamlab curves status')
            owned = False
        return reply
    finally:
        if owned:
            try:
                console.command('hamlab curves abort')
            except Exception as exc:
                print('Transfer cleanup failed; use hamlab curves abort: '+str(exc), file=sys.stderr)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--host', default='192.168.178.98')
    ap.add_argument('--serial', help='Zephyr USB CDC port instead of Telnet')
    ap.add_argument('--timeout', type=float, default=10)
    sub = ap.add_subparsers(dest='cmd', required=True)
    check = sub.add_parser('validate', help='Offline only, no Pico access')
    check.add_argument('file')
    imp = sub.add_parser('import', help='Pico check only unless --save')
    imp.add_argument('file')
    imp.add_argument('--profile', help='Save a named profile without activating; requires --save to store')
    imp.add_argument('--save', action='store_true', help='Explicitly save and activate entire set')
    exp = sub.add_parser('export', help='Export active set; refuse existing output')
    exp.add_argument('--output', required=True)
    sub.add_parser('status')
    sub.add_parser('list')
    sel = sub.add_parser('select')
    sel.add_argument('role', choices=tuple(EXPECTED))
    sel.add_argument('profile')
    args = ap.parse_args(argv)
    console = None
    try:
        if not math.isfinite(args.timeout) or args.timeout <= 0:
            raise ValueError('Positive timeout required')
        profile = getattr(args, 'profile', None)
        if profile is not None and profile not in ('builtin','legacy') and (not re.fullmatch(r'[A-Za-z0-9_-]{1,23}', profile) or profile in ('legacy', 'imported', 'active')):
            raise ValueError('Invalid profile name: 1..23 letters/digits/_/-, reserved names forbidden')
        if args.cmd == 'import' and profile in ('builtin','legacy'):
            raise ValueError('builtin and legacy are reserved')
        if args.cmd in ('validate', 'import'):
            data, raw = validate(Path(args.file).read_text(encoding='utf-8'))
            print(f'Valid: four curves, {sum(len(c["points"]) for c in data["curves"])} points, {len(raw)} compact bytes')
            if args.cmd == 'validate':
                return 0
        if args.cmd == 'export' and Path(args.output).exists():
            raise ValueError('Output exists; use a new filename')
        console = Console(args)
        if args.cmd == 'import':
            reply = transfer(console, raw, args.save, args.profile)
            print(json.dumps(reply))
            print(('Profile stored; activate with select.' if args.profile else 'Saved/active in flash; verify after restart.') if args.save else 'Pico JSON check passed; nothing saved or activated.')
        elif args.cmd == 'export':
            data = console.command('hamlab curves export')
            validate(json.dumps(data))
            with Path(args.output).open('x', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=True)
                f.write('\n')
            print('Saved '+args.output)
        elif args.cmd == 'select':
            print(json.dumps(console.command('hamlab curves select '+args.role+' '+args.profile), indent=2))
        else:
            print(json.dumps(console.command('hamlab curves '+args.cmd), indent=2))
        return 0
    except KeyboardInterrupt:
        print('Stopped.', file=sys.stderr)
        return 130
    except Exception as exc:
        print('Error: '+str(exc), file=sys.stderr)
        return 1
    finally:
        if console:
            console.close()


if __name__ == '__main__':
    sys.exit(main())
