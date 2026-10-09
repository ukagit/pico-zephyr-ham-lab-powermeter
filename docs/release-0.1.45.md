# Firmware 0.1.45 – A2 dBm und OLED

Vollansicht und A2-Kompaktseite: dBm zusätzlich zu mW/W. Berechnung aus der ausgewählten Leistungskennlinie: 10 log10(P_W × 1000). Ohne gültige positive Leistung kein dBm-Wert. JSON current_coupler enthält power_dbm.

OLED: zwei neue Ansichten A2-Leistung (große Zahlen, mW/W, dBm, Balken und bestehender 3-s-Hold) und A2-Voltmeter (Volt 1:1, linearer Autoscale-Balken, OVERFLOW ab 3,2 V oder ADC-Übersteuerung). SSD1306 ist monochrom: Overflow als Text und voller Balken. Die Vollansicht des OLED zeigt ebenfalls A2 mW/W und dBm.

Bedienung: GP19 schaltet zyklisch A0 kompakt → A2-Leistung → A2-Voltmeter → A0 kompakt. GP20 Vollansicht, GP21 Akku. Encoder durchläuft alle fünf Ansichten.

Vorhandene Kennlinien und Flash-Profile bleiben erhalten. OA79-JSON separat importieren und current auswählen. Offline-Prüfungen; Zephyr-Build und Hardwaretest beim Nutzer.
