> Historischer Zwischenstand. Aktuell: [Bedienung](bedienung.md), [Kalibrierung](messung-und-kalibrierung.md), [Werkzeuge](testwerkzeuge.md).

# Vorläufige Vorlaufkalibrierung 0.1.4

Gemessen am 03.10.2026 bei 7031670 Hz, 50-Ohm-Last, CW.
Quelle: cal_7mhz_20V_5_20div(1).csv (5..20%) und cal_7mhz_50Vdiv(1).csv (30..100%).
Referenz P=Vss²/400, Sinus vorausgesetzt. RMS dient als Vergleich, nicht als gemittelte Referenz.
Stückweise lineare Interpolation der gemessenen ADC-Spannung auf Watt.
Spannungsteiler bereits enthalten, kein weiterer Faktor 2.
Gültiger Tabellenbereich 0.2366875..2.277875 V / 4..92.16 W.
Außerhalb: forward_w=null, quality=outside_calibrated_range. Kein erfundener Nullpunkt.
Die HF-Frequenz wird vom Pico nicht gemessen: frequency_verified=false.
DDS frequency_hz ist unabhängig. Diese Kennlinie nur für den unveränderten Aufbau bei 7.031670 MHz verwenden.
Rücklauf und SWR unkalibriert. Kein Nachweis für 150 W oder andere Frequenzen.
RMS/Vss-Leistungsdifferenz bei 5% ca. 11.4%, bei 100% ca. 3% (bezogen auf RMS).

## Bedienung
hamlab meter / hamlab power; HTTP /api/v1/measure und /api/v1/state.
Web / und /compact zeigen Vorlauf-Watt sowie beide ADC-Spannungen.
Unterhalb der kleinsten Kalibrierspannung erscheint --, auch bei ausgeschaltetem Sender.

## Prüfung
Hosttest: Tabellenpunkte, Zwischenwerte, NaN, Bereichsgrenzen.
Kein lokaler Zephyr-Build möglich; west build und Hardwaretest beim Anwender erforderlich.
