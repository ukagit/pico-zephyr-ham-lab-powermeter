# A2-Stromkoppler auf A0-Master abgleichen

Firmware 0.1.31 muss laufen. A0−A3 = bestehender Vorlauf-Richtkoppler, A2−A3 = neuer Stromkoppler. A3 Masse. Beide Koppler bleiben während der gesamten Messreihe angeschlossen. 50-Ω-Dummyload, kein Scope-Tastkopf, ICOM-Tuner aus, CW und vorhandene USB-CW-Tastung RTS. Baudrate unverändert 19200.

Im Pico per USB/Telnet:
```text
hamlab calibration 7100000
```
Damit wird die kompatible 7-MHz-Auswertung ausgewählt. Frequenz wird nicht automatisch erkannt. Die A0-Referenzkurve wurde bei 7.03167 MHz aufgenommen; der Abgleich darf bei 7.03167 oder 7.1 MHz laufen, standardmäßig 7.1 MHz.

Verbindung prüfen (ohne Sendetastung / ohne Einstellungsänderungen):
```sh
python3 tools/powermeter_align_current.py
```
Messplan anzeigen, ohne Gerätezugriff:
```sh
python3 tools/powermeter_align_current.py --plan
```
Messung:
```sh
python3 tools/powermeter_align_current.py --run --key-line rts --baud 19200   --pico 192.168.178.98 --frequency 7100000   --levels 1,2,3,4,5,10,15,20,30,40,50,60,70,80,90,100   --samples 3 --settle 1 --pause 5   --output abgleich_a2_auf_a0_7mhz.csv
```
Scope wird nicht angesprochen. Ablauf: RF-OFF-Ruhewerte, je Stufe drei gemeinsame A0/A2-Abfragen, Sender in RX zwischen Stufen. Watchdog schaltet RTS spätestens nach 8 Sekunden ab. Bei Abbruch werden RTS deaktiviert, RX angefordert und ursprüngliche ICOM-Frequenz/Leistungsstellung wiederhergestellt. Eine vorhandene CSV wird nicht überschrieben. Bereits erfasste Zeilen bleiben bei Fehler erhalten.

Wichtige CSV-Spalten:
- `master_mean_w`: Mittelwert der A0-Wattangabe, Referenz für den Abgleich.
- `current_mean_v`: gemittelte rohe A2−A3-Spannung; kein alter A2-Wattwert.
- `forward_mean_v`: A0−A3-Spannung zur Kontrolle.
- `master_std_w`, `current_std_v`: Streuung der Wiederholungen.
- `alignment_usable`: nur True, wenn sämtliche A0-Wattwerte der Stufe gültig sind.
- `paired_samples`: sämtliche Einzelpaare mit ADC-Rohwerten, Messbereichen und Status.
- Zeile 0 %: Ruhewerte, keine Leistungskalibrierungsstützstelle.

Falls der A0-Wert bei einer kleinen Leistungsstufe unterhalb seiner Kennlinie liegt, werden die Spannungen trotzdem gespeichert, aber keine Wattzahl erfunden. Für die spätere A2-Kurve nur gültige RF-Punkte verwenden. Der Ruheoffset wird dokumentiert; A2-Kennlinien verwenden tatsächliche ADC-Spannung, nicht automatisch offsetkorrigierte Spannung.

Die Prozentstellung am ICOM ist keine Wattreferenz. Dieser Abgleich übernimmt die Fehler/Unsicherheit von A0 und erhöht nicht die absolute Genauigkeit. Bei Fehlanpassung ist eine auf 50 Ω abgeglichene Strommessung keine allgemeine Leistungsmessung. Das Tool zeichnet nur auf und schreibt keine Kalibrierung in die Firmware. Die fertige CSV anschließend zur Auswertung bereitstellen.

Dieses Update betrifft nur die Python-Werkzeuge; kein erneuter Firmware-Flash erforderlich. Es benötigt auch die vorhandenen `powermeter_probe_test.py`, `powermeter_calibrate.py` und `icom7300_read.py` aus dem Paket sowie pyserial.
