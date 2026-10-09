#!/usr/bin/env python3
"""Offline tests; no serial port, network, scope or RF access."""
import contextlib
import csv
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import powermeter_probe_test as meter


class FakeRig:
    instance = None
    def __init__(self, *args):
        FakeRig.instance = self
        self.io = self
        self.rts = False
        self.dtr = False
        self.closed = False
        self.frequency = 7031670
        self.power = 82
        self.key_events = []
    def query(self, cmd):
        if cmd == b'\x03': return meter.encode_bcd(self.frequency, 5)[::-1]
        if cmd == b'\x04': return b'\x03\x03'
        if cmd == b'\x14\x0a': return meter.encode_bcd(self.power, 2)
        return meter.encode_bcd(100, 2)
    def write_setting(self, cmd, data):
        if cmd == b'\x05': self.frequency = meter.bcd(data[::-1])
        if cmd == b'\x14\x0a': self.power = meter.bcd(data)
    def rx(self):
        self.rts = self.dtr = False
        self.key_events.append('rx')
    def close(self): self.closed = True


class FakeTimer:
    ident = None
    def __init__(self, seconds, callback): self.callback = callback
    def start(self): self.ident = 1
    def cancel(self): pass
    def join(self): pass


def detector(host, deadline):
    rig = FakeRig.instance
    v = rig.power/255 if rig.rts else .001
    return [dict(input='A0-A3', voltage_v=v, raw=1234, range_mv=1024, valid=True),
            dict(input='A1-A3', voltage_v=None, valid=False)]


class ProbeTest(unittest.TestCase):
    def invoke(self, argv, reader=detector):
        with patch.object(meter, 'Rig', FakeRig), patch.object(meter, 'read_detector', reader), \
             patch.object(meter.time, 'sleep', lambda x: None), \
             patch.object(meter.threading, 'Timer', FakeTimer), \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return meter.main(argv)
    def test_levels(self):
        self.assertEqual(meter.levels_parse('1:100:1'), list(range(1,101)))
        for text in ['0,10', '1,101', 'nan', '1:10:0', '1,1', '1,1.01']:
            with self.assertRaises(ValueError): meter.levels_parse(text)
    def test_plan_no_device_access(self):
        with patch.object(meter, 'Rig', side_effect=AssertionError('device access')), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(meter.main(['sweep','--plan']),0)
    def test_sweep_and_restore(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'a.csv'
            self.assertEqual(self.invoke(['sweep','--run','--probe','without','--levels','1,50,100',
                                         '--samples','3','--pause','0','--output',str(out)]),0)
            with out.open() as f: rows=list(csv.DictReader(f))
            self.assertEqual(len(rows),4)
            self.assertAlmostEqual(float(rows[0]['forward_mean_v']),.001)
            self.assertEqual(float(rows[-1]['forward_mean_v']),1)
            rig=FakeRig.instance
            self.assertFalse(rig.rts)
            self.assertEqual((rig.frequency,rig.power,rig.closed),(7031670,82,True))
    def test_failure_retains_completed_points_and_rx(self):
        def bad(host,deadline):
            if FakeRig.instance.rts and FakeRig.instance.power>100:
                raise TimeoutError('failed capture')
            return detector(host,deadline)
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'a.csv'
            self.assertEqual(self.invoke(['sweep','--run','--probe','without','--levels','1,100',
                                         '--pause','0','--output',str(out)],bad),1)
            with out.open() as f: self.assertEqual(len(list(csv.DictReader(f))),2)
            rig=FakeRig.instance
            self.assertFalse(rig.rts)
            self.assertEqual((rig.frequency,rig.power,rig.closed),(7031670,82,True))
    def test_watchdog_discards_point_and_restores(self):
        class ExpiringTimer(FakeTimer):
            def start(self): self.ident=1;self.callback()
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'timeout.csv'
            with patch.object(meter, 'Rig', FakeRig), patch.object(meter, 'read_detector', detector), \
                 patch.object(meter.time, 'sleep', lambda x: None), \
                 patch.object(meter.threading, 'Timer', ExpiringTimer), \
                 contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(meter.main(['sweep','--run','--probe','without','--levels','5',
                                            '--pause','0','--output',str(out)]),1)
            with out.open() as f: self.assertEqual(len(list(csv.DictReader(f))),1)
            self.assertFalse(FakeRig.instance.rts)
            self.assertEqual((FakeRig.instance.frequency,FakeRig.instance.power),(7031670,82))
    def test_readonly_no_tx_or_writes(self):
        self.assertEqual(self.invoke(['sweep']),0)
        rig=FakeRig.instance
        self.assertEqual((rig.frequency,rig.power,rig.key_events),(7031670,82,[]))
    def test_compare_and_refuse_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            a,b,out=[Path(d)/x for x in ('a.csv','b.csv','diff.csv')]
            for path,label,factor in ((a,'without',1),(b,'with',1.1)):
                self.assertEqual(self.invoke(['sweep','--run','--probe',label,'--levels','10,100',
                                             '--pause','0','--output',str(path)]),0)
                if factor!=1:
                    with path.open() as f: rows=list(csv.DictReader(f))
                    for row in rows[1:]:
                        row['forward_mean_v']=float(row['forward_mean_v'])*factor
                        row['forward_net_v']=float(row['forward_mean_v'])-.001
                    with path.open('w',newline='') as f:
                        w=csv.DictWriter(f,meter.FIELDS);w.writeheader();w.writerows(rows)
            args=['compare','--without',str(a),'--with-probe',str(b),'--output',str(out)]
            with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(meter.main(args),0)
                self.assertEqual(meter.main(args),1)
            with out.open() as f: rows=list(csv.DictReader(f))
            self.assertTrue(all(abs(float(x['difference_pct'])-10)<1e-8 for x in rows))
            self.assertTrue(all(float(x['net_difference_pct'])>10 for x in rows))


if __name__=='__main__': unittest.main()
