#!/usr/bin/env python3
"""Export all active firmware curves as PNG, PDF and CSV; needs matplotlib."""
from pathlib import Path
import csv
import re
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

root = Path(__file__).resolve().parent.parent
version = re.search(r'HAMLAB_VERSION\s+"([^"]+)"',
                    (root/'src/hamlab_version.h').read_text()).group(1)
curves = []
for filename, name, label, frequency, color, master in [
    ('power_calibration.h', 'forward_curve', 'Vorlauf A0 · 7,03167 MHz', 7031670, '#187b54', 'Scope Vpp'),
    ('power_calibration.h', 'reverse_curve_7100000', 'Rücklauf A1 · 7,1 MHz', 7100000, '#2364b0', 'Scope Vpp, Koppler umgedreht'),
    ('power_calibration.h', 'reverse_curve_50100000', 'Rücklauf A1 · 50,1 MHz', 50100000, '#bf6421', 'Scope Vpp, Koppler umgedreht'),
    ('current_calibration.h', 'current_curve', 'Stromkoppler A2 · 7,1 MHz · A0-Master', 7100000, '#70449e', 'A0, 50 Ohm')]:
    source = (root/'src'/filename).read_text()
    block = re.search(r'\b'+name+r'\[\]\s*=\s*\{(.*?)\};', source, re.S).group(1)
    points = [tuple(map(float, p)) for p in
              re.findall(r'\{\s*([\d.]+)\s*,\s*([\d.]+)\s*\}', block)]
    assert len(points) >= 2
    assert all(b[0] > a[0] and b[1] >= a[1] for a, b in zip(points, points[1:]))
    curves.append(dict(name=name, label=label, frequency=frequency, color=color,
                       points=points, master=master, source=filename))

plt.rcParams.update({'font.family':'DejaVu Sans', 'font.size':10,
                     'axes.spines.top':False, 'axes.spines.right':False})
fig, axes = plt.subplots(2, 2, figsize=(13, 10))
fig.subplots_adjust(top=.87, bottom=.18, left=.075, right=.97, hspace=.40, wspace=.24)
fig.suptitle('Powermeter: aktive Kennlinien', fontsize=20, fontweight='bold', y=.97)
fig.text(.5,.93, f'Firmware {version} · aus beiden Kalibrierheadern · keine Extrapolation',
         ha='center', color='#46515f')
for row in range(2):
    for col in range(2):
        ax = axes[row,col]
        selected = curves[:3] if row == 0 else curves[3:]
        for c in selected:
            x, y = zip(*c['points'])
            ax.plot(x, y, 'o-', color=c['color'], lw=1.8, ms=4, label=c['label'])
        ax.set_xlabel('ADC-seitige Detektorspannung [V]')
        ax.set_ylabel('Zugeordnete Leistung [W]')
        ax.grid(alpha=.22)
        ax.xaxis.set_major_formatter(FuncFormatter(lambda x,p:f'{x:g}'.replace('.',',')))
        if row == 0:
            ax.set_title('Richtkoppler: '+('Gesamtbereich' if col == 0 else 'Unterer Bereich'))
            ax.set(xlim=(0,2.4), ylim=(0,100)) if col == 0 else ax.set(xlim=(0,.85), ylim=(0,20))
        else:
            ax.set_title('Stromkoppler: '+('A0-Abgleich, nur 50 Ω' if col == 0 else 'Unterer Bereich, nur 50 Ω'))
            ax.set(xlim=(0,.60), ylim=(0,100)) if col == 0 else ax.set(xlim=(0,.33), ylim=(0,20))
        if col == 0:
            ax.legend(fontsize=8, loc='upper left')
fig.text(.075,.105, 'Oben: Richtkoppler, Scope-Vpp-Referenz. Unten: zusätzlicher Stromkoppler, A0 ist Master.', fontsize=10)
fig.text(.075,.073, 'A2: 1 % ausgeschlossen; 90/100 % gepoolt. Konstante Randstücke decken nur beobachtete Endpunktstreuung ab.', fontsize=9)
fig.text(.075,.041, 'Punkte sind Firmware-Stützstellen; die Verbindung ist lineare Interpolation. Keine absolute Genauigkeit zugesichert.', fontsize=9)
fig.text(.075,.014, '„~1“ bei kleinem Rücklauf ist eine SWR-Annahme und kein Bestandteil dieser Leistungskennlinien.', fontsize=9, color='#46515f')
for ext in ('png', 'pdf'):
    out = root/'docs/images'/f'powermeter-kennlinien-v{version}.{ext}'
    fig.savefig(out, dpi=160, facecolor='white')
    print(out)
plt.close(fig)
out = root/'docs/calibration'/f'firmware-v{version}-kennlinien.csv'
with out.open('w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['curve','frequency_hz','adc_voltage_v','power_w','reference','source'])
    for c in curves:
        for v, w in c['points']:
            writer.writerow([c['name'],c['frequency'],v,w,c['master'],c['source']])
print(out)
print(f'PASS: {len(curves)} active firmware arrays, {sum(len(c["points"]) for c in curves)} support points; constant endpoint segments retained')
