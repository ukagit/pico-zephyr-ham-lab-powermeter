# Firmware 0.1.43 – A2 direkt, 1:1

Korrektur der Hardwareangabe: A2 hat keinen Spannungsteiler. Das Gleichspannungs-Voltmeter zeigt daher die ADC-Spannung direkt an. Im Kanal A2-A3 gilt `divider_ratio: 1` und `input_voltage_v == voltage_v`, sofern gültig und nicht übersteuert. Vollansicht und A2-Kompaktseite sind angepasst; Balken-Autoscale 0,1/0,2/0,5/1/2/3,3 V. Die Änderung ersetzt die Faktor-2-Annahme von 0.1.42.

Leistungskennlinien verwenden weiterhin die unveränderte ADC-Spannung. Batterie GP28 hat weiterhin ihren eigenen Faktor 2. ADC-Versorgung 3,3 V: Der PGA-Bereich ±6,144 V erweitert die zulässige physische Eingangsspannung nicht.

Offline-Prüfungen bestanden; Zephyr-Build und Hardwaretest erfolgen beim Nutzer.
