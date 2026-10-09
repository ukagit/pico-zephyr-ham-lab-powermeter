"""Offline tests of actual firmware parser/store using a simulated settings backend."""
import copy
import ctypes as C
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import powermeter_curves as pc

ROOT = Path(__file__).resolve().parents[1]
class Point(C.Structure):
    _fields_ = [('v', C.c_double), ('w', C.c_double)]
class Curve(C.Structure):
    _fields_ = [('hz', C.c_uint32), ('count', C.c_uint16), ('reserved', C.c_uint16), ('points', Point*24)]
class Bank(C.Structure):
    _fields_ = [('magic', C.c_uint32), ('schema', C.c_uint32), ('curves', Curve*4), ('crc', C.c_uint32)]

class CurvesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        t = Path(cls.tmp.name)
        h = t/'zephyr/settings/settings.h'; h.parent.mkdir(parents=True)
        h.write_text('''#include <stddef.h>
#include <sys/types.h>
typedef ssize_t (*settings_read_cb)(void *,void *,size_t);
typedef int (*settings_load_direct_cb)(const char *,size_t,settings_read_cb,void *,void *);
int settings_subsys_init(void);
int settings_load_subtree_direct(const char *,settings_load_direct_cb,void *);
int settings_save_one(const char *,const void *,size_t);
''')
        (t/'mock.c').write_text("""#include <zephyr/settings/settings.h>
#include <string.h>
struct item {char key[64]; unsigned char data[4096];size_t len;};
static struct item items[16];static int count;
int fail_write,writes;
int settings_subsys_init(void){return 0;}
static ssize_t rd(void *arg,void *out,size_t n){struct item *i=arg;if(n>i->len)return -5;memcpy(out,i->data,n);return n;}
int settings_load_subtree_direct(const char *key,settings_load_direct_cb cb,void *arg){size_t n=strlen(key);for(int i=0;i<count;i++)if(!strncmp(key,items[i].key,n)&&items[i].key[n]=='/'){int rc=cb(items[i].key+n+1,items[i].len,rd,&items[i],arg);if(rc)return rc;}return 0;}
int settings_save_one(const char *key,const void *data,size_t n){if(fail_write)return -5;int i=0;while(i<count&&strcmp(key,items[i].key))i++;if(i==count){if(count==16)return -28;count++;strcpy(items[i].key,key);}memcpy(items[i].data,data,n);items[i].len=n;writes++;return 0;}
void corrupt(void){for(int i=0;i<count;i++)if(!strcmp(items[i].key,"hamlab_profiles/active"))items[i].data[20]^=1;}
void clear(void){count=0;fail_write=writes=0;}
""")
        so=t/'core.so'
        subprocess.run(['gcc','-std=c11','-Wall','-Wextra','-Werror','-shared','-fPIC','-I'+str(t), str(ROOT/'src/curves/curves_core.c'),str(ROOT/'src/curves/curves_store.c'),str(t/'mock.c'),'-lm','-o',str(so)],check=True)
        cls.lib=C.CDLL(str(so))
    @classmethod
    def tearDownClass(cls): cls.tmp.cleanup()
    def setUp(self):
        self.data,_=pc.validate((ROOT/'docs/calibration/curves-v0.1.32.json').read_text())
        self.error=C.create_string_buffer(200)
        self.lib.clear()
        self.assertEqual(self.lib.hamlab_curves_init(),0)
    def parse(self,data):
        raw=data if isinstance(data,bytes) else json.dumps(data,separators=(',',':')).encode()
        bank=Bank()
        rc=self.lib.curves_parse(raw,len(raw),C.byref(bank),self.error,len(self.error))
        return rc,bank
    def test_parser_and_exact_export(self):
        rc,b=self.parse(self.data);self.assertEqual(rc,0,self.error.value)
        self.assertTrue(self.lib.curves_bank_valid(C.byref(b)))
        out=C.create_string_buffer(4097)
        self.assertGreater(self.lib.curves_encode(C.byref(b),out,len(out)),0)
        rc,b2=self.parse(out.value);self.assertEqual(rc,0)
        self.assertEqual(bytes(b),bytes(b2))
        b.curves[0].points[0].w+=1
        self.assertFalse(self.lib.curves_bank_valid(C.byref(b)))
    def test_scope_detector_one_mhz(self):
        data,_=pc.validate((ROOT/'docs/calibration/1n4148_50ohm_1mhz.json').read_text())
        rc,bank=self.parse(data);self.assertEqual(rc,0,self.error.value)
        self.assertEqual(bank.curves[3].hz,1000000)
        self.assertEqual(bank.curves[3].count,17)
        self.assertAlmostEqual(bank.curves[3].points[0].w,2.04**2/400)
        self.assertAlmostEqual(bank.curves[3].points[16].w,9.2**2/400)
        out=C.create_string_buffer(4097)
        self.assertGreater(self.lib.curves_encode(C.byref(bank),out,len(out)),0)
        again,_=pc.validate(out.value.decode());self.assertEqual(again['curves'][3]['master'],'scope')
        rc,reloaded=self.parse(out.value);self.assertEqual(rc,0)
        self.assertEqual(bytes(bank),bytes(reloaded))
        data['curves'][3]['master']='A0';self.assertNotEqual(self.parse(data)[0],0)
    def test_order_and_limits(self):
        data=copy.deepcopy(self.data); data['curves'].reverse()
        self.assertEqual(self.parse(data)[0],0)
        for mutate in [lambda d:d['curves'].pop(), lambda d:d['curves'].__setitem__(1,d['curves'][0]),lambda d:d['curves'][0].update(frequency_hz=7100000),lambda d:d['curves'][0]['points'].__setitem__(1,d['curves'][0]['points'][0]),lambda d:d['curves'][0]['points'][0].__setitem__(0,3.4),lambda d:d['curves'][0]['points'][0].__setitem__(1,151),lambda d:d.update(extra=1)]:
            data=copy.deepcopy(self.data);mutate(data)
            self.assertNotEqual(self.parse(data)[0],0)
        raw=json.dumps(self.data,separators=(',',':')).encode()
        for malformed in [raw+b'\0',raw+b'x',raw.replace(b'"schema_version":1',b'"schema_version":1,"schema_version":1'),raw.replace(b'0.0556641',b'NaN'),raw[:300]]:
            self.assertNotEqual(self.parse(malformed)[0],0)
    def test_interpolation_no_extrapolation(self):
        _,b=self.parse(self.data);c=b.curves[0];w=C.c_double()
        fn=self.lib.curves_interpolate;fn.argtypes=[C.POINTER(Curve),C.c_double,C.POINTER(C.c_double)]
        v=(c.points[0].v+c.points[1].v)/2
        self.assertTrue(fn(C.byref(c),v,C.byref(w)))
        self.assertAlmostEqual(w.value,(c.points[0].w+c.points[1].w)/2)
        self.assertFalse(fn(C.byref(c),0,C.byref(w)))
        self.assertFalse(fn(C.byref(c),3.3,C.byref(w)))
    def test_store_commit_failure_recovery(self):
        lib=self.lib
        self.assertEqual(lib.hamlab_curves_init(),0)
        lib.hamlab_curve.restype=C.POINTER(Curve)
        original=lib.hamlab_curve(0).contents.points[0].w
        data=copy.deepcopy(self.data);data['curves'][0]['points'][0][1]+=0.01
        _,raw=pc.validate(json.dumps(data))
        self.assertEqual(lib.hamlab_curves_begin(len(raw)),0)
        self.assertNotEqual(lib.hamlab_curves_chunk(b'zz'),0)
        self.assertEqual(lib.hamlab_curves_received(),0)
        self.assertNotEqual(lib.hamlab_curves_check(self.error,len(self.error)),0)
        for i in range(0,len(raw),80):self.assertEqual(lib.hamlab_curves_chunk(raw[i:i+80].hex().encode()),0)
        self.assertEqual(lib.hamlab_curves_check(self.error,len(self.error)),0)
        self.assertEqual(lib.hamlab_curve(0).contents.points[0].w,original)
        C.c_int.in_dll(lib,'fail_write').value=1
        self.assertNotEqual(lib.hamlab_curves_import(self.error,len(self.error)),0)
        self.assertEqual(lib.hamlab_curve(0).contents.points[0].w,original)
        C.c_int.in_dll(lib,'fail_write').value=0
        self.assertEqual(lib.hamlab_curves_import(self.error,len(self.error)),0)
        self.assertAlmostEqual(lib.hamlab_curve(0).contents.points[0].w,original+.01)
        self.assertTrue(lib.hamlab_curves_from_flash())
        self.assertEqual(lib.hamlab_curves_init(),0) # re-read saved record
        lib.corrupt()
        self.assertNotEqual(lib.hamlab_curves_init(),0)
        self.assertFalse(lib.hamlab_curves_from_flash())
        self.assertEqual(lib.hamlab_curve(0).contents.points[0].w,original)
    def upload(self,data):
        _,raw=pc.validate(json.dumps(data))
        self.assertEqual(self.lib.hamlab_curves_begin(len(raw)),0)
        for i in range(0,len(raw),80):self.assertEqual(self.lib.hamlab_curves_chunk(raw[i:i+80].hex().encode()),0)
    def test_profile_selection_persistence_and_failure(self):
        lib=self.lib;lib.hamlab_curve.restype=C.POINTER(Curve)
        lib.hamlab_curve_profile.restype=C.c_char_p
        old=lib.hamlab_curve(3).contents.points[0].w
        self.data['curves'][3]['points'][0][1]=1.4
        self.data['curves'][3]['points'][1][1]=1.4
        self.upload(self.data)
        self.assertEqual(lib.hamlab_curves_import_profile(b'current_100watt',self.error,len(self.error)),0)
        self.assertEqual(lib.hamlab_curve(3).contents.points[0].w,old)
        C.c_int.in_dll(lib,'fail_write').value=1
        self.assertNotEqual(lib.hamlab_curves_select(3,b'current_100watt'),0)
        self.assertEqual(lib.hamlab_curve(3).contents.points[0].w,old)
        C.c_int.in_dll(lib,'fail_write').value=0
        self.assertEqual(lib.hamlab_curves_select(3,b'current_100watt'),0)
        self.assertEqual(lib.hamlab_curve(3).contents.points[0].w,1.4)
        self.assertEqual(lib.hamlab_curves_init(),0)
        self.assertEqual(lib.hamlab_curve_profile(3),b'current_100watt')
        self.assertEqual(lib.hamlab_curve(3).contents.points[0].w,1.4)
        self.upload(self.data)
        self.assertNotEqual(lib.hamlab_curves_import_profile(b'current_100watt',self.error,len(self.error)),0)
        lib.hamlab_curves_abort()
        self.assertEqual(lib.hamlab_curves_select(3,b'builtin'),0)
        self.assertEqual(lib.hamlab_curve(3).contents.points[0].w,old)
        self.assertNotEqual(lib.hamlab_curves_select(3,b'no_such_profile'),0)
        self.assertNotEqual(lib.hamlab_curves_select(5,b'builtin'),0)
    def test_legacy_migration_and_profile_limit(self):
        lib=self.lib;lib.hamlab_curve_profile.restype=C.c_char_p
        _,bank=self.parse(self.data)
        self.assertEqual(lib.settings_save_one(b'hamlab_curves/bank',C.byref(bank),C.sizeof(bank)),0)
        self.assertEqual(lib.hamlab_curves_init(),0)
        self.assertEqual(lib.hamlab_curve_profile(0),b'legacy')
        for i in range(8):
            self.upload(self.data)
            self.assertEqual(lib.hamlab_curves_import_profile(('sensor_'+str(i)).encode(),self.error,len(self.error)),0)
        self.upload(self.data)
        self.assertNotEqual(lib.hamlab_curves_import_profile(b'sensor_9',self.error,len(self.error)),0)
        lib.hamlab_curves_abort()
        self.assertEqual(lib.hamlab_curves_select(3,b'sensor_0'),0)
        self.assertEqual(lib.hamlab_curves_init(),0)
        self.assertEqual(lib.hamlab_profiles_count(),8)
        self.assertEqual(lib.hamlab_curve_profile(0),b'legacy')
        self.assertEqual(lib.hamlab_curve_profile(3),b'sensor_0')
        self.assertEqual(lib.hamlab_curves_select(3,b'legacy'),0)
        self.assertEqual(lib.hamlab_curve_profile(3),b'legacy')
        for name in (b'',b'builtin',b'../foo',b'active',b'x'*24):self.assertFalse(lib.hamlab_profile_name_valid(name))
    def test_pc_check_and_commit_protocol(self):
        class Fake:
            def __init__(self):self.commands=[];self.n=0
            def command(self,s):
                self.commands.append(s)
                if ' begin ' in s:return {'expected_bytes':5,'received_bytes':0}
                if ' chunk ' in s:self.n+=len(s.split()[-1])//2;return {'received_bytes':self.n}
                if s.endswith('check'):return {'valid':True,'saved':False}
                if ' store ' in s:return {'saved':True,'activated':False,'profile':s.split()[-1]}
                if s.endswith('import'):return {'saved':True,'source':'flash'}
                return {'aborted':True}
        f=Fake();pc.transfer(f,b'abcde',False)
        self.assertTrue(f.commands[-1].endswith('abort'))
        self.assertFalse(any(s.endswith('import') for s in f.commands))
        f=Fake();pc.transfer(f,b'abcde',True)
        self.assertTrue(f.commands[-1].endswith('import'))
        f=Fake();pc.transfer(f,b'abcde',True,'current_100watt')
        self.assertTrue(f.commands[-1].endswith('store current_100watt'))

if __name__=='__main__':unittest.main()
