#!/usr/bin/env python3
"""IC-7300 / sds status / Pico raw detector calibration.
Default: read-only connection check. --run enables RF using USB CW RTS (configurable).
Requires CW, BK-IN enabled, USB Keying(CW)=RTS, USB SEND=OFF,
USB Keying(RTTY)=OFF, a rated 50-ohm dummy load and suitable scope probe.
RF setting percentages are NOT reference watts. Scope Vpp determines reference.
"""
import argparse
import csv
import json
import math
from pathlib import Path
import re
import shlex
import subprocess
import sys
import threading
import time
from urllib.request import urlopen
from urllib.error import HTTPError, URLError
from datetime import datetime,timezone
from icom7300_read import CIV,DEFAULT_PORT,bcd,frames

def encode_bcd(value,width):
    text=f'{value:0{width*2}d}'
    if len(text)!=width*2:raise ValueError('BCD overflow')
    return bytes(int(text[i:i+2],16) for i in range(0,len(text),2))

def scope_parse(text,channel):
    line=next((s for s in text.splitlines() if s.startswith(f'CH{channel}:')),None)
    if not line:raise ValueError('Scope channel missing')
    result={}
    for key in ('RMS','Vpp','Freq'):
        m=re.search(r'\b'+key+r'\s*=\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\s*([munpkMG]?)(V|Hz)',line)
        if not m:raise ValueError('Invalid scope '+key+': '+line)
        scale={'':1,'m':1e-3,'u':1e-6,'n':1e-9,'p':1e-12,'k':1e3,'M':1e6,'G':1e9}[m[2]]
        result[key]=float(m[1])*scale
    if result['Vpp']<=0 or result['Freq']<=0:raise ValueError('No usable RF signal')
    return result

def load_reference(vpp,load_ohms):
    load_w=vpp*vpp/(8*load_ohms)
    rho=(load_ohms-50)/(load_ohms+50)
    forward_w=load_w/(1-rho*rho)
    return load_w,forward_w,forward_w*rho*rho

def pico_read(host,deadline=None):
    last_error='No response'
    for attempt in range(1,4):
        remaining=2 if deadline is None else deadline-time.monotonic()
        if remaining<=0:raise TimeoutError('TX time limit reached during Pico read; point discarded')
        data=None;status=200
        try:
            try:
                with urlopen('http://'+host+':8080/api/v1/measure',timeout=min(2,remaining)) as response:
                    data=json.load(response)
            except HTTPError as exc:
                status=exc.code
                if status not in (409,503):raise
                try:data=json.loads(exc.read())
                finally:exc.close()
            if not data.get('measurement_valid'):
                details={key:data.get(key) for key in ('measurement_valid','measurement_error','channels')}
                last_error=f'HTTP {status}: '+json.dumps(details,separators=(',',':'))
            else:
                channels=data['channels']
                if [c.get('input') for c in channels[:2]]!=['A0-A3','A1-A3']:
                    raise ValueError('Unexpected Pico ADC mapping: '+json.dumps(channels))
                for channel in channels[:2]:
                    voltage=channel.get('voltage_v')
                    if not channel.get('valid') or channel.get('overrange') or not isinstance(voltage,(int,float)) or not math.isfinite(voltage):
                        raise ValueError('Invalid detector value: '+json.dumps(channel))
                return data
        except (URLError,TimeoutError,OSError) as exc:
            if isinstance(exc,HTTPError) and exc.code not in (409,503):raise
            last_error=str(exc)
        if attempt<3:
            print(f'Pico attempt {attempt}/3 failed: {last_error}; retrying',file=sys.stderr,flush=True)
            remaining=.2 if deadline is None else min(.2,max(0,deadline-time.monotonic()))
            if remaining:time.sleep(remaining)
    raise ValueError('Pico measurement invalid after 3 attempts: '+last_error)

# Scope setup happens in RX, outside the bounded TX interval.
def scope_scale(value):
    exponent=math.floor(math.log10(value))
    return min((m*10**e for e in range(exponent-1,exponent+2) for m in (1,2,5)),key=lambda x:abs(math.log(x/value)))

def scope_plan(frequency,level,factors,vdiv_map):
    vdiv=next(volts for limit,volts in vdiv_map if level<=limit)
    return [(scope_scale(factor/frequency),vdiv) for factor in factors]

def parse_scope_map(text):
    entries=[tuple(map(float,item.split(':'))) for item in text.split(',')]
    if not entries or entries[-1][0]!=100 or any(not math.isfinite(x) or x<=0 for pair in entries for x in pair) or any(a[0]>=b[0] for a,b in zip(entries,entries[1:])):
        raise ValueError('Scope map requires increasing upper percentages ending at 100, with positive V/div')
    return entries

def setup_scope(command,channel,tdiv,vdiv):
    for argv,pattern,expected in (
        (command+['tdiv',format(tdiv,'.12g')],r'tdiv=([0-9.eE+-]+)\s*([num]?)(?:s)/div',tdiv),
        (command+['vdiv',str(channel),format(vdiv,'.12g')],r'vdiv=([0-9.eE+-]+)\s*([mu]?)(?:V)/div',vdiv)):
        result=subprocess.run(argv,capture_output=True,text=True,timeout=3,check=True)
        match=re.search(pattern,result.stdout)
        if not match:
            raise ValueError('Scope setting response missing: '+result.stdout.strip())
        actual=float(match[1])*{'':1,'m':1e-3,'u':1e-6,'n':1e-9}[match[2]]
        if not math.isclose(actual,expected,rel_tol=.01,abs_tol=1e-15):
            raise ValueError(f'Scope setting mismatch: requested {expected:g}, received {actual:g}')
        print(result.stdout.strip(),flush=True)
    time.sleep(.25)

class Rig(CIV):
    def write_setting(self,command,data):
        self.io.reset_input_buffer()
        self.io.write(b'\xfe\xfe'+bytes((self.address,0xe0))+command+data+b'\xfd');self.io.flush()
        pending=bytearray();deadline=time.monotonic()+self.timeout
        while time.monotonic()<deadline:
            pending.extend(self.io.read(self.io.in_waiting or 1))
            for frame in frames(pending):
                if frame[:2]!=bytes((0xe0,self.address)):continue
                if frame[2:]==b'\xfb':return
                if frame[2:]==b'\xfa':raise RuntimeError('Setting rejected')
        raise TimeoutError('Setting not acknowledged')
    def rx(self):
        self.io.dtr=False;self.io.rts=False
        self.write_setting(b'\x1c\x00',b'\x00')

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--port',default=DEFAULT_PORT);ap.add_argument('--baud',type=int,default=19200)
    ap.add_argument('--key-line',choices=('rts','dtr'),default='rts',help='USB CW keying line; default RTS')
    ap.add_argument('--pico',default='192.168.178.98');ap.add_argument('--scope-command',default='sds status')
    ap.add_argument('--auto-scope',action='store_true',help='Set timebase and V/div before each capture, in RX')
    ap.add_argument('--scope-control',default='sds',help='CLI prefix, e.g. sds --ip HOST')
    ap.add_argument('--scope-vdiv-map',default='5:10,20:20,100:50',help='Upper RF percentage:V/div pairs')
    ap.add_argument('--timebase-factors',default='1',help='Seconds/div = factor/frequency, rounded to 1/2/5 steps; e.g. 0.5,1,2')
    ap.add_argument('--plan',action='store_true',help='Print plan only; no device access or writes')
    ap.add_argument('--channel',type=int,choices=(1,2),default=1)
    ap.add_argument('--frequency',type=int,default=7031670)
    ap.add_argument('--load-ohms',type=int,choices=(25,50),default=50,help='Actual resistive load; reference_w is forward power')
    ap.add_argument('--levels',default='5',help='RF setting percentages, e.g. 5,10,20')
    ap.add_argument('--output',default='powermeter_calibration.csv')
    ap.add_argument('--settle',type=float,default=0.3);ap.add_argument('--pause',type=float,default=5)
    ap.add_argument('--max-tx',type=float,default=8)
    ap.add_argument('--run',action='store_true');ap.add_argument('--self-test',action='store_true')
    args=ap.parse_args()
    if args.self_test:
        x=scope_parse('CH1: RMS=61.4 V  Vpp=176 V  Freq=7.03 MHz',1)
        assert abs(x['Vpp']**2/400-77.44)<1e-9
        assert encode_bcd(7031670,5)[::-1]==bytes.fromhex('70 16 03 07 00')
        assert scope_parse('CH2: RMS=235 mV Vpp=400 mV Freq=7 MHz',2)['Vpp']==0.4
        load,pf,pr=load_reference(54.4,25)
        assert abs(pf-16.6464)<1e-8 and abs(pr-pf/9)<1e-8
        assert load_reference(54.4,50)==(7.398399999999999,7.398399999999999,0.0)
        print('Scope parsing, units, 25/50-ohm reference and CI-V encoding passed');return 0
    levels=[float(v) for v in args.levels.split(',')]
    if any(not math.isfinite(v) or v<1 or v>100 for v in levels):ap.error('Levels must be 1..100')
    if not 1800000<=args.frequency<=54000000:ap.error('Check HF/50 MHz test frequency')
    if not 0<args.max_tx<=15 or not 0<=args.settle<args.max_tx or args.pause<0:ap.error('Invalid timing')
    try:
        factors=[float(x) for x in args.timebase_factors.split(',')]
        if not factors or any(not math.isfinite(x) or not .1<=x<=100 for x in factors):raise ValueError('Timebase factors must be 0.1..100')
        if not args.auto_scope and factors!=[1.0]:raise ValueError('Timebase factors require --auto-scope')
        vdiv_map=parse_scope_map(args.scope_vdiv_map)
        control=shlex.split(args.scope_control)
        if not control:raise ValueError('Empty scope control command')
    except ValueError as exc:ap.error(str(exc))
    captures=[(level,tdiv,vdiv,factor) for level in levels for factor,(tdiv,vdiv) in zip(factors,scope_plan(args.frequency,level,factors,vdiv_map))]
    if args.plan:
        for level,tdiv,vdiv,factor in captures:
            print(json.dumps(dict(frequency_hz=args.frequency,rf_setting_pct=level,auto_scope=args.auto_scope,scope_tdiv_s=tdiv if args.auto_scope else None,scope_vdiv_v=vdiv if args.auto_scope else None,timebase_factor=factor)))
        return 0
    out=Path(args.output)
    if args.run and out.exists():ap.error('Output already exists; choose a new filename')
    rig=None;original_freq=None;original_power=None;timer=None;expired=threading.Event()
    try:
        rig=Rig(args.port,args.baud,0x94,0.7,False)
        if args.run:rig.rx()
        original_freq=bcd(rig.query(b'\x03')[::-1])
        mode=rig.query(b'\x04')[0];original_power=bcd(rig.query(b'\x14\x0a'))
        print(json.dumps({'frequency_hz':original_freq,'mode_code':mode,'rf_power_raw':original_power,'pico':pico_read(args.pico)},indent=2))
        # Check the scope executable/output without requiring a carrier in check mode.
        cmd=shlex.split(args.scope_command)
        scope=subprocess.run(cmd,capture_output=True,text=True,timeout=3,check=True)
        print(scope.stdout)
        if not args.run:
            print('Connection check only. No TX or setting writes performed.');return 0
        if mode!=3:raise ValueError('Set Icom to CW before running')
        rig.write_setting(b'\x05',encode_bcd(args.frequency,5)[::-1])
        if bcd(rig.query(b'\x03')[::-1])!=args.frequency:raise ValueError('Frequency readback mismatch')
        fields=['timestamp_utc','frequency_hz','rf_setting_pct','rf_power_raw','scope_rms_v','scope_vpp_v','scope_frequency_hz','reference_w','load_ohms','load_w','reverse_reference_w','forward_v','reverse_v','forward_range_mv','reverse_range_mv','forward_raw','reverse_raw','po_raw','swr_raw','alc_raw','vd_raw','id_raw','capture_seconds','scope_tdiv_s','scope_vdiv_v','timebase_factor','scope_vpp_divisions','rms_vpp_ratio']
        with out.open('x',newline='') as file:
            writer=csv.DictWriter(file,fields);writer.writeheader();file.flush()
            for level,tdiv,vdiv,factor in captures:
                if args.auto_scope:setup_scope(control,args.channel,tdiv,vdiv)
                setting=round(level*255/100)
                rig.write_setting(b'\x14\x0a',encode_bcd(setting,2))
                if bcd(rig.query(b'\x14\x0a'))!=setting:raise ValueError('Power setting mismatch')
                expired.clear()
                def stop_rf():
                    expired.set();setattr(rig.io,args.key_line,False)
                timer=threading.Timer(args.max_tx,stop_rf);timer.daemon=True
                print(f'Measuring RF setting {level:g}% ...',flush=True)
                started=time.monotonic();timer.start()
                try:
                    setattr(rig.io,args.key_line,True);time.sleep(args.settle)
                    scope=subprocess.run(cmd,capture_output=True,text=True,timeout=3,check=True)
                    measured=scope_parse(scope.stdout,args.channel)
                    if args.auto_scope and measured['Vpp']/vdiv>7:raise ValueError('Scope signal exceeds 7 divisions; choose larger V/div and repeat')
                    if abs(measured['Freq']/args.frequency-1)>0.01:raise ValueError('Scope frequency mismatch')
                    pico=pico_read(args.pico,deadline=started+args.max_tx)
                    meters={key:bcd(rig.query(bytes((0x15,sub)))) for key,sub in [('po_raw',0x11),('swr_raw',0x12),('alc_raw',0x13),('vd_raw',0x15),('id_raw',0x16)]}
                    if expired.is_set():raise TimeoutError('TX time limit reached; point discarded')
                    a,b=pico['channels'];load_w,forward_ref,reverse_ref=load_reference(measured['Vpp'],args.load_ohms);row=dict(scope_tdiv_s=tdiv if args.auto_scope else '',scope_vdiv_v=vdiv if args.auto_scope else '',timebase_factor=factor if args.auto_scope else '',scope_vpp_divisions=measured['Vpp']/vdiv if args.auto_scope else '',rms_vpp_ratio=measured['RMS']*2*math.sqrt(2)/measured['Vpp'],timestamp_utc=datetime.now(timezone.utc).isoformat(),frequency_hz=args.frequency,rf_setting_pct=level,rf_power_raw=setting,scope_rms_v=measured['RMS'],scope_vpp_v=measured['Vpp'],scope_frequency_hz=measured['Freq'],reference_w=forward_ref,load_ohms=args.load_ohms,load_w=load_w,reverse_reference_w=reverse_ref,forward_v=a['voltage_v'],reverse_v=b['voltage_v'],forward_range_mv=a['range_mv'],reverse_range_mv=b['range_mv'],forward_raw=a['raw'],reverse_raw=b['raw'],capture_seconds=round(time.monotonic()-started,3),**meters)
                finally:
                    setattr(rig.io,args.key_line,False);timer.cancel();timer.join();timer=None;rig.rx()
                writer.writerow(row);file.flush();print(json.dumps(row),flush=True)
                time.sleep(args.pause)
        print('Saved '+str(out));return 0
    except KeyboardInterrupt:print('Stopped',file=sys.stderr);return 130
    except Exception as exc:print('Error: '+str(exc),file=sys.stderr);return 1
    finally:
        if rig:
            if args.run:
                setattr(rig.io,args.key_line,False)
                if timer:timer.cancel();timer.join()
                try:
                    rig.rx()
                    if original_power is not None:rig.write_setting(b'\x14\x0a',encode_bcd(original_power,2))
                    if original_freq is not None:rig.write_setting(b'\x05',encode_bcd(original_freq,5)[::-1])
                except Exception as exc:print('RX/restore failed: '+str(exc),file=sys.stderr)
            rig.io.close()

if __name__=='__main__':sys.exit(main())
