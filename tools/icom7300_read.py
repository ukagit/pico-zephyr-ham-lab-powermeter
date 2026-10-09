#!/usr/bin/env python3
"""IC-7300 USB CI-V read-only snapshot. No PTT or setting writes.
Install: python3 -m pip install pyserial
Run: python3 icom7300_read.py [--port PATH] [--baud 19200] [--watch 1]
Meter values are BCD-decoded indicator levels (0..255), NOT watts/volts/amps.
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone

DEFAULT_PORT = '/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_IC-7300_03009698-if00-port0'
MODES = {0:'LSB',1:'USB',2:'AM',3:'CW',4:'RTTY',5:'FM',7:'CW-R',8:'RTTY-R'}
# Only these query payloads are permitted; no data appended to read/write commands.
QUERIES = {'frequency_hz':b'\x03','mode':b'\x04','rf_power_raw':b'\x14\x0a',
           'po_raw':b'\x15\x11','swr_raw':b'\x15\x12','alc_raw':b'\x15\x13',
           'comp_raw':b'\x15\x14','vd_raw':b'\x15\x15','id_raw':b'\x15\x16'}

def bcd(data):
    digits=[]
    for value in data:
        hi,lo=value>>4,value&15
        if hi>9 or lo>9: raise ValueError('Invalid BCD: '+data.hex())
        digits.extend((str(hi),str(lo)))
    return int(''.join(digits)) if digits else 0

def frames(buffer):
    result=[]
    while True:
        start=buffer.find(b'\xfe\xfe')
        if start<0:
            if buffer[-1:] == b'\xfe': buffer[:]=b'\xfe'
            else: buffer.clear()
            break
        del buffer[:start]
        end=buffer.find(b'\xfd',2)
        if end<0: break
        result.append(bytes(buffer[2:end]));del buffer[:end+1]
    return result

class CIV:
    def __init__(self,port,baud,address,timeout,verbose):
        import serial
        self.io=serial.Serial(port=None,baudrate=baud,timeout=0.05,write_timeout=timeout,
                              exclusive=True)
        self.io.dtr=False;self.io.rts=False
        self.io.port=port;self.io.open()
        self.address=address;self.timeout=timeout;self.verbose=verbose
    def query(self,command):
        if command not in QUERIES.values(): raise ValueError('Query not allowed')
        self.io.reset_input_buffer()
        frame=b'\xfe\xfe'+bytes((self.address,0xe0))+command+b'\xfd'
        if self.verbose: print('TX '+frame.hex(' '),file=sys.stderr)
        self.io.write(frame);self.io.flush()
        pending=bytearray();deadline=time.monotonic()+self.timeout
        while time.monotonic()<deadline:
            pending.extend(self.io.read(self.io.in_waiting or 1))
            for reply in frames(pending):
                if self.verbose: print('RX '+reply.hex(' '),file=sys.stderr)
                if len(reply)<3 or reply[:2]!=bytes((0xe0,self.address)):continue
                body=reply[2:]
                if body==b'\xfa':raise RuntimeError('Radio rejected query')
                if body.startswith(command) and len(body)>len(command):
                    return body[len(command):]
        raise TimeoutError('No CI-V reply; check port, baud, address and CAT programs')
    def snapshot(self):
        result={'timestamp_utc':datetime.now(timezone.utc).isoformat(),
                'meter_units':'raw_indicator_levels_0_to_255'}
        errors={}
        for key,cmd in QUERIES.items():
            try:
                data=self.query(cmd)
                if key=='frequency_hz':
                    if len(data)!=5:raise ValueError('Expected 5 frequency bytes')
                    result[key]=bcd(data[::-1])
                elif key=='mode':
                    if len(data)!=2:raise ValueError('Expected mode and filter bytes')
                    result[key]=MODES.get(data[0],f'unknown_0x{data[0]:02x}')
                    result['filter']=data[1]
                else:
                    if len(data)!=2:raise ValueError('Expected 2 BCD bytes')
                    result[key]=bcd(data)
                    if result[key]>255:raise ValueError('Indicator outside 0..255')
            except (TimeoutError,RuntimeError,ValueError) as exc:
                result[key]=None;errors[key]=str(exc)
        if errors:result['errors']=errors
        return result

def self_test():
    assert bcd(bytes.fromhex('00 00 07 14 00')[::-1])==14070000
    assert bcd(bytes.fromhex('02 13'))==213
    pending=bytearray(b'noise\xfe\xfe\x94\xe0\x03\xfd\xfe')
    assert frames(pending)==[b'\x94\xe0\x03'] and pending==b'\xfe'
    pending.extend(bytes.fromhex('fe e0 94 03 00 00 07 14 00 fd'))
    assert frames(pending)==[bytes.fromhex('e0 94 03 00 00 07 14 00')]
    try:bcd(b'\xfa')
    except ValueError:pass
    else:raise AssertionError('Invalid BCD accepted')
    print('CI-V framing and BCD tests passed')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',default=DEFAULT_PORT)
    parser.add_argument('--baud',type=int,default=19200)
    parser.add_argument('--address',type=lambda x:int(x,16),default=0x94)
    parser.add_argument('--timeout',type=float,default=1.0)
    parser.add_argument('--watch',type=float,default=0,help='Repeat interval in seconds')
    parser.add_argument('--verbose',action='store_true')
    parser.add_argument('--self-test',action='store_true')
    args=parser.parse_args()
    if args.self_test:self_test();return 0
    if not 0<=args.address<=255 or args.timeout<=0 or args.watch<0:
        parser.error('Invalid address, timeout or interval')
    radio=None
    try:
        radio=CIV(args.port,args.baud,args.address,args.timeout,args.verbose)
        while True:
            result=radio.snapshot();print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)
            if not args.watch:return 1 if result.get('errors') else 0
            time.sleep(args.watch)
    except KeyboardInterrupt:return 0
    except Exception as exc:
        print('Error: '+str(exc),file=sys.stderr);return 1
    finally:
        if radio is not None:radio.io.close()

if __name__=='__main__':sys.exit(main())
