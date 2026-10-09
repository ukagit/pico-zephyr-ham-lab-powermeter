# 0.1.36 – 1N4148-Messkopf, 50 Ohm, 1 MHz

A2 akzeptiert zusätzlich die Kombination 1 MHz / scope_vpp_sine_50ohm / master scope. Bestehende 7,1-MHz-A0-Abgleiche, Speicherformat und Profile bleiben kompatibel. JSON-API und Web zeigen Referenz und Frequenz der aktiven A2-Kurve. Keine neue Kennlinie automatisch aktiviert.

Vorlage: docs/calibration/1n4148_50ohm_1mhz.json. Sie enthält die drei bisherigen Standardkurven plus die neue A2-Kurve. Durch select current wird nur A2 ersetzt.

17 gemessene Punkte, FY-Stufen 4–20, 2,04–9,2 Vss, ADC 0,0016328–0,3348281 V. Leistung fuer Sinus am 50-Ohm-Abschluss: P=Vss²/400, Einheit W. Bereich 0,010404–0,2116 W. FY-Ausgang CH2, Scope CH1. Baseline 0,0001484 V. Punkte 0–3 wegen Nähe zum Nullpegel und fehlender Wiederholungsmessungen vorerst ausgeschlossen. Raw ADC-Spannungen inklusive Nullpegel verwenden, keinen zweiten Offset abziehen. Keine Extrapolation.

Diese automatisierte Reihe unterscheidet sich erheblich von der vorigen Handmessung: bei ca. 5 Vss früher 0,777 V, jetzt 0,1497734 V. Messweg, Teiler und Scope-Skalierung vor einer abschließenden Kalibrierung vergleichen. Profil ist vorläufig und gilt ausschließlich für diesen Aufbau bei 1 MHz.

Nach Build/Flash:

```bash
python3 tools/powermeter_curves.py import docs/calibration/1n4148_50ohm_1mhz.json --profile diode_1mhz --save
```

Auf dem Pico:

```text
hamlab curves select current diode_1mhz
hamlab curves status
```

A2-Wattwert unter current_coupler.power_50ohm_w; Hauptanzeige/SWR weiter aus A0/A1. Der Rollenname current bleibt aus Kompatibilitätsgründen, auch für diesen Spannungsmesskopf. 19 Offline-Tests bestehen. Kein Zephyr-Build/Hardwaretest hier durchgeführt.
