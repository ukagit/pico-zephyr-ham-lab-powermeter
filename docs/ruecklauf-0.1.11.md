> Historischer Zwischenstand. Aktuell: [Bedienung](bedienung.md), [Kalibrierung](messung-und-kalibrierung.md), [Werkzeuge](testwerkzeuge.md).

# Vorläufiger Rücklauf und SWR

Quelle reverse_25ohm_7mhz_tuner_off.csv, 04.10.2026, 7031670 Hz, Tuner aus.
Annahme: Last bei HF rein ohmsch 25 Ohm, Scope direkt über Last, Sinus.
CSV reference_w ist Vss²/400 (alte 50-Ohm-Formel).
Pload=Vss²/200, Pf=Pload*9/8, Pr=Pload/8=Vss²/1600.
Interpolierte Rücklaufkurve aus Punkten 10..30%, 1.0816..2.6244 W.
5%-Punkt (0.0076797 V / 0.4096 W) ausgeschlossen nahe Untergrund.
Unter 0.0558281 V oder über 0.1986094 V keine numerische Rücklaufleistung/SWR.
Keine Extrapolation und kein erfundener Nullpunkt. Gute 50-Ohm-Last ergibt deshalb zunächst SWR --.
Vorlaufkurve bleibt bisherige 50-Ohm-Kalibrierung. SWR=(1+sqrt(Pr/Pf))/(1-sqrt(Pr/Pf)).
SWR-Max-Hold 3 Sekunden, Reset gemeinsam mit Leistung. Web-Vollansicht und OLED ergänzt.
Kompaktansicht weiterhin nur Vorlauf. Kalibrierung nur bei diesem Aufbau/Frequenz.

## Abschließende gemeinsame Kalibrierung

1. Schalter, Analoginstrument/Stellwiderstand und Spannungsteiler endgültig fixieren.
2. Nullsignal beide Kanäle erfassen.
3. 50-Ohm-Last: Vorlaufkurve über gesamten gewünschten Bereich, niedrige Pegel eingeschlossen.
4. 25-Ohm-Last: Rücklaufkurve bei bekannten Lastspannungen, bis zur erlaubten Belastbarkeit.
5. Wiederholungen aufwärts/abwärts zur Kontrolle; Scope-Skalierung und RMS/Vss dokumentieren.
6. Unabhängige SWR-Prüfung; 25-Ohm-Kalibrierpunkte alleine sind keine unabhängige Validierung.
7. Erst dann finalen Status setzen. Oberhalb gemessener Bereiche und bei anderen Frequenzen bleibt eine weitere Kalibrierung nötig.
