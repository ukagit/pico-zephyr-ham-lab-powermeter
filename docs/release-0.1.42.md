# Firmware 0.1.42 – A2-Voltmeter

Vollansicht und A2-Kompaktseite zeigen zusätzlich die Gleichspannung vor dem externen 1:2-Spannungsteiler (zweimal 1,5 kΩ). Berechnung: ADC-Spannung × 2, ohne Detektor- oder Leistungskennlinie. Eigener linearer Spannungsbalken mit Autoscale 0,1/0,2/0,5/1/2/5/6,6 V. Die bestehende Leistungsanzeige bleibt erhalten.

API `/api/v1/state` und Shell `hamlab meter`: Kanal A2-A3 enthält `divider_ratio: 2` und `input_voltage_v`. `voltage_v` bleibt die unveränderte ADC-Spannung; Kennlinien verwenden weiterhin diesen Wert. Bei ADC-Fehler oder Übersteuerung ist `input_voltage_v` null. Bei A0/A1 ist dieses neue Feld null, da deren externe Beschaltung hier nicht umgerechnet wird.

Der Wert ist Gleichspannung nach dem Detektor, vor dem Teiler; er ist keine HF-Spitzenspannung, Vpp oder RMS. Die Diode wird damit nicht linearisiert. Der Faktor setzt den tatsächlichen 1:2-Teiler voraus. Der ADC wird mit 3,3 V versorgt; ±6,144 V PGA erlaubt keine Eingangsspannung oberhalb der Versorgung. 6,6 V vor dem Teiler ist die theoretische Versorgungsgrenze, keine empfohlene Betriebsreserve.

Lokale Offline-Prüfungen; Zephyr-Build und Hardwaretest erfolgen beim Nutzer.
