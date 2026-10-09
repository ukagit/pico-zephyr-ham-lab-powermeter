# Unterbereich, noch ohne Leistungsreferenz

Vom Anwender am 03.10.2026 gemeldet, Prozent RF-Einstellung und Vorlauf-ADC-Spannung:

| RF % | ADC V |
|---|---|
|1|0.0056|
|2|0.1026|
|3|0.1387|
|4|0.2004|
|5|0.2445|

Keine bekannte Wattreferenz vorhanden. Prozent ist keine gemessene Leistung.
Diese Punkte ändern deshalb noch nicht die Volt-Watt-Kennlinie.
Bitte Scope Vss/RMS gleichzeitig bei 1,2,3,4,5% erfassen, passende Vertikalskalierung.
Der 1%-Wert liegt nahe bisherigen Nullsignalspannungen; Nullsignal erneut miterfassen.
5%-Spannung gegenüber bisher 0.2366875 V verändert: Wiederholungspunkt erforderlich.

# Peak-Hold 0.1.5

Maximum gültiger kalibrierter ADC-Messungen seit Boot oder manuellem Reset.
Firmware hält den Wert unabhängig vom Browser. POST /api/v1/peak/reset setzt ihn zurück.
Bei weiter anliegendem Signal wird er mit der nächsten Messung neu gesetzt.
SWR-Peak bleibt null bis zur separaten Rücklauf/SWR-Kalibrierung.
ADC-Messungen erfolgen periodisch, daher kein Nachweis einer schnellen HF-PEP-Messung.
DDS-/ATT-Informationen aus Web/OLED entfernt; bestehende Shell-Steuerung bleibt verfügbar.
