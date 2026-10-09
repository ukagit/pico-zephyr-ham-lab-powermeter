"""Exercise the voltage widget's warning, recovery and offline states."""
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parent.parent

class A2VoltageTest(unittest.TestCase):
    def test_both_pages(self):
        for page in ('hamlab.html', 'compact-a2.html'):
            with self.subTest(page=page):
                html = (ROOT / 'web' / page).read_text()
                fn = html[html.index('function drawA2Voltage'):html.index('let lastA2=')]
                script = '''const nodes={};
const el=id=>nodes[id]??(nodes[id]={style:{},setAttribute(k,v){this[k]=v},removeAttribute(k){delete this[k]}});
''' + fn + '''
const sample=v=>({valid:true,overrange:false,voltage_v:v,input_voltage_v:v,divider_ratio:1});
drawA2Voltage(sample(0.5));
if(nodes.a2voltage.textContent!=='0,5000 V')throw Error('1:1 voltage');
drawA2Voltage(sample(3.2));
if(nodes.a2voltage.textContent!=='OVERFLOW'||nodes.a2vfill.style.width!=='100%'||nodes.a2vfill.style.background!=='#e53935')throw Error('rail warning');
drawA2Voltage({valid:false,overrange:true,input_voltage_v:null});
if(nodes.a2voltage.textContent!=='OVERFLOW')throw Error('ADC overrange');
drawA2Voltage(sample(0.5));
if(nodes.a2voltage.textContent!=='0,5000 V'||nodes.a2vfill.style.background!=='#64b5ff')throw Error('recovery');
drawA2Voltage(null);
if(nodes.a2voltage.textContent!=='-- V'||nodes.a2vfill.style.width!=='0%')throw Error('offline');
'''
                subprocess.run(['node', '-e', script], check=True)
