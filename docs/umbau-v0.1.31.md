# Umbau 0.1.31

A0−A3 Vorlauf und A1−A3 Rücklauf behalten ihre Kennlinien. A3 bleibt Masse.
A2−A3 misst nun den neuen Stromkoppler, mit eigener ADS1115-Autorange.
Der Akku-Spannungsteiler (10 kΩ oben / 10 kΩ unten, Faktor 2) wechselt von A2 auf GP28 (Pico ADC2). Gemeinsame Masse. Keine Akkuspannung direkt an GP28: Eingang maximal 3,3 V.

`hamlab meter` und `/api/v1/state` liefern einen dritten Kanal `current` und `current_coupler.power_50ohm_w`. Fehler dieses Zusatzkanals beeinflussen die Gültigkeit der beiden Richtkopplerkanäle nicht. Die Web-Vollansicht und OLED-Vollansicht zeigen den zusätzlichen Wert; Kompaktansicht und SWR bleiben beim Richtkoppler.

Die Stromkoppler-Kurve stammt aus den Messungen vom 6.10.2026 bei 7,1 MHz: etwa 1,315–88,363 W. 90/100 % sind gepoolt. Keine Extrapolation. Leistung gilt ausschließlich für eine ohmsche 50-Ω-Last am Messort. Frequenz wird nicht automatisch erkannt. Bei Fehlanpassung ist der Wert keine allgemeingültige Leistungsmessung und wird nicht zur SWR-Berechnung benutzt.

Akku: alle zwei Sekunden, Pico-ADC 12 Bit, nominelle Referenz 3300 mV. Referenztoleranz beeinflusst die Spannung; bei Bedarf `vref-mv` anhand gemessener ADC-Versorgung anpassen. Akkuseite OLED zeigt GP28.

Build/Flash:
```sh
west build -b rpi_pico/rp2040/w -S cdc-acm-console . -d build -p always
./tools/flash_openocd.sh
```
Zephyr-Build und Hardwaretest müssen lokal erfolgen.
