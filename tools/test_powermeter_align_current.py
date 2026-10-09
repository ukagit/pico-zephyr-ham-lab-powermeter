#!/usr/bin/env python3
"""Offline alignment recorder checks: no radio, network or RF access."""
import contextlib
import csv
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import powermeter_align_current as align
import powermeter_probe_test as sweep
from test_powermeter_probe_test import FakeRig, FakeTimer, detector


def pair(host, deadline):
    rig = FakeRig.instance
    on = rig.rts
    v = rig.power/255 if on else .001
    return dict(timestamp_utc='2026-10-06T18:00:00+00:00', forward_v=v,
                current_v=v/2, forward_raw=1000, current_raw=500,
                forward_range_mv=2048, current_range_mv=1024, reverse_v=.001,
                master_w=v*100 if on else None, master_valid=on,
                master_quality='provisional' if on else 'outside_calibrated_range',
                master_calibration_frequency_hz=7031670)


class AlignmentTest(unittest.TestCase):
    def invoke(self, args, reader=pair):
        with patch.object(sweep, 'Rig', FakeRig), patch.object(sweep, 'read_detector', detector), \
             patch.object(align, 'read_pair', reader), \
             patch.object(sweep.threading, 'Timer', FakeTimer), \
             patch.object(sweep.time, 'sleep', lambda x: None), \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return align.main(args)

    def test_plan_no_access(self):
        with patch.object(sweep, 'Rig', side_effect=AssertionError()), \
             patch.object(align, 'read_pair', side_effect=AssertionError()), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(align.main(['--plan']), 0)

    def test_paired_recording_and_restore(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)/'paired.csv'
            self.assertEqual(self.invoke(['--run','--levels','1,20,100','--pause','0',
                                         '--output',str(out)]), 0)
            with out.open() as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 4)
            self.assertEqual(rows[0]['alignment_usable'], 'False')
            self.assertEqual(rows[0]['master_mean_w'], '')
            for r in rows[1:]:
                self.assertEqual(r['alignment_usable'], 'True')
                self.assertAlmostEqual(float(r['current_mean_v'])*200,
                                       float(r['master_mean_w']))
                self.assertEqual(len(json.loads(r['paired_samples'])), 3)
            rig = FakeRig.instance
            self.assertFalse(rig.rts)
            self.assertTrue(rig.closed)
            self.assertEqual((rig.frequency, rig.power), (7031670, 82))

    def test_uncalibrated_master_not_fabricated(self):
        def invalid(host, deadline):
            p = pair(host, deadline)
            p['master_w'] = None
            p['master_valid'] = False
            return p
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)/'invalid.csv'
            self.assertEqual(self.invoke(['--run','--levels','1','--pause','0',
                                         '--output',str(out)], invalid), 0)
            with out.open() as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(rows[1]['master_mean_w'], '')
            self.assertEqual(rows[1]['alignment_usable'], 'False')
            self.assertGreater(float(rows[1]['current_mean_v']), 0)

    def test_error_preserves_partial_and_rx(self):
        def failing(host, deadline):
            if FakeRig.instance.rts:
                raise ValueError('A2 absent')
            return pair(host, deadline)
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)/'partial.csv'
            self.assertEqual(self.invoke(['--run','--levels','1','--output',str(out)], failing), 1)
            with out.open() as f:
                self.assertEqual(len(list(csv.DictReader(f))), 1)
            self.assertFalse(FakeRig.instance.rts)
            self.assertTrue(FakeRig.instance.closed)
            self.assertEqual(FakeRig.instance.power, 82)


if __name__ == '__main__':
    unittest.main()
